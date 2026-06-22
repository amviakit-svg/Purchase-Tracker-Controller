import sys

def fix_empty_finally(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if line.strip() == 'finally:':
            if i + 1 < len(lines) and lines[i+1].strip() == '':
                # It's an empty finally block.
                # Just add pass
                out_lines.append(line)
                indent = len(line) - len(line.lstrip())
                out_lines.append(" " * (indent + 4) + "pass\n")
                i += 1
                continue
            elif i + 1 < len(lines) and lines[i+1].strip() == 'finally:':
                out_lines.append(line)
                indent = len(line) - len(line.lstrip())
                out_lines.append(" " * (indent + 4) + "pass\n")
                i += 1
                continue
                
        out_lines.append(line)
        i += 1
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

fix_empty_finally('backend/database.py.patched')
fix_empty_finally('backend/main.py.patched')
