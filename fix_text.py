# -*- coding: utf-8 -*-
with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('Default module', 'Website module')
with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('backend/database.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('Default module', 'Website module')
content = content.replace("'DEFAULT'", "'WEBSITE'")
with open('backend/database.py', 'w', encoding='utf-8') as f:
    f.write(content)

import sqlite3
conn = sqlite3.connect('metadata.db')
cursor = conn.cursor()
cursor.execute("UPDATE modules SET name='Website module', code='WEBSITE' WHERE id=1;")
conn.commit()
conn.close()
