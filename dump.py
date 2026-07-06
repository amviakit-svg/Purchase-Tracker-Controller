import sqlite3
import pandas as pd

conn = sqlite3.connect('data/metadata.db')
df_filters = pd.read_sql_query("SELECT id, module_id, field_name FROM dynamic_filters", conn)
print("=== FILTERS ===")
print(df_filters)

df_cards = pd.read_sql_query("SELECT id, module_id, card_name FROM dynamic_cards", conn)
print("\n=== CARDS ===")
print(df_cards)
conn.close()
