import codecs

with codecs.open('backend/main.py', 'r', 'utf-8') as f:
    text = f.read()

# Find the start of the bad block (from "def process_rules_background():" at line 6885)
bad_idx = text.rfind('def process_rules_background():', text.find('processing_status["progress"] = "completed"'))

if bad_idx != -1:
    good_text = text[:bad_idx]
    
    # We need to add the correct `finally` block back
    finally_block = """    except Exception as e:
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
            processing_status["is_processing"] = False
"""
    
    # Append the rest of the file which should start from @app.get("/api/primary/source-files")
    rest_idx = text.find('@app.get("/api/primary/source-files")')
    if rest_idx != -1:
        good_text += finally_block + "\n" + text[rest_idx:]
        
        with codecs.open('backend/main.py', 'w', 'utf-8') as f:
            f.write(good_text)
        print("Patched successfully")
    else:
        print("Could not find rest_idx")
else:
    print("Could not find bad_idx")
