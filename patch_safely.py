import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I want to find the end of process_rules_background
# The last part of process_rules_background is the except block
pattern = re.compile(
    r'(    except Exception as e:\n'
    r'        import traceback\n'
    r'        error_msg = f"Processing error: \{str\(e\)\}\\n\{traceback\.format_exc\(\)\}"\n'
    r'        logger\.error\(error_msg\)\n'
    r'        with processing_lock:\n'
    r'            from database import add_notification\n'
    r'            cid = processing_status\.get\("company_id"\)\n'
    r'            mid = processing_status\.get\("module_id"\)\n'
    r'            uid = processing_status\.get\("user_id"\)\n'
    r'            if cid and mid:\n'
    r'                add_notification\(cid, mid, \'error\', f"Processing failed: \{str\(e\)\[:100\]\}\.\.\.", "\?page=process", user_id=uid\)\n'
    r'            processing_status\["error"\] = str\(e\)\n'
    r'            processing_status\["result"\] = \{"success": False, "message": str\(e\)\}\n'
    r'            processing_status\["progress"\] = "error"\n'
    r'            processing_status\["is_processing"\] = False)',
    re.MULTILINE
)

replacement = """    except Exception as e:
        import traceback
        error_msg = f"Processing error: {str(e)}\\n{traceback.format_exc()}"
        logger.error(error_msg)
        try:
            with processing_lock:
                from database import add_notification
                cid = processing_status.get("company_id")
                mid = processing_status.get("module_id")
                uid = processing_status.get("user_id")
                if cid and mid:
                    add_notification(cid, mid, 'error', f"Processing failed: {str(e)[:100]}...", "?page=process", user_id=uid)
                processing_status["error"] = str(e)
                processing_status["result"] = {"success": False, "message": str(e)}
                processing_status["progress"] = "error"
        except Exception as inner_e:
            logger.error(f"Error inside exception handler: {inner_e}")
    finally:
        with processing_lock:
            processing_status["is_processing"] = False"""

if pattern.search(content):
    content = pattern.sub(replacement, content)
    with open('backend/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully!")
else:
    print("Could not find the target block.")
