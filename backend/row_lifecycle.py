"""
Row lifecycle management for master_data DuckDB tables.

Implements soft-delete / restore with a stable per-row fingerprint so that
user-driven deletes survive the auto-sync cycle (re-applying deletes whenever
the source data is refreshed).

Hidden columns maintained on every master_data table:
    __is_deleted  BOOLEAN       - row is soft-deleted (excluded from preview)
    __deleted_at  TIMESTAMP     - when the row was deleted
    __row_fp      VARCHAR       - SHA-256 fingerprint over all non-meta columns
                                  (stable identity for restore + dedup)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Hidden columns we own. Anything starting with __ is treated as meta.
META_COLUMNS = ("__is_deleted", "__deleted_at", "__row_fp")


# ----------------------------------------------------------------------------
# Schema migration
# ----------------------------------------------------------------------------

def ensure_lifecycle_columns(duck_conn) -> None:
    """Idempotently add the lifecycle meta-columns to the master_data table.

    Safe to call repeatedly.  If the table does not exist yet, the call is a
    no-op (it will be created with the columns by the merge / create flow).
    """
    try:
        tables = {t[0] for t in duck_conn.execute("SHOW TABLES").fetchall()}
    except Exception:
        return

    if "master_data" not in tables:
        return

    existing = set(
        duck_conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
    )

    if "__is_deleted" not in existing:
        duck_conn.execute('ALTER TABLE master_data ADD COLUMN "__is_deleted" BOOLEAN DEFAULT FALSE')
    if "__deleted_at" not in existing:
        duck_conn.execute('ALTER TABLE master_data ADD COLUMN "__deleted_at" TIMESTAMP')
    if "__row_fp" not in existing:
        duck_conn.execute('ALTER TABLE master_data ADD COLUMN "__row_fp" VARCHAR')


# ----------------------------------------------------------------------------
# Fingerprint
# ----------------------------------------------------------------------------

def _safe_sql_ident(name: str) -> str:
    """Quote an identifier for DuckDB (escape any embedded double-quotes)."""
    return '"' + name.replace('"', '""') + '"'


def user_columns(duck_conn) -> List[str]:
    """Return the list of user-facing columns (excludes __meta columns)."""
    try:
        cols = duck_conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
    except Exception:
        return []
    return [c for c in cols if c not in META_COLUMNS]


def _row_fingerprint(row: Dict[str, Any]) -> str:
    """Deterministic SHA-256 fingerprint of a single row's user-data.

    Excludes META_COLUMNS.  Uses json.dumps with sorted keys + a stable
    representation of None values.
    """
    cleaned = {}
    for k, v in row.items():
        if k in META_COLUMNS:
            continue
        # Normalise: datetimes -> isoformat, everything else via str()
        if v is None:
            cleaned[k] = None
        elif isinstance(v, (int, float, str, bool)):
            cleaned[k] = v
        else:
            cleaned[k] = str(v)
    payload = json.dumps(cleaned, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_fingerprint(duck_conn) -> int:
    """Recompute __row_fp for every row where it's currently NULL.

    Returns the number of rows updated.  Safe to run after any merge that
    inserted new rows.
    """
    cols = user_columns(duck_conn)
    if not cols:
        return 0

    select_list = ", ".join(_safe_sql_ident(c) for c in cols)
    update_sql = f"""
        UPDATE master_data
           SET "__row_fp" = md5(concat_ws('||',
               {', '.join('coalesce(cast(' + _safe_sql_ident(c) + " AS VARCHAR), '<NULL>')" for c in cols)}
           ))
         WHERE "__row_fp" IS NULL OR "__row_fp" = ''
    """
    duck_conn.execute(update_sql)
    return duck_conn.execute("SELECT COUNT(*) FROM master_data WHERE \"__row_fp\" IS NOT NULL").fetchone()[0]


def recompute_fingerprint_for_rows(duck_conn, fingerprints: Sequence[str]) -> int:
    """Recompute __row_fp for the given existing rows.

    Used after Restore so that if the user later edits a column we still
    track the row correctly.  For our purposes the *value* rarely changes
    while the row is soft-deleted, so this is mostly a safety-net.
    """
    if not fingerprints:
        return 0
    cols = user_columns(duck_conn)
    if not cols:
        return 0

    select_list = ", ".join(_safe_sql_ident(c) for c in cols)
    placeholders = ",".join(["?"] * len(fingerprints))
    update_sql = f"""
        UPDATE master_data
           SET "__row_fp" = md5(concat_ws('||',
               {', '.join('coalesce(cast(' + _safe_sql_ident(c) + " AS VARCHAR), '<NULL>')" for c in cols)}
           ))
         WHERE "__row_fp" IN ({placeholders})
    """
    duck_conn.execute(update_sql, list(fingerprints))
    return len(fingerprints)


# ----------------------------------------------------------------------------
# Soft delete / restore
# ----------------------------------------------------------------------------

def soft_delete_rows(duck_conn, fingerprints: Sequence[str]) -> int:
    """Mark the given rows as deleted.  Returns the count affected."""
    if not fingerprints:
        return 0
    placeholders = ",".join(["?"] * len(fingerprints))
    sql = f"""
        UPDATE master_data
           SET "__is_deleted" = TRUE,
               "__deleted_at" = CURRENT_TIMESTAMP
         WHERE "__row_fp" IN ({placeholders})
           AND ("__is_deleted" = FALSE OR "__is_deleted" IS NULL)
    """
    duck_conn.execute(sql, list(fingerprints))
    # Return the number of rows still flagged as deleted (truthful count)
    return duck_conn.execute(
        f"SELECT COUNT(*) FROM master_data WHERE \"__row_fp\" IN ({placeholders}) AND \"__is_deleted\" = TRUE",
        list(fingerprints),
    ).fetchone()[0]


def restore_rows(duck_conn, fingerprints: Sequence[str]) -> int:
    """Un-delete the given rows.  Returns the count actually restored."""
    if not fingerprints:
        return 0
    placeholders = ",".join(["?"] * len(fingerprints))
    sql = f"""
        UPDATE master_data
           SET "__is_deleted" = FALSE,
               "__deleted_at" = NULL
         WHERE "__row_fp" IN ({placeholders})
           AND "__is_deleted" = TRUE
    """
    duck_conn.execute(sql, list(fingerprints))
    return duck_conn.execute(
        f"SELECT COUNT(*) FROM master_data WHERE \"__row_fp\" IN ({placeholders}) AND (\"__is_deleted\" = FALSE OR \"__is_deleted\" IS NULL)",
        list(fingerprints),
    ).fetchone()[0]


# ----------------------------------------------------------------------------
# Query helpers
# ----------------------------------------------------------------------------

def list_deleted_rows(
    duck_conn,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    source_file: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return deleted rows matching the given filters.

    The result is a list of dicts (one per row) including ALL user columns
    plus "__row_fp", "__deleted_at" and "Source_File_Name".
    """
    user_cols = user_columns(duck_conn)
    if not user_cols:
        return []

    select_list = (
        ["\"__row_fp\" AS _row_fp", "\"__deleted_at\" AS _deleted_at"]
        + [f"{_safe_sql_ident(c)} AS {_safe_sql_ident(c)}" for c in user_cols]
    )
    select_sql = ", ".join(select_list)

    where = ["\"__is_deleted\" = TRUE"]
    params: List[Any] = []

    if source_file and source_file not in ("All Files", "", None):
        where.append(f"{_safe_sql_ident('Source_File_Name')} = ?")
        params.append(source_file)

    if search:
        like_clauses = []
        for c in user_cols:
            like_clauses.append(f"CAST({_safe_sql_ident(c)} AS VARCHAR) ILIKE ?")
            params.append(f"%{search}%")
        if like_clauses:
            where.append("(" + " OR ".join(like_clauses) + ")")

    where_sql = " AND ".join(where)
    sql = f"""
        SELECT {select_sql}
          FROM master_data
         WHERE {where_sql}
         ORDER BY "__deleted_at" DESC NULLS LAST
         LIMIT ? OFFSET ?
    """
    params.extend([int(limit), int(offset)])
    df = duck_conn.execute(sql, params).fetchdf()
    return df.to_dict(orient="records")


