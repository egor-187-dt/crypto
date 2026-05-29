import sqlite3
import os

db_path = "data/vault.db"

if not os.path.exists(db_path):
    print("БД не найдена")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Проверяем какие колонки есть
cursor.execute("PRAGMA table_info(vault_entries)")
columns = cursor.fetchall()
col_names = [col[1] for col in columns]
print("Существующие колонки:", col_names)

# Добавляем недостающие колонки
if 'url' not in col_names:
    cursor.execute("ALTER TABLE vault_entries ADD COLUMN url TEXT")
    print("Добавлена колонка url")

if 'notes' not in col_names:
    cursor.execute("ALTER TABLE vault_entries ADD COLUMN notes TEXT")
    print("Добавлена колонка notes")

if 'tags' not in col_names:
    cursor.execute("ALTER TABLE vault_entries ADD COLUMN tags TEXT")
    print("Добавлена колонка tags")

if 'encrypted_data' not in col_names:
    cursor.execute("ALTER TABLE vault_entries ADD COLUMN encrypted_data BLOB")
    print("Добавлена колонка encrypted_data")

if 'deleted' not in col_names:
    cursor.execute("ALTER TABLE vault_entries ADD COLUMN deleted INTEGER DEFAULT 0")
    print("Добавлена колонка deleted")

if 'deleted_at' not in col_names:
    cursor.execute("ALTER TABLE vault_entries ADD COLUMN deleted_at TIMESTAMP")
    print("Добавлена колонка deleted_at")

if 'version' not in col_names:
    cursor.execute("ALTER TABLE vault_entries ADD COLUMN version INTEGER DEFAULT 2")
    print("Добавлена колонка version")

conn.commit()
conn.close()

print("\nТаблица обновлена!")