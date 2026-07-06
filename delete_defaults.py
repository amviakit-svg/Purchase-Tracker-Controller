import sqlite3

conn = sqlite3.connect('data/metadata.db')
cursor = conn.cursor()

# Delete ALL filters and cards assigned to E-Retail (module_id = 1)
cursor.execute("DELETE FROM dynamic_filters WHERE module_id = 1")
filters_deleted = cursor.rowcount

cursor.execute("DELETE FROM dynamic_cards WHERE module_id = 1")
cards_deleted = cursor.rowcount

conn.commit()
print(f"Deleted {filters_deleted} filters and {cards_deleted} cards from E-Retail.")

conn.close()