def count_deleted_rows(
    duck_conn,
    search: Optional[str] = None,
    source_file: Optional[str] = None,
) -> int:
    """Count of rows currently soft-deleted (with optional filters)."""
    user_cols = user_columns(duck_conn)

    where = ["\"__is_deleted\" = TRUE"]
    params: List[Any] = []

    if source_file and source_file not in ("All Files", "", None):
        where.append(f"{_safe_sql_ident('Source_File_Name')} = ?")
        params.append(source_file)

    if search:
        like_clauses = []
        for c in user_cols:
            like_clauses.append(f"CAST({_safe_sql_ident(c)} AS VARCHAR) ILIKE ?")
            params.append(f"%{search}%")
        if like_clauses:
            where.append("(" + " OR ".join(like_clauses) + ")")

    where_sql = " AND ".join(where)
    sql = f'SELECT COUNT(*) FROM master_data WHERE {where_sql}'
    return int(duck_conn.execute(sql, params).fetchone()[0])


def list_deleted_source_files(duck_conn) -> List[str]:
    """Distinct Source_File_Name values for rows that are currently deleted."""
    try:
        df = duck_conn.execute(
            'SELECT DISTINCT "Source_File_Name" FROM master_data '
            'WHERE "__is_deleted" = TRUE AND "Source_File_Name" IS NOT NULL '
            'ORDER BY "Source_File_Name"'
        ).fetchdf()
        return df["Source_File_Name"].tolist()
    except Exception:
        return []