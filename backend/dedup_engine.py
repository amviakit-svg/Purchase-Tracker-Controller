"""
backend/dedup_engine.py
========================

Concat-based duplicate detection for the "Create Master File" flow.

Strict whole-file rejection (no partial merging):
  - Pick one or more existing master-file columns.
  - Concatenate them with a separator (default ' | ').
  - Compare each new file's concat values against the set of values already
    present in master_data.
  - If ANY row in a file matches, the ENTIRE file is rejected.

A "rejected artefact" is written next to the original folder for the user to
download — it is the full file with two extra columns:
    Status         : 'Rejected – Duplicate' for matching rows, blank otherwise
    Reject_Reason  : reason text for matching rows, blank otherwise
"""

import os
import json
import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger("reconciliation_tool")

# Reserved system column added to the master_data DuckDB table that holds
# the per-row concat value. Prefixed with `__` so it is hidden from user
# column lists in the UI.
DEDUP_COL_NAME = "__dedup_concat"


# ============================================================
# Public API
# ============================================================

def is_dedup_active(dedup_cfg):
    """
    Returns True if dedup is configured AND has at least one column selected.
    This is the single check used by /api/master/merge and auto_sync.
    """
    if not dedup_cfg:
        return False
    if not dedup_cfg.get('dedup_enabled'):
        return False
    cols = dedup_cfg.get('dedup_columns_list') or []
    return len([c for c in cols if c]) > 0


def resolve_dedup_columns(dedup_cfg, available_columns):
    """
    Filter the configured dedup columns to only those that still exist in the
    file/master. Returns the resolved list. If the result is empty, dedup is
    considered inactive (returns []).
    """
    if not dedup_cfg:
        return []
    cols = dedup_cfg.get('dedup_columns_list') or []
    if isinstance(cols, str):
        try:
            cols = json.loads(cols)
        except (json.JSONDecodeError, TypeError):
            cols = []
    resolved = [c for c in cols if c in (available_columns or [])]
    return resolved


def build_concat(df, cols, sep=' | '):
    """
    Vectorized concat of the chosen columns, NaN-safe, trimmed.
    Returns a pd.Series of strings aligned to df.index.
    """
    if df is None or len(df) == 0 or not cols:
        return pd.Series([], dtype=str)
    parts = []
    for c in cols:
        if c not in df.columns:
            parts.append(pd.Series([''] * len(df), index=df.index, dtype=str))
        else:
            parts.append(df[c].fillna('').astype(str).str.strip())
    if not parts:
        return pd.Series([''] * len(df), index=df.index, dtype=str)
    out = parts[0]
    for p in parts[1:]:
        out = out + sep + p
    return out.fillna('').astype(str).str.strip()


def normalize_concat(series):
    """Lower-case + strip for comparison only."""
    if series is None or len(series) == 0:
        return series
    return series.fillna('').astype(str).str.strip().str.lower()


def load_existing_concat_set(duck_conn, dedup_col_name=DEDUP_COL_NAME):
    """
    Return a set of normalized concat values already present in master_data.
    """
    if duck_conn is None:
        return set()
    try:
        tables = duck_conn.execute("SHOW TABLES").fetchall()
        if (DEDUP_COL_NAME,) not in tables:
            return set()
        # Check if column exists
        cols_info = duck_conn.execute(f"PRAGMA table_info({dedup_col_name})").fetchall()
        col_names = [c[1] for c in cols_info]
        if 'value' not in col_names:
            return set()
        rows = duck_conn.execute(
            f"SELECT value FROM {dedup_col_name} WHERE value IS NOT NULL AND TRIM(value) <> ''"
        ).fetchall()
        result = set()
        for (v,) in rows:
            if v is None:
                continue
            result.add(str(v).strip().lower())
        return result
    except Exception as e:
        logger.warning(f"load_existing_concat_set failed: {e}")
        return set()


def detect_duplicate_rows(df, existing_set, cols, sep=' | '):
    """
    Return a boolean Series aligned to df.index: True where the row's concat
    value matches an existing value in the master.

    Matching is case-insensitive and trim-insensitive (normalized on both sides).
    """
    if df is None or len(df) == 0 or not existing_set or not cols:
        return pd.Series([False] * len(df), index=df.index if df is not None else None, dtype=bool)
    new_concat = build_concat(df, cols, sep)
    normalized = normalize_concat(new_concat)
    mask = normalized.isin(existing_set)
    return mask.fillna(False).astype(bool)


