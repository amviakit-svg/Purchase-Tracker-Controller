import sys
with open('backend/auto_sync.py', 'r') as f:
    content = f.read()

target = """                    except Exception as ne:
                        pass
                
                            sheet_names = wb.sheetnames
                            wb.close()"""

replacement = """                    except Exception as ne:
                        pass
                
            # 2. ADD FILES
            if files_to_add:
                # Mark as processing
                for f in files_to_add:
                    set_file_sync_status(f['id'], 'in_processing')
                    
                all_new_data = []
                for f in files_to_add:
                    try:
                        file_format = f.get('format', '').upper()
                        file_path = f['file_path']
                        original_name = f['original_name']
                        
                        # Read the file
                        if file_format == 'CSV':
                            sheet_names = ['Sheet1']
                        else:
                            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                            sheet_names = wb.sheetnames
                            wb.close()"""

content = content.replace(target, replacement)
with open('backend/auto_sync.py', 'w') as f:
    f.write(content)
print("Patched!")
