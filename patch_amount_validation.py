import re
import os
import json

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        # --- Check Amount Validation Constraints ---
        if cid is not None and mid is not None:
            v_conn = get_db_connection()
            try:
                invalid_masters = v_conn.execute(\"\"\"
                    SELECT f.name, m.validation_status 
                    FROM master_files m
                    JOIN folders f ON m.folder_id = f.id
                    JOIN master_file_configs c ON m.folder_id = c.folder_id
                    WHERE m.company_id = ? AND m.module_id = ?
                      AND c.amount_validation_enabled = 1
                      AND m.validation_status != 'Matched'
                \"\"\", (cid, mid)).fetchall()
                if invalid_masters:
                    msg = "due to rule not matching of 'rule - Validation of Amount'"
                    processing_status["result"] = {"success": False, "message": msg}
                    processing_status["error"] = msg
                    processing_status["is_processing"] = False
                    processing_status["progress"] = "error"
                    return
            except Exception as e:
                logger.error(f"Error checking amount validation block: {e}")
            finally:
                v_conn.close()
        # -------------------------------------------

        
        # Load rules scoped to company/module if authenticated context exists
        conn = get_db_connection()
        if cid is not None and mid is not None:
            all_rules = conn.execute(
                "SELECT * FROM rules WHERE company_id = ? AND module_id = ? AND validation_id = ? ORDER BY phase, id",
                (cid, mid, vid)
            ).fetchall()
        else:
            all_rules = conn.execute("SELECT * FROM rules WHERE validation_id = ? ORDER BY phase, id", (vid,)).fetchall()
        conn.close()
        
        if not all_rules:
            processing_status["result"] = {"success": False, "message": "No rules configured"}
            processing_status["is_processing"] = False
            processing_status["progress"] = "completed"
            return

        phase1_rules = [dict(r) for r in all_rules if r['phase'] == 1]
        phase2_rules = [dict(r) for r in all_rules if r['phase'] == 2]
        phase3_rules = [dict(r) for r in all_rules if r['phase'] == 3]

        # FIX: Only use the most recent rule record for each phase!
        # The database keeps historical saves, but we should only execute the latest configuration.
        phase1_rules = [phase1_rules[-1]] if phase1_rules else []
        phase2_rules = [phase2_rules[-1]] if phase2_rules else []
        phase3_rules = [phase3_rules[-1]] if phase3_rules else []

        # FIX: For Validation 1 and 3, Phase 2 (Matching Rules) is intentionally hidden in the UI.
        # Do NOT load or process Phase 2 rules for these validations, even if they exist in DB.
        # The "Phase 2" the user sees in Val 1/3 is actually the renamed Phase 3 (Remarks).
        if vid in (1, 3):
            phase2_rules = []
        if not phase1_rules:
            processing_status["result"] = {"success": False, "message": "No Phase 1 (Primary Data) rule configured"}
            processing_status["is_processing"] = False
            processing_status["progress"] = "completed"
            return"""

new_block = """        # Load rules scoped to company/module if authenticated context exists
        conn = get_db_connection()
        if cid is not None and mid is not None:
            all_rules = conn.execute(
                "SELECT * FROM rules WHERE company_id = ? AND module_id = ? AND validation_id = ? ORDER BY phase, id",
                (cid, mid, vid)
            ).fetchall()
        else:
            all_rules = conn.execute("SELECT * FROM rules WHERE validation_id = ? ORDER BY phase, id", (vid,)).fetchall()
        conn.close()
        
        if not all_rules:
            processing_status["result"] = {"success": False, "message": "No rules configured"}
            processing_status["is_processing"] = False
            processing_status["progress"] = "completed"
            return

        phase1_rules = [dict(r) for r in all_rules if r['phase'] == 1]
        phase2_rules = [dict(r) for r in all_rules if r['phase'] == 2]
        phase3_rules = [dict(r) for r in all_rules if r['phase'] == 3]

        # FIX: Only use the most recent rule record for each phase!
        # The database keeps historical saves, but we should only execute the latest configuration.
        phase1_rules = [phase1_rules[-1]] if phase1_rules else []
        phase2_rules = [phase2_rules[-1]] if phase2_rules else []
        phase3_rules = [phase3_rules[-1]] if phase3_rules else []

        # FIX: For Validation 1 and 3, Phase 2 (Matching Rules) is intentionally hidden in the UI.
        # Do NOT load or process Phase 2 rules for these validations, even if they exist in DB.
        # The "Phase 2" the user sees in Val 1/3 is actually the renamed Phase 3 (Remarks).
        if vid in (1, 3):
            phase2_rules = []
        if not phase1_rules:
            processing_status["result"] = {"success": False, "message": "No Phase 1 (Primary Data) rule configured"}
            processing_status["is_processing"] = False
            processing_status["progress"] = "completed"
            return

        # --- Check Amount Validation Constraints ---
        if cid is not None and mid is not None:
            # Extract folder IDs used in rules for this specific validation
            used_master_folder_ids = set()
            
            def extract_folder_id(fid, is_master=False):
                if isinstance(fid, str) and fid.startswith('master_'):
                    try: return int(fid.replace('master_', ''))
                    except: return None
                elif is_master and str(fid).isdigit():
                    return int(fid)
                return None

            for rule_list in [phase1_rules, phase2_rules, phase3_rules]:
                for rule in rule_list:
                    try:
                        import json
                        cfg = json.loads(rule['config'])
                        if isinstance(cfg, str): cfg = json.loads(cfg)
                        if not isinstance(cfg, dict): continue
                        
                        fid = extract_folder_id(cfg.get('file_id'), cfg.get('is_master'))
                        if fid: used_master_folder_ids.add(fid)
                        
                        src = extract_folder_id(cfg.get('source_file'))
                        if src: used_master_folder_ids.add(src)
                    except: pass
            
            if used_master_folder_ids:
                v_conn = get_db_connection()
                try:
                    placeholders = ','.join('?' for _ in used_master_folder_ids)
                    params = [cid, mid] + list(used_master_folder_ids)
                    
                    invalid_masters = v_conn.execute(f\"\"\"
                        SELECT f.name, m.validation_status 
                        FROM master_files m
                        JOIN folders f ON m.folder_id = f.id
                        JOIN master_file_configs c ON m.folder_id = c.folder_id
                        WHERE m.company_id = ? AND m.module_id = ?
                          AND c.amount_validation_enabled = 1
                          AND m.validation_status != 'Matched'
                          AND m.folder_id IN ({placeholders})
                    \"\"\", params).fetchall()
                    
                    if invalid_masters:
                        msg = "due to rule not matching of 'rule - Validation of Amount'"
                        processing_status["result"] = {"success": False, "message": msg}
                        processing_status["error"] = msg
                        processing_status["is_processing"] = False
                        processing_status["progress"] = "error"
                        return
                except Exception as e:
                    logger.error(f"Error checking amount validation block: {e}")
                finally:
                    v_conn.close()
        # -------------------------------------------"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('backend/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Old block not found!")
