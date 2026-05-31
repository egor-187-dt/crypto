import sqlite3
import os
import json

# Находим config.json напрямую
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data')
config_file = os.path.join(data_dir, 'config.json')

db_path = "data/vault.db"

if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config_data = json.load(f)
        db_path = config_data.get("db_path", "data/vault.db")

print(f"DB path: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, title, username, deleted FROM vault_entries")
rows = cursor.fetchall()

print(f"\nВсего записей в БД: {len(rows)}")
for row in rows:
    print(f"ID: {row[0]}, Title: {row[1]}, Username: {row[2]}, Deleted: {row[3]}")

conn.close()