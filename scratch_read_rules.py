import sqlite3
import json

conn = sqlite3.connect('data/metadata.db')
cursor = conn.cursor()
cursor.execute('SELECT config FROM rules WHERE validation_id = 1 AND phase = 3 ORDER BY id DESC LIMIT 1')
row = cursor.fetchone()
if row:
    rules = json.loads(row[0])
    for group in rules:
        for rule in group.get('remark_rules', []):
            print(f"Remark: {rule['remark']}")
            for c in rule['conditions']:
                val = c.get('value')
                if val is None:
                    val = f"{c.get('value_min')} to {c.get('value_max')}"
                print(f"  {c['column']} {c['operator']} {val}")
else:
    print('No config found')
