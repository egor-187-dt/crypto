import sqlite3
import os

db_path = "data/vault.db"
if os.path.exists(db_path):
    os.remove(db_path)
    print("Удалили старую БД")

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE vault_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        username TEXT,
        encrypted_data BLOB,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        deleted INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE master_password (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL
    )
''')

conn.commit()

test_blob = b'test_blob_12345'
now = "2024-01-01T12:00:00"

cursor.execute(
    "INSERT INTO vault_entries (encrypted_data, title, username, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
    (test_blob, "Тест", "user", now, now)
)
conn.commit()

entry_id = cursor.lastrowid
print(f"Запись создана с ID: {entry_id}")

cursor.execute("SELECT id, title, username FROM vault_entries")
rows = cursor.fetchall()
print(f"Записи в БД: {rows}")

conn.close()
print("Готово!")