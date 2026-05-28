import sqlite3
from src.core.config import config

db_path = config.get("db_path", "data/vault.db")
print(f"БД: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Проверяем колонки
cursor.execute("PRAGMA table_info(vault_entries)")
cols = cursor.fetchall()
print("Колонки в vault_entries:")
for col in cols:
    print(f"  {col[1]} ({col[2]})")

# Проверяем есть ли данные
cursor.execute("SELECT COUNT(*) FROM vault_entries")
count = cursor.fetchone()[0]
print(f"Всего записей: {count}")

conn.close()