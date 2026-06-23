with open('backend/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Patch read-only connections
target1 = '        conn = duckdb.connect(master[\'db_path\'])\n        all_columns = conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()'
rep1 = '        conn = duckdb.connect(master[\'db_path\'], read_only=True)\n        all_columns = conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()'
text = text.replace(target1, rep1)

target2 = '        conn = duckdb.connect(master[\'db_path\'])\n\n        # Get column names first'
rep2 = '        conn = duckdb.connect(master[\'db_path\'], read_only=True)\n\n        # Get column names first'
text = text.replace(target2, rep2)

target3 = '        conn = duckdb.connect(master[\'db_path\'])\n        source_files = []'
rep3 = '        conn = duckdb.connect(master[\'db_path\'], read_only=True)\n        source_files = []'
text = text.replace(target3, rep3)

target4 = '        conn = duckdb.connect(master[\'db_path\'])\n        \n        # Total records'
rep4 = '        conn = duckdb.connect(master[\'db_path\'], read_only=True)\n        \n        # Total records'
text = text.replace(target4, rep4)

# 2. Patch except block in apply_master_formula
old_formula_except = '''    except Exception as e:
        logger.error(f"Formula error: {e}")
        raise HTTPException(status_code=500, detail=str(e))'''

new_formula_except = '''    except Exception as e:
        logger.error(f"Formula error: {e}")
        if 'conn' in locals() and hasattr(conn, 'close'):
            try: conn.close()
            except: pass
        if 'sec_conn' in locals() and hasattr(sec_conn, 'close'):
            try: sec_conn.close()
            except: pass
        raise HTTPException(status_code=500, detail=str(e))'''

text = text.replace(old_formula_except, new_formula_except)

# 3. Patch generic except block
old_generic_except = '''    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))'''

new_generic_except = '''    except Exception as e:
        if 'conn' in locals() and hasattr(conn, 'close'):
            try: conn.close()
            except: pass
        if 'sec_conn' in locals() and hasattr(sec_conn, 'close'):
            try: sec_conn.close()
            except: pass
        if 'duck_conn' in locals() and hasattr(duck_conn, 'close'):
            try: duck_conn.close()
            except: pass
        raise HTTPException(status_code=500, detail=str(e))'''

text = text.replace(old_generic_except, new_generic_except)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patch applied successfully')