def ensure_dedup_table(duck_conn, dedup_col_name=DEDUP_COL_NAME):
    """
    Make sure the `__dedup_concat` DuckDB table exists. This is a small lookup
    table { value VARCHAR PRIMARY KEY } that stores the normalized concat
    values of every row currently in master_data. Using a table (instead of a
    column on master_data) keeps the master schema unchanged.
    """
    if duck_conn is None:
        return
    try:
        duck_conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {dedup_col_name} (
                value VARCHAR PRIMARY KEY
            )
            """
        )
    except Exception as e:
        logger.warning(f"ensure_dedup_table failed: {e}")


def populate_dedup_table(duck_conn, df, cols, sep=' | ', dedup_col_name=DEDUP_COL_NAME):
    """
    Compute the concat for every row in `df` and INSERT the unique values
    into the `__dedup_concat` table. Existing values are left alone.
    """
    if df is None or len(df) == 0 or not cols:
        return 0
    try:
        ensure_dedup_table(duck_conn, dedup_col_name)
        new_concat = build_concat(df, cols, sep)
        normalized = normalize_concat(new_concat)
        unique_vals = [v for v in normalized.unique().tolist() if v]
        if not unique_vals:
            return 0
        # Use INSERT ... ON CONFLICT DO NOTHING to be idempotent
        duck_conn.executemany(
            f"INSERT INTO {dedup_col_name} (value) VALUES (?) ON CONFLICT DO NOTHING",
            [(v,) for v in unique_vals],
        )
        return len(unique_vals)
    except Exception as e:
        logger.warning(f"populate_dedup_table failed: {e}")
        return 0


def write_rejected_artefact(file_df, file_info, dup_mask, cols, sep=' | ', reason='', rejected_artefact_dir=None):
    """
    Write the FULL file_df to an .xlsx file with two extra columns:
        Status         : 'Rejected – Duplicate' where dup_mask is True, else blank
        Reject_Reason  : reason text where dup_mask is True, else blank
    Returns the absolute path of the written artefact.

    Layout is:
        data/rejected/<folder_id>/<file_id>__<timestamp>.xlsx
    """
    if file_df is None or len(file_df) == 0:
        return None
    try:
        # Decide target directory
        if rejected_artefact_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'rejected')
        else:
            base_dir = rejected_artefact_dir
        folder_id = file_info.get('folder_id') if isinstance(file_info, dict) else None
        if folder_id is not None:
            base_dir = os.path.join(base_dir, f"folder_{folder_id}")
        os.makedirs(base_dir, exist_ok=True)

        file_id = file_info.get('id') if isinstance(file_info, dict) else None
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_id_part = f"file{file_id}_" if file_id is not None else ""
        artefact_name = f"{file_id_part}{ts}.xlsx"
        artefact_path = os.path.join(base_dir, artefact_name)

        artefact_df = file_df.copy()
        # Reset index to avoid pandas writing the index column
        artefact_df = artefact_df.reset_index(drop=True)
        # Make sure the mask is the same length and aligned
        if not isinstance(dup_mask, pd.Series):
            dup_mask = pd.Series([False] * len(artefact_df))
        else:
            dup_mask = dup_mask.reset_index(drop=True)
        if len(dup_mask) != len(artefact_df):
            # Pad/truncate defensively
            dup_mask = pd.Series([False] * len(artefact_df))

        artefact_df['Status']        = np.where(dup_mask, 'Rejected – Duplicate', '')
        artefact_df['Reject_Reason'] = np.where(dup_mask, reason or 'Duplicate concat match', '')

        try:
            artefact_df.to_excel(artefact_path, index=False)
        except Exception:
            # Fallback to CSV if openpyxl/xlsxwriter is missing
            artefact_path = artefact_path.replace('.xlsx', '.csv')
            artefact_df.to_csv(artefact_path, index=False)

        return artefact_path
    except Exception as e:
        logger.error(f"write_rejected_artefact failed: {e}")
        return None