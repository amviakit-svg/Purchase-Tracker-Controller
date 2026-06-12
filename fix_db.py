import sqlite3
import os
db_path = 'data/metadata.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE modules SET name='Website module', code='WEBSITE' WHERE id=1;")
    conn.commit()
    conn.close()
    print("Updated db")
else:
    print("not found")
