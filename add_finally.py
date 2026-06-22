import codecs

with codecs.open('backend/main.py', 'r', 'utf-8') as f:
    text = f.read()

target = """    except Exception as e:
        import traceback
        error_msg = f"Processing error: {str(e)}\\n{traceback.format_exc()}"
        logger.error(error_msg)
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
            processing_status["is_processing"] = False"""

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

if target in text:
    text = text.replace(target, replacement)
    with codecs.open('backend/main.py', 'w', 'utf-8') as f:
        f.write(text)
    print("Patched successfully")
else:
    print("Target not found. Doing fuzzy search...")
    for i in range(1, 10):
        print(repr(target.split('\\n')[-i]))
