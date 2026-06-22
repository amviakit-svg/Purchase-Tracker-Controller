import re

def fix_empty_try(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find "try:\n\s*except Exception:" and insert a "pass"
    # Actually, we can use regex to match try:\s*except
    
    lines = content.split('\n')
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out_lines.append(line)
        if line.strip() == 'try:':
            if i + 1 < len(lines) and lines[i+1].strip() == 'except Exception:':
                indent = len(lines[i+1]) - len(lines[i+1].lstrip())
                out_lines.append(" " * (indent + 4) + "pass")
        i += 1
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))

fix_empty_try('backend/database.py.patched')
fix_empty_try('backend/main.py.patched')
