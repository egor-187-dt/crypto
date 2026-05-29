import os
import sqlite3

db_path = "data/vault.db"

if os.path.exists(db_path):
    os.remove(db_path)
    print("Old database removed")

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE vault_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        username TEXT,
        encrypted_data BLOB NOT NULL,
        url TEXT,
        notes TEXT,
        tags TEXT,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        deleted INTEGER DEFAULT 0,
        deleted_at TIMESTAMP,
        version INTEGER DEFAULT 2
    )
''')

cursor.execute('''
    CREATE INDEX idx_vault_entries_title ON vault_entries(title)
''')
cursor.execute('''
    CREATE INDEX idx_vault_entries_updated ON vault_entries(updated_at)
''')
cursor.execute('''
    CREATE INDEX idx_vault_entries_deleted ON vault_entries(deleted)
''')

cursor.execute('''
    CREATE TABLE master_password (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE key_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_type TEXT NOT NULL,
        salt TEXT,
        hash TEXT,
        key_data TEXT,
        params TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT,
        encrypted INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        entry_id INTEGER,
        details TEXT,
        signature TEXT
    )
''')

conn.commit()
conn.close()

print("Fresh database created successfully")