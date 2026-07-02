with open('backend/main.py', 'r') as f:
    text = f.read()
lines = text.split('\n')
for i, line in enumerate(lines):
    if '@app.post("/api/master/{folder_id}/rows/delete")' in line:
        print(f'Start line: {i+1}')
