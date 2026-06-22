import sys
import re

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip if get_db_connection function definition
        if line.strip().startswith('def get_db_connection'):
            out_lines.append(line)
            i += 1
            continue
            
        out_lines.append(line)
        
        match = re.search(r'^(\s*)(\w+)\s*=\s*(get_db_connection\(\)|duckdb\.connect\()', line)
        
        if match and not line.strip().startswith('#'):
            indent = len(match.group(1))
            var_name = match.group(2)
            base_indent = " " * indent
            
            out_lines.append(base_indent + "try:\n")
            
            i += 1
            body_lines = []
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip() == "":
                    body_lines.append(next_line)
                    i += 1
                    continue
                
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= indent and not next_line.strip().startswith('#'):
                    # Check if the block ended
                    # If it's a multi-line string or something weird it could break,
                    # but typically next_indent <= indent means block ended.
                    break
                
                # Remove manual close()
                if next_line.strip() in (f'{var_name}.close()',):
                    i += 1
                    continue
                
                body_lines.append("    " + next_line)
                i += 1
            
            out_lines.extend(body_lines)
            
            out_lines.append(base_indent + "finally:\n")
            out_lines.append(base_indent + "    try:\n")
            out_lines.append(base_indent + f"        {var_name}.close()\n")
            out_lines.append(base_indent + "    except Exception:\n")
            out_lines.append(base_indent + "        pass\n")
            
            continue
            
        i += 1

    with open(filepath + '.patched', 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

patch_file('backend/database.py')
patch_file('backend/main.py')
