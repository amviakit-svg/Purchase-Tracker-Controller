import sqlite3
import json
conn = sqlite3.connect('data/metadata.db')
res = conn.execute("SELECT id, folder_id, target_column, payload_json FROM master_activities WHERE target_column LIKE '%Invoice Value Difference%'").fetchall()
print('Found:', res)
