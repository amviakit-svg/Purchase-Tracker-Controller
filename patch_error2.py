with open('backend/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Patch the 4 read-only connections using exact line matching or context
text = text.replace(
    '        conn = duckdb.connect(master[\'db_path\'])\n        all_columns = conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()',
    '        conn = duckdb.connect(master[\'db_path\'], read_only=True)\n        all_columns = conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()'
)
text = text.replace(
    '        conn = duckdb.connect(master[\'db_path\'])\n\n        # Get column names first',
    '        conn = duckdb.connect(master[\'db_path\'], read_only=True)\n\n        # Get column names first'
)
text = text.replace(
    '        conn = duckdb.connect(master[\'db_path\'])\n        source_files = []',
    '        conn = duckdb.connect(master[\'db_path\'], read_only=True)\n        source_files = []'
)
text = text.replace(
    '        conn = duckdb.connect(master[\'db_path\'])\n        \n        # Total records',
    '        conn = duckdb.connect(master[\'db_path\'], read_only=True)\n        \n        # Total records'
)

# 2. Patch exception block in apply_master_formula
old_except = '''    except Exception as e:
        logger.error(f"Formula error: {e}")
        raise HTTPException(status_code=500, detail=str(e))'''

new_except = '''    except Exception as e:
        import traceback
        with open('error_log.txt', 'a') as ef:
            ef.write(traceback.format_exc() + '\\n')
        logger.error(f"Formula error: {e}")
        try:
            if 'conn' in locals() and hasattr(conn, 'close'): conn.close()
            if 'sec_conn' in locals() and hasattr(sec_conn, 'close'): sec_conn.close()
        except: pass
        raise HTTPException(status_code=500, detail=str(e))'''

text = text.replace(old_except, new_except)

# 3. Patch HTTP exception
old_http = '''    except HTTPException:
        raise'''

new_http = '''    except HTTPException:
        try:
            if 'conn' in locals() and hasattr(conn, 'close'): conn.close()
            if 'sec_conn' in locals() and hasattr(sec_conn, 'close'): sec_conn.close()
        except: pass
        raise'''

text = text.replace(old_http, new_http)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched correctly!')
