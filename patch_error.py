import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Patch read-only endpoints
read_only_targets = [
    'async def preview_master(',
    'async def get_master_stats(',
    'async def get_source_files(',
    'async def get_master_columns('
]

lines = text.split('\n')
in_readonly_endpoint = False
for i, line in enumerate(lines):
    if any(target in line for target in read_only_targets):
        in_readonly_endpoint = True
    elif line.startswith('def ') or line.startswith('async def ') or line.startswith('@app.'):
        if not any(target in line for target in read_only_targets) and (line.startswith('def ') or line.startswith('async def ')):
            in_readonly_endpoint = False
    
    if in_readonly_endpoint and 'duckdb.connect(' in line and 'read_only' not in line and '_mig_conn' not in line:
        lines[i] = line.replace('duckdb.connect(master[\'db_path\'])', 'duckdb.connect(master[\'db_path\'], read_only=True)')

text = '\n'.join(lines)

# 2. Patch exception handlers to close connections
def repl_except_http(m):
    return m.group(1) + '''except HTTPException:
        try:
            if 'conn' in locals() and hasattr(conn, 'close'): conn.close()
            if 'sec_conn' in locals() and hasattr(sec_conn, 'close'): sec_conn.close()
            if 'duck_conn' in locals() and hasattr(duck_conn, 'close'): duck_conn.close()
            if 'conn_rw' in locals() and hasattr(conn_rw, 'close'): conn_rw.close()
        except: pass
        raise'''

def repl_except_exc(m):
    return m.group(1) + '''except Exception as e:
        import traceback
        with open('error_log.txt', 'a') as ef:
            ef.write(traceback.format_exc() + '\\n')
        try:
            if 'conn' in locals() and hasattr(conn, 'close'): conn.close()
            if 'sec_conn' in locals() and hasattr(sec_conn, 'close'): sec_conn.close()
            if 'duck_conn' in locals() and hasattr(duck_conn, 'close'): duck_conn.close()
            if 'conn_rw' in locals() and hasattr(conn_rw, 'close'): conn_rw.close()
        except: pass
        raise HTTPException(status_code=500, detail=str(e))'''

text = re.sub(r'([ \t]+)except HTTPException:\n[ \t]+raise', repl_except_http, text)
text = re.sub(r'([ \t]+)except Exception as e:\n[ \t]+raise HTTPException\(status_code=500, detail=str\(e\)\)', repl_except_exc, text)

# 3. Specifically patch apply_master_formula exception block
replacement_formula = '''    except Exception as e:
        import traceback
        with open('error_log.txt', 'a') as ef:
            ef.write(traceback.format_exc() + '\\n')
        logger.error(f"Formula error: {e}")
        try:
            if 'conn' in locals() and hasattr(conn, 'close'): conn.close()
            if 'sec_conn' in locals() and hasattr(sec_conn, 'close'): sec_conn.close()
        except: pass
        raise HTTPException(status_code=500, detail=str(e))'''

text = re.sub(r'([ \t]+)except Exception as e:\n[ \t]+logger\.error\(f\"Formula error: \{e\}\"\)\n[ \t]+raise HTTPException\(status_code=500, detail=str\(e\)\)', replacement_formula, text)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Patched successfully')
