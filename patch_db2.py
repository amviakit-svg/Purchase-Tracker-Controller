import sys
import ast

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
        
        # Look for conn assignment
        if ('conn = get_db_connection()' in line or 'conn = duckdb.connect' in line) and not line.strip().startswith('#'):
            indent = len(line) - len(line.lstrip())
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
                # If we hit a line that is indented less or equal to the assignment
                # AND it's not just a comment or something inside a multi-line string...
                # Well, python indentation rules apply
                if next_indent <= indent and not next_line.strip().startswith('#'):
                    # We broke out of the block!
                    break
                
                # Remove manual conn.close()
                if next_line.strip() in ('conn.close()', 'db_conn.close()'):
                    i += 1
                    continue
                
                body_lines.append("    " + next_line)
                i += 1
            
            out_lines.extend(body_lines)
            
            # Append finally block
            out_lines.append(base_indent + "finally:\n")
            out_lines.append(base_indent + "    try:\n")
            out_lines.append(base_indent + "        conn.close()\n")
            out_lines.append(base_indent + "    except Exception:\n")
            out_lines.append(base_indent + "        pass\n")
            
            continue # Already incremented i
            
        i += 1

    with open(filepath + '.patched', 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

patch_file('backend/database.py')
