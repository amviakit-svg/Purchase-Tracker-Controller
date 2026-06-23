"""
If-Condition engine for the Master File "Add Formula" modal.

Supports two payload shapes:

1) LEGACY single-group (kept for backward compatibility with existing saves):
    {
        "logic": "AND" | "OR",
        "conditions": [ {column, aggregator, value_type, value, ...}, ... ],
        "true_value":  {type, value},
        "false_value": {type, value},
    }
   → CASE WHEN (cond_1 AND/OR cond_2) THEN true_value ELSE false_value END

2) NEW multi-group (Phase-2 IF now mirrors Phase-3 flexibility):
    {
        "groups": [
            {
                "logic": "AND" | "OR",
                "conditions": [ ... ],
                "value": {type, value},   # value written into the target column
            },
            ...
        ],
        "false_value": {type, value},     # default when no group matches
    }
   → CASE
        WHEN (g1.cond1 AND g1.cond2)  THEN g1.value
        WHEN (g2.cond1 OR  g2.cond2)  THEN g2.value
        ELSE false_value
     END

Each condition has:
    column      - the column on the master_data table to test
    aggregator  - one of:
                    >, <, >=, <=, =, !=,
                    starts_with, ends_with, contains,
                    blank, not_blank,
                    left_eq, right_eq, mid_eq       ← NEW: position operators
    value_type  - "value" | "text" | "column" | "number"
                  (column not allowed for position operators)
    value       - the comparison value (literal or another column name)

Position operators carry extra fields:
    position    - "left" | "right" | "mid"
    length      - integer (chars to take from left/right; or substring length)
    start       - integer, 1-based, only for "mid"
    text_op     - one of: "=", "!=", "starts_with", "ends_with", "contains"

The true / false / group-value / false_value branch can be a literal
constant OR a column reference.

The aggregator list mirrors Excel's text-comparison operators + blank-checks,
plus positional text slicing (LEFT/RIGHT/MID).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Aggregator catalog (mirrors the UI dropdown)
# ---------------------------------------------------------------------------

NUMERIC_AGGREGATORS = {">", "<", ">=", "<="}
EQUALITY_AGGREGATORS = {"=", "!="}
TEXT_AGGREGATORS = {"starts_with", "ends_with", "contains"}
BLANK_AGGREGATORS = {"blank", "not_blank", "zero_or_blank", "not_zero_or_blank"}
POSITION_AGGREGATORS = {"left_eq", "right_eq", "mid_eq"}
BETWEEN_AGGREGATORS = {"between", "not_between"}
ALL_AGGREGATORS = (
    NUMERIC_AGGREGATORS
    | EQUALITY_AGGREGATORS
    | TEXT_AGGREGATORS
    | BLANK_AGGREGATORS
    | POSITION_AGGREGATORS
    | BETWEEN_AGGREGATORS
)

# Sub-operators usable inside a position operator
POSITION_TEXT_OPS = {"=", "!=", "starts_with", "ends_with", "contains"}


# ---------------------------------------------------------------------------
# SQL helpers (mirror auto_sync._safe_sql_ident behaviour)
# ---------------------------------------------------------------------------

def _safe_ident(name: str) -> str:
    if not name or not isinstance(name, str):
        raise ValueError("Column name must be a non-empty string")
    if name.startswith("__"):
        raise ValueError(f"Cannot reference internal column '{name}'")
    return '"' + name.replace('"', '""') + '"'


def _sql_string_literal(value: str) -> str:
    """Return a single-quoted SQL string with embedded quotes escaped."""
    return "'" + value.replace("'", "''") + "'"


def _sql_number_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    try:
        f = float(value)
        i = int(f)
        if f == i:
            return str(i)
        return repr(f)
    except (TypeError, ValueError):
        raise ValueError(f"Expected numeric value, got: {value!r}")


def _coerce_pos_int(raw: Any, field: str) -> int:
    """Coerce a position-operator integer field.  Rejects <=0 / non-int."""
    if raw is None or raw == "":
        raise ValueError(f"Position operator requires '{field}'")
    try:
        # Accept "3", 3, 3.0, "3.0" → 3
        n = int(float(raw))
    except (TypeError, ValueError):
        raise ValueError(f"'{field}' must be a positive integer, got {raw!r}")
    if n < 1:
        raise ValueError(f"'{field}' must be >= 1, got {n}")
    return n


# ---------------------------------------------------------------------------
# Position-operator SQL fragment
# ---------------------------------------------------------------------------

def _render_position_expr(cond: Dict[str, Any], columns: List[str]) -> Tuple[str, str]:
    """Return (sql_lhs_for_slice, referenced_column).

    The slice expression is the LEFT/RIGHT/SUBSTRING of the column cast to
    VARCHAR, e.g.  LEFT(CAST("col" AS VARCHAR), 3)
    """
    col = cond.get("column")
    if not col:
        raise ValueError("Position condition is missing 'column'")
    if col not in columns:
        raise ValueError(f"Column '{col}' does not exist in master file")

    position = (cond.get("position") or "").lower()
    if position not in ("left", "right", "mid"):
        raise ValueError(
            f"Position operator requires 'position' = left|right|mid (got {position!r})"
        )

    length = _coerce_pos_int(cond.get("length"), "length")

    col_id = _safe_ident(col)
    cast_col = f"CAST({col_id} AS VARCHAR)"

    if position == "left":
        sql_slice = f"LEFT({cast_col}, {length})"
    elif position == "right":
        sql_slice = f"RIGHT({cast_col}, {length})"
    else:  # mid
        start = _coerce_pos_int(cond.get("start"), "start")
        # DuckDB SUBSTRING is 1-based and accepts (str, start, length)
        sql_slice = f"SUBSTRING({cast_col}, {start}, {length})"

    return sql_slice, col


def _render_position_compare(
    sql_lhs: str,
    cond: Dict[str, Any],
    columns: List[str],
) -> Tuple[str, List[str]]:
    """Apply the inner text_op + value to the slice expression.

    RHS can be either a literal value or a column reference.  When it's a column,
    the same position/length/start slice is applied to the RHS column so the
    comparison is row-wise and symmetric (e.g. LEFT(A, 2) = LEFT(B, 2)).
    """
    text_op = (cond.get("text_op") or "=").lower()
    if text_op not in POSITION_TEXT_OPS:
        raise ValueError(
            f"Position operator 'text_op' must be one of {sorted(POSITION_TEXT_OPS)} (got {text_op!r})"
        )

    val_type = (cond.get("value_type") or "value").lower()
    val = cond.get("value", "")

    referenced: List[str] = []

    if val_type == "column":
        # Column RHS — slice the same way as the LHS so the comparison is
        # row-wise:  LEFT(A, 2) {op} LEFT(B, 2), etc.
        if not val:
            raise ValueError("Position operator (column RHS): column name is required.")
        if val not in columns:
            raise ValueError(f"Column '{val}' does not exist in master file")
        if val.startswith("__"):
            raise ValueError(f"Cannot reference internal column '{val}'")

        position = (cond.get("position") or "left").lower()
        if position not in ("left", "right", "mid"):
            raise ValueError(
                f"Position operator 'position' must be left|right|mid (got {position!r})"
            )
        length_val = _coerce_pos_int(cond.get("length"), "length")
        col_id = _safe_ident(val)
        cast_col = f"CAST({col_id} AS VARCHAR)"
        if position == "left":
            rhs_slice = f"LEFT({cast_col}, {length_val})"
        elif position == "right":
            rhs_slice = f"RIGHT({cast_col}, {length_val})"
        else:  # mid
            start_val = _coerce_pos_int(cond.get("start"), "start")
            rhs_slice = f"SUBSTRING({cast_col}, {start_val}, {length_val})"
        referenced.append(val)
    elif val_type in ("value", "text", "number"):
        if val is None or val == "":
            raise ValueError("Position operator requires a non-empty 'value'")
        rhs_slice = _sql_string_literal(str(val))
    else:
        raise ValueError(f"Unknown value_type '{val_type}' for position operator")

    if text_op == "=":
        return f"({sql_lhs} = {rhs_slice})", referenced
    if text_op == "!=":
        return f"({sql_lhs} != {rhs_slice})", referenced
    if text_op == "starts_with":
        return f"({sql_lhs} LIKE {rhs_slice} || '%')", referenced
    if text_op == "ends_with":
        return f"({sql_lhs} LIKE '%' || {rhs_slice})", referenced
    if text_op == "contains":
        return f"({sql_lhs} LIKE '%' || {rhs_slice} || '%')", referenced
    # Unreachable
    raise ValueError(f"Unhandled position text_op '{text_op}'")


# ---------------------------------------------------------------------------
# Condition rendering
# ---------------------------------------------------------------------------

def _render_condition(cond: Dict[str, Any], columns: List[str]) -> Tuple[str, List[str]]:
    """Return (sql_fragment, referenced_columns)."""
    if not isinstance(cond, dict):
        raise ValueError("Each condition must be an object")

    col = cond.get("column")
    agg = cond.get("aggregator")
    val_type = (cond.get("value_type") or "value").lower()
    val = cond.get("value", "")

    if not col:
        raise ValueError("Condition is missing 'column'")
    if col not in columns:
        raise ValueError(f"Column '{col}' does not exist in master file")
    if not agg:
        raise ValueError("Condition is missing 'aggregator'")
    if agg not in ALL_AGGREGATORS:
        raise ValueError(
            f"Unknown aggregator '{agg}'. Allowed: {sorted(ALL_AGGREGATORS)}"
        )

    # --- Position operators (LEFT/RIGHT/MID + inner text_op) ---
    if agg in POSITION_AGGREGATORS:
        sql_lhs, ref_col = _render_position_expr(cond, columns)
        fragment, extra_refs = _render_position_compare(sql_lhs, cond, columns)
        return fragment, [ref_col] + extra_refs

    col_id = _safe_ident(col)
    referenced = [col]

    # --- Blank checks ignore value entirely ---
    if agg == "blank":
        return (
            f"({col_id} IS NULL OR TRIM(CAST({col_id} AS VARCHAR)) = '')",
            referenced,
        )
    if agg == "not_blank":
        return (
            f"({col_id} IS NOT NULL AND TRIM(CAST({col_id} AS VARCHAR)) != '')",
            referenced,
        )
    if agg == "zero_or_blank":
        return (
            f"({col_id} IS NULL OR TRIM(CAST({col_id} AS VARCHAR)) = '' OR TRY_CAST({col_id} AS DOUBLE) = 0)",
            referenced,
        )
    if agg == "not_zero_or_blank":
        return (
            f"({col_id} IS NOT NULL AND TRIM(CAST({col_id} AS VARCHAR)) != '' AND TRY_CAST({col_id} AS DOUBLE) IS DISTINCT FROM 0)",
            referenced,
        )

    # --- Resolve the RHS ---
    if agg in BETWEEN_AGGREGATORS:
        val_min = cond.get("value_min", "")
        val_max = cond.get("value_max", "")
        
        if val_type == "column":
            if not val_min or not val_max:
                raise ValueError(f"Min and max columns cannot be empty for '{agg}'")
            if val_min not in columns:
                raise ValueError(f"Column '{val_min}' does not exist")
            if val_max not in columns:
                raise ValueError(f"Column '{val_max}' does not exist")
            rhs_min = _safe_ident(val_min)
            rhs_max = _safe_ident(val_max)
            referenced.extend([val_min, val_max])
            sql_rhs_min = f"TRY_CAST({rhs_min} AS DOUBLE)"
            sql_rhs_max = f"TRY_CAST({rhs_max} AS DOUBLE)"
        else:
            if val_min is None or val_min == "" or val_max is None or val_max == "":
                raise ValueError(f"Min and Max values cannot be empty for '{agg}'")
            try:
                sql_rhs_min = _sql_number_literal(val_min)
                sql_rhs_max = _sql_number_literal(val_max)
            except ValueError:
                sql_rhs_min = f"TRY_CAST({_sql_string_literal(str(val_min))} AS DOUBLE)"
                sql_rhs_max = f"TRY_CAST({_sql_string_literal(str(val_max))} AS DOUBLE)"
                
        sql_lhs = f"TRY_CAST({col_id} AS DOUBLE)"
        if agg == "between":
            return f"({sql_lhs} BETWEEN {sql_rhs_min} AND {sql_rhs_max})", referenced
        else:
            return f"({sql_lhs} NOT BETWEEN {sql_rhs_min} AND {sql_rhs_max})", referenced

    if val_type == "column":
        if not val:
            raise ValueError("Column reference cannot be empty")
        if val not in columns:
            raise ValueError(f"Column '{val}' does not exist in master file")
        rhs = _safe_ident(val)
        referenced.append(val)
    elif val_type in ("value", "text", "number"):
        if val is None or val == "":
            raise ValueError(f"Value cannot be empty for aggregator '{agg}'")
        if agg in NUMERIC_AGGREGATORS:
            try:
                rhs = _sql_number_literal(val)
            except ValueError:
                # Fall back to string compare rather than failing
                rhs = _sql_string_literal(str(val))
        else:
            rhs = _sql_string_literal(str(val))
    else:
        raise ValueError(f"Unknown value_type '{val_type}'")

    # --- Render the comparison ---
    if agg in NUMERIC_AGGREGATORS:
        sql_lhs = f"TRY_CAST({col_id} AS DOUBLE)"
        try:
            sql_rhs = _sql_number_literal(val) if val_type in ("value", "text", "number") else f"TRY_CAST({rhs} AS DOUBLE)"
        except ValueError:
            sql_rhs = f"TRY_CAST({rhs} AS DOUBLE)"
        return f"({sql_lhs} {agg} {sql_rhs})", referenced

    if agg in EQUALITY_AGGREGATORS:
        sql_lhs = f"CAST({col_id} AS VARCHAR)"
        if val_type == "column":
            sql_rhs = f"CAST({rhs} AS VARCHAR)"
        else:
            sql_rhs = _sql_string_literal(str(val))
        return f"({sql_lhs} {agg} {sql_rhs})", referenced

    if agg in TEXT_AGGREGATORS:
        sql_lhs = f"CAST({col_id} AS VARCHAR)"
        if val_type == "column":
            rhs_expr = f"CAST({rhs} AS VARCHAR)"
        else:
            rhs_expr = _sql_string_literal(str(val))
        if agg == "starts_with":
            return f"({sql_lhs} LIKE {rhs_expr} || '%')", referenced
        if agg == "ends_with":
            return f"({sql_lhs} LIKE '%' || {rhs_expr})", referenced
        if agg == "contains":
            return f"({sql_lhs} LIKE '%' || {rhs_expr} || '%')", referenced

    # Should never reach here
    raise ValueError(f"Unhandled aggregator '{agg}'")


# ---------------------------------------------------------------------------
# Branch (true / false / group-value) rendering
# ---------------------------------------------------------------------------

def _render_branch(branch: Optional[Dict[str, Any]], columns: List[str]) -> Tuple[str, List[str]]:
    """Render a true/false/group-value branch.

    branch = { "type": "value" | "text" | "column" | "number", "value": "..." }
    """
    if branch is None:
        return ("''", [])

    btype = (branch.get("type") or "value").lower()
    val = branch.get("value", "")

    if btype == "column":
        if not val:
            raise ValueError("Column branch must specify a column name")
        if val not in columns:
            raise ValueError(f"Column '{val}' does not exist in master file")
        return (_safe_ident(val), [val])

    if btype in ("value", "text", "number"):
        if val is None or val == "":
            return ("''", [])
        # Auto-detect numeric strings
        if btype == "number" or (btype == "value" and _looks_numeric(val)):
            try:
                return (_sql_number_literal(val), [])
            except ValueError:
                pass
        return (_sql_string_literal(str(val)), [])

    raise ValueError(f"Unknown branch type '{btype}'")


def _looks_numeric(v: Any) -> bool:
    if isinstance(v, (int, float)):
        return True
    if not isinstance(v, str):
        return False
    s = v.strip()
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Multi-group builder
# ---------------------------------------------------------------------------

def _render_group(group: Dict[str, Any], columns: List[str], group_index: int) -> Tuple[str, List[str]]:
    """Render one WHEN arm:  WHEN (cond_1 AND/OR cond_2) THEN <value>"""
    if not isinstance(group, dict):
        raise ValueError(f"Group {group_index} must be an object")

    conds = group.get("conditions") or []
    if not isinstance(conds, list) or not conds:
        raise ValueError(f"Group {group_index} needs at least one condition")

    logic = (group.get("logic") or "AND").upper()
    if logic not in ("AND", "OR"):
        raise ValueError(f"Group {group_index}: logic must be 'AND' or 'OR'")

    fragments: List[str] = []
    refs: List[str] = []
    for c in conds:
        f, r = _render_condition(c, columns)
        fragments.append(f)
        refs.extend(r)

    joiner = " AND " if logic == "AND" else " OR "
    when_sql = joiner.join(fragments)

    # Group value (what gets written when this group matches)
    group_value = group.get("value") or {"type": "value", "value": ""}
    value_sql, value_refs = _render_branch(group_value, columns)
    refs.extend(value_refs)

    arm = f"WHEN {when_sql} THEN {value_sql}"
    return arm, refs


def build_groups_if_sql(payload: Dict[str, Any], columns: List[str]) -> Tuple[str, List[str]]:
    """Build the multi-group SQL CASE expression.

    Payload shape:
        {
            "groups": [
                {"logic": "AND"|"OR", "conditions": [...], "value": {type, value}},
                ...
            ],
            "false_value": {type, value}
        }
    """
    if not isinstance(payload, dict):
        raise ValueError("IF payload must be an object")

    groups = payload.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("IF requires at least one group")

    false_branch = payload.get("false_value") or {"type": "value", "value": ""}

    arms: List[str] = []
    all_refs: List[str] = []
    for idx, g in enumerate(groups, start=1):
        arm, refs = _render_group(g, columns, idx)
        arms.append(arm)
        all_refs.extend(refs)

    false_sql, false_refs = _render_branch(false_branch, columns)
    all_refs.extend(false_refs)

    full_sql = "CASE\n  " + "\n  ".join(arms) + f"\n  ELSE {false_sql}\nEND"

    # de-dup referenced columns, preserve order
    seen = set()
    deduped: List[str] = []
    for c in all_refs:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    return full_sql, deduped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_if_sql(payload: Dict[str, Any], columns: List[str]) -> Tuple[str, List[str]]:
    """Build the SQL CASE expression for an IF_CONDITION formula.

    Auto-detects single-group vs multi-group payload shape and delegates to
    the appropriate builder.  Both shapes return (sql_expression, referenced_columns).
    """
    if not isinstance(payload, dict):
        raise ValueError("IF payload must be an object")

    # Multi-group path (new)
    if isinstance(payload.get("groups"), list):
        return build_groups_if_sql(payload, columns)

    # Legacy single-group path
    conditions = payload.get("conditions") or []
    if not conditions:
        raise ValueError("IF requires at least one condition")
    if not isinstance(conditions, list):
        raise ValueError("'conditions' must be a list")

    logic = (payload.get("logic") or "AND").upper()
    if logic not in ("AND", "OR"):
        raise ValueError("logic must be 'AND' or 'OR'")

    true_branch = payload.get("true_value") or {"type": "value", "value": "TRUE"}
    false_branch = payload.get("false_value") or {"type": "value", "value": ""}

    fragments = []
    referenced: List[str] = []
    for cond in conditions:
        frag, refs = _render_condition(cond, columns)
        fragments.append(frag)
        referenced.extend(refs)

    joiner = " AND " if logic == "AND" else " OR "
    when_sql = joiner.join(fragments)

    true_sql, true_refs = _render_branch(true_branch, columns)
    false_sql, false_refs = _render_branch(false_branch, columns)
    referenced.extend(true_refs)
    referenced.extend(false_refs)

    full_sql = f"CASE WHEN {when_sql} THEN {true_sql} ELSE {false_sql} END"

    # de-dup referenced columns, preserve order
    seen = set()
    deduped: List[str] = []
    for c in referenced:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    return full_sql, deduped


def validate_if_payload(payload: Dict[str, Any], columns: List[str]) -> Dict[str, Any]:
    """Validate an IF payload without executing it.  Mirrors the
    validate_formula() return shape used by the rest of the codebase.
    """
    try:
        sql, cols = build_if_sql(payload, columns)
        return {"valid": True, "sql": sql, "columns": cols}
    except ValueError as e:
        return {
            "valid": False,
            "error": str(e),
            "suggestion": "Check column names, aggregators, values, and position-operator parameters.",
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Unexpected error: {e}",
            "suggestion": "Verify the IF condition configuration.",
        }