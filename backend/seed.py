import sqlite3
import os

DB_PATH = os.path.join('data', 'metadata.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Seed company 1
cursor.execute("INSERT OR IGNORE INTO companies (id, name, code) VALUES (1, 'Default Company', 'DEFAULT_COMP')")
# Seed module 1
cursor.execute("INSERT OR IGNORE INTO modules (id, name, code) VALUES (1, 'Default module', 'DEFAULT_MOD')")
# Seed company_module 1
cursor.execute("INSERT OR IGNORE INTO company_modules (id, company_id, module_id) VALUES (1, 1, 1)")
# Seed user 1
cursor.execute("INSERT OR IGNORE INTO users (id, email, password_hash, name, role, company_id) VALUES (1, 'admin@default.com', 'hash', 'Admin', 'admin', 1)")

# Delete others
cursor.execute("DELETE FROM companies WHERE id != 1")
cursor.execute("DELETE FROM modules WHERE id != 1")
cursor.execute("DELETE FROM company_modules WHERE id != 1")
cursor.execute("DELETE FROM users WHERE id != 1")

conn.commit()
conn.close()
print("Database seeded and cleaned.")
