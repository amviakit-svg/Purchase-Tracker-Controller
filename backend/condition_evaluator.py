import pandas as pd
import numpy as np

def evaluate_condition_vectorized(df: pd.DataFrame, cond: dict) -> pd.Series:
    """
    Evaluates a single IF condition dict against a DataFrame and returns a boolean mask.
    Supports advanced IF_AGG_OPTIONS and column vs value comparisons.
    """
    if df.empty:
        return pd.Series(dtype=bool)

    cond_col = cond.get('column', '')
    if not cond_col or cond_col not in df.columns:
        return pd.Series([False] * len(df), index=df.index)

    operator = cond.get('operator', '')
    
    # Map legacy operators if any somehow made it here
    legacy_map = {
        'equal_to': '=', 'greater_than': '>', 'smaller_than': '<', 
        'not_equal_to': '!=', 'begin_with': 'starts_with', 
        'end_with': 'ends_with', 'contain': 'contains', 'not_contain': 'not_contain'
    }
    operator = legacy_map.get(operator, operator)
    
    col_data_raw = df[cond_col]
    col_data = col_data_raw.astype(str).str.strip()
    mask = pd.Series([False] * len(df), index=df.index)

    # Base blanks
    is_blank = (col_data == '') | col_data_raw.isna() | col_data.isin(['nan', 'null', 'none', 'na', 'n/a', '-'])
    
    if operator == 'blank':
        return is_blank
    elif operator == 'not_blank':
        return ~is_blank
    elif operator == 'zero_or_blank':
        is_zero = pd.to_numeric(col_data_raw, errors='coerce') == 0
        return is_blank | is_zero
    elif operator == 'not_zero_or_blank':
        is_zero = pd.to_numeric(col_data_raw, errors='coerce') == 0
        return ~(is_blank | is_zero)
        
    vtype = cond.get('value_type', 'value')
    
    def get_comparison_series(val_key='value'):
        val = cond.get(val_key, '')
        if vtype == 'column':
            if val in df.columns:
                return df[val].astype(str).str.strip(), pd.to_numeric(df[val], errors='coerce')
            else:
                return pd.Series([''] * len(df), index=df.index), pd.Series([float('nan')] * len(df), index=df.index)
        else:
            return pd.Series([str(val)] * len(df), index=df.index), pd.Series([pd.to_numeric(val, errors='coerce')] * len(df), index=df.index)

    val_str, val_num = get_comparison_series('value')
    col_num = pd.to_numeric(col_data_raw, errors='coerce')

    # Position extraction
    if operator in ['left_eq', 'right_eq', 'mid_eq']:
        pos_op = cond.get('pos_op', '=')
        pos_op = legacy_map.get(pos_op, pos_op)
        pos_len = int(cond.get('pos_len', 0) or 0)
        
        if operator == 'left_eq':
            extracted = col_data.str[:pos_len]
        elif operator == 'right_eq':
            extracted = col_data.str[-pos_len:] if pos_len > 0 else pd.Series([''] * len(df), index=df.index)
        else: # mid_eq
            pos_start = int(cond.get('pos_start', 1) or 1) - 1 # 1-indexed to 0-indexed
            pos_start = max(0, pos_start)
            extracted = col_data.str[pos_start:pos_start+pos_len]
            
        ext_num = pd.to_numeric(extracted, errors='coerce')
        
        if pos_op == '=':
            numeric_match = (ext_num - val_num).abs() <= 1e-9
            string_match = extracted.str.lower() == val_str.str.lower()
            return numeric_match.fillna(string_match)
        elif pos_op == '!=':
            numeric_ne = (ext_num - val_num).abs() > 1e-9
            string_ne = extracted.str.lower() != val_str.str.lower()
            return numeric_ne.fillna(string_ne)
        elif pos_op == '>':
            return ext_num > val_num
        elif pos_op == '<':
            return ext_num < val_num
        elif pos_op == '>=':
            return ext_num >= val_num
        elif pos_op == '<=':
            return ext_num <= val_num

    # Normal operators
    if operator == '=':
        numeric_match = (col_num - val_num).abs() <= 1e-9
        string_match = col_data.str.lower() == val_str.str.lower()
        return numeric_match.fillna(string_match)
    elif operator == '!=':
        numeric_ne = (col_num - val_num).abs() > 1e-9
        string_ne = col_data.str.lower() != val_str.str.lower()
        return numeric_ne.fillna(string_ne)
    elif operator == '>':
        return col_num > val_num
    elif operator == '<':
        return col_num < val_num
    elif operator == '>=':
        return col_num >= val_num
    elif operator == '<=':
        return col_num <= val_num
    elif operator == 'starts_with':
        if vtype == 'column':
            return pd.Series([str(t).startswith(str(v)) if str(v) else False for t, v in zip(col_data.str.lower(), val_str.str.lower())], index=df.index)
        else:
            return col_data.str.lower().str.startswith(str(val_str.iloc[0]).lower(), na=False)
    elif operator == 'ends_with':
        if vtype == 'column':
            return pd.Series([str(t).endswith(str(v)) if str(v) else False for t, v in zip(col_data.str.lower(), val_str.str.lower())], index=df.index)
        else:
            return col_data.str.lower().str.endswith(str(val_str.iloc[0]).lower(), na=False)
    elif operator == 'contains':
        if vtype == 'column':
            return pd.Series([str(v) in str(t) if str(v) else False for t, v in zip(col_data.str.lower(), val_str.str.lower())], index=df.index)
        else:
            return col_data.str.lower().str.contains(str(val_str.iloc[0]).lower(), regex=False, na=False)
    elif operator == 'not_contain':
        if vtype == 'column':
            return pd.Series([str(v) not in str(t) if str(v) else True for t, v in zip(col_data.str.lower(), val_str.str.lower())], index=df.index)
        else:
            return ~col_data.str.lower().str.contains(str(val_str.iloc[0]).lower(), regex=False, na=False)
    elif operator in ('between', 'not_between'):
        val_min_str, val_min_num = get_comparison_series('value_min')
        val_max_str, val_max_num = get_comparison_series('value_max')
        if operator == 'between':
            return (col_num >= val_min_num) & (col_num <= val_max_num)
        else:
            return (col_num < val_min_num) | (col_num > val_max_num)
        
    return mask
