import re
with open('backend/main.py', 'r') as f:
    text = f.read()
match = re.search(r'@app\.post\("/api/master/\{folder_id\}/rows/delete"\).*?def.*?(?=^\s*@app|^\s*def)', text, re.DOTALL | re.MULTILINE)
if match: print(match.group(0))
