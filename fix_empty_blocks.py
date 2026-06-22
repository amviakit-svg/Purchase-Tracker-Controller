import re

def fix_empty_blocks(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out_lines.append(line)
        
        stripped = line.strip()
        if stripped in ('finally:', 'try:', 'except:', 'except Exception:'):
            # Check the next non-empty line
            j = i + 1
            is_empty = False
            while j < len(lines):
                if lines[j].strip() == '':
                    j += 1
                    continue
                next_indent = len(lines[j]) - len(lines[j].lstrip())
                curr_indent = len(line) - len(line.lstrip())
                if next_indent <= curr_indent:
                    is_empty = True
                break
            
            # Also if EOF
            if j == len(lines):
                is_empty = True
                
            if is_empty:
                indent = len(line) - len(line.lstrip())
                out_lines.append(" " * (indent + 4) + "pass\n")
                
        i += 1
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

fix_empty_blocks('backend/database.py.patched')
fix_empty_blocks('backend/main.py.patched')
