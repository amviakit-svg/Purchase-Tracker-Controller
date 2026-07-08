import sqlite3
conn = sqlite3.connect('data/metadata.db')
cursor = conn.cursor()
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('master_files', 'master_file_configs', 'modules');")
for row in cursor.fetchall():
    print(row[0] + '\n')
