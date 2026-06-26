"""
One-time maintenance script to clean up the dedup table so the bug fix
takes effect immediately on restart, without needing to wait for the
next merge / sync cycle.

For every master_<folder_id>.duckdb under data/master_files/, this script:

  1. Ensures `__dedup_concat` has the new `row_fp` column.
  2. Removes any dedup row whose `row_fp` is NULL/empty (these are the
     "legacy" entries that, with the fix, cannot be matched back to a
     live master_data row — leaving them in keeps the old behaviour
     of "always block", but since the lookup now JOINs against master_data
     they become LEGACY entries that always count as duplicates).

     Actually that's the LEGACY safe behaviour — we DON'T want to wipe
     them. Instead we upgrade them by re-deriving from master_data.

  3. Rebuilds `__dedup_concat` from LIVE rows in `master_data` so the
     table starts in a clean, fully-fingerprinted state.

This script is idempotent — safe to run multiple times.

Usage:
    python cleanup_stale_dedup.py
"""
import os
import sys
import glob
import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.dedup_engine import (
    DEDUP_COL_NAME,
    ensure_dedup_table,
    populate_dedup_table,
)


def find_master_dbs():
    pattern = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data', 'master_files', '**', 'folder_*_master.duckdb',
    )
    return glob.glob(pattern, recursive=True)


def cleanup_one(master_db_path):
    print(f'\n=== {master_db_path} ===')
    folder_id = None
    try:
        base = os.path.basename(master_db_path)            # 'folder_<id>_master.duckdb'
        folder_id = int(base.replace('folder_', '').replace('_master.duckdb', ''))
    except Exception:
        pass
    print(f'  folder_id = {folder_id}')

    conn = duckdb.connect(master_db_path, read_only=False)
    try:
        tables = {t[0] for t in conn.execute("SHOW TABLES").fetchall()}
        if "master_data" not in tables:
            print('  master_data table missing — skipping.')
            return
        if DEDUP_COL_NAME not in tables:
            print('  __dedup_concat table missing — skipping (will be created on next merge).')
            return

        # Ensure row_fp column exists
        ensure_dedup_table(conn, DEDUP_COL_NAME)

        # Inspect current state
        cols_info = conn.execute(f"PRAGMA table_info({DEDUP_COL_NAME})").fetchall()
        col_names = {c[1] for c in cols_info}
        if 'row_fp' not in col_names:
            print('  no row_fp column — skipping (legacy pre-fix DB; nothing to clean).')
            return

        before_count = conn.execute(f"SELECT COUNT(*) FROM {DEDUP_COL_NAME}").fetchone()[0]
        live_fp_count = conn.execute(
            f"SELECT COUNT(*) FROM {DEDUP_COL_NAME} "
            f"WHERE row_fp IS NOT NULL AND row_fp <> ''"
        ).fetchone()[0]
        legacy_count = before_count - live_fp_count
        print(f'  before: {before_count} dedup rows ({live_fp_count} with fingerprint, {legacy_count} legacy)')

        # Look up the actual dedup config for this folder from SQLite so we
        # rebuild with EXACTLY the columns the user configured (not a superset,
        # which would over-block uploads).
        dedup_cols = None
        sep = ' | '
        if folder_id is not None:
            try:
                import sqlite3
                meta_paths = [
                    os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        'data', 'metadata.db',
                    ),
                    os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        'data', 'master_files', 'metadata.db',
                    ),
                ]
                for meta in meta_paths:
                    if not os.path.exists(meta):
                        continue
                    sconn = sqlite3.connect(meta)
                    try:
                        row = sconn.execute(
                            "SELECT dedup_enabled, dedup_columns, dedup_separator "
                            "FROM master_files WHERE folder_id = ?",
                            (folder_id,),
                        ).fetchone()
                    finally:
                        sconn.close()
                    if row:
                        enabled = bool(row[0])
                        cols_json = row[1]
                        sep = row[2] or ' | '
                        if not enabled or not cols_json:
                            print('  dedup disabled in config — wiping dedup table.')
                            conn.execute(f"DROP TABLE IF EXISTS {DEDUP_COL_NAME}")
                            break
                        try:
                            import json as _json
                            parsed = _json.loads(cols_json)
                            if isinstance(parsed, str):
                                parsed = _json.loads(parsed)
                            if isinstance(parsed, list):
                                dedup_cols = [str(c) for c in parsed if c]
                        except Exception:
                            dedup_cols = None
                        if dedup_cols:
                            print(f'  dedup config cols = {dedup_cols} (sep={sep!r})')
                        break
            except Exception as _meta_err:
                print(f'  WARN: could not read metadata.db: {_meta_err}')

        # Fallback: NO dedup config found. Take the conservative path —
        # drop the dedup table so the next sync will rebuild it from the
        # live config. We do NOT want to populate with guessed columns
        # because that could over-block legitimate uploads.
        if dedup_cols is None:
            print('  no dedup config found in SQLite — dropping __dedup_concat.')
            conn.execute(f"DROP TABLE IF EXISTS {DEDUP_COL_NAME}")
            return

        # Rebuild dedup table from LIVE rows only
        print('  rebuilding __dedup_concat from LIVE rows in master_data...')
        conn.execute(f"DROP TABLE IF EXISTS {DEDUP_COL_NAME}")
        ensure_dedup_table(conn, DEDUP_COL_NAME)

        _existing = conn.execute(
            "SELECT * FROM master_data "
            "WHERE (CAST(\"__is_deleted\" AS BOOLEAN) IS NULL "
            "       OR CAST(\"__is_deleted\" AS BOOLEAN) = FALSE)"
        ).fetchdf()
        if len(_existing) > 0:
            populate_dedup_table(
                conn, _existing, dedup_cols, sep, DEDUP_COL_NAME,
            )

        after_count = conn.execute(f"SELECT COUNT(*) FROM {DEDUP_COL_NAME}").fetchone()[0]
        with_fp = conn.execute(
            f"SELECT COUNT(*) FROM {DEDUP_COL_NAME} "
            f"WHERE row_fp IS NOT NULL AND row_fp <> ''"
        ).fetchone()[0]
        print(f'  after: {after_count} dedup rows ({with_fp} with fingerprint)')

    finally:
        conn.close()


def main():
    dbs = find_master_dbs()
    if not dbs:
        print('No master DuckDB files found under data/master_files/')
        return
    print(f'Found {len(dbs)} master DuckDB file(s).')
    for db in dbs:
        try:
            cleanup_one(db)
        except Exception as e:
            print(f'  ERROR: {e}')


if __name__ == '__main__':
    main()