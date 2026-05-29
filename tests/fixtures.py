import os
import tempfile
import sqlite3
from src.database.db import Database


class TestDBFixture:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

    def create_test_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE vault_entries (
                id TEXT PRIMARY KEY,
                title TEXT,
                username TEXT,
                encrypted_password TEXT,
                encrypted_data BLOB,
                url TEXT,
                notes TEXT,
                tags TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE master_password (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        return self.db_path

    def cleanup(self):
        import shutil
        shutil.rmtree(self.temp_dir)