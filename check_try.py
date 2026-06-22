import codecs
import re

with codecs.open('backend/main.py', 'r', 'utf-8') as f:
    lines = f.readlines()

stack = []
for i, line in enumerate(lines):
    if not line.strip() or line.strip().startswith('#'):
        continue
    indent = len(line) - len(line.lstrip())
    
    # Remove things that closed at higher indent
    while stack and stack[-1][1] >= indent:
        if stack[-1][1] > indent:
            stack.pop()
        else:
            if line.strip().startswith('except') or line.strip().startswith('finally'):
                if stack[-1][0] == 'try':
                    stack.pop()
                else:
                    break
            else:
                stack.pop()
                
    if line.strip().startswith('try:'):
        stack.append(('try', indent, i+1))

for item in stack:
    if item[0] == 'try':
        print(f"Unclosed try at line {item[2]} with indent {item[1]}")
