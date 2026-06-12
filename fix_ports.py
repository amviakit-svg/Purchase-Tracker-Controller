# -*- coding: utf-8 -*-
files_to_fix = [
    'install_service.bat',
    'restart_server.py',
    'setup.bat',
    'start_server.bat',
    'backend/main.py'
]

for file in files_to_fix:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('8000', '5000')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

print("Ports successfully updated to 5000")
