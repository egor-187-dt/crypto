import sqlite3
from src.core.config import config

db_path = config.get("db_path", "data/vault.db")
print(f"DB path: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(vault_entries)")
columns = cursor.fetchall()

print("\nТаблица vault_entries:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()