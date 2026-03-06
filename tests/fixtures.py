import os
import tempfile
import sqlite3
from src.database.db import Database


class TestDBFixture:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

    def create_test_db(self):
        """Создает БД с тестовыми данными"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Создаем таблицы
        cursor.execute('''
            CREATE TABLE vault_entries (
                id INTEGER PRIMARY KEY,
                title TEXT,
                username TEXT,
                encrypted_password BLOB
            )
        ''')

        # Добавляем тестовые данные
        cursor.execute('''
            INSERT INTO vault_entries (title, username, encrypted_password)
            VALUES (?, ?, ?)
        ''', ("test", "user", b"encrypted"))

        conn.commit()
        conn.close()
        return self.db_path

    def cleanup(self):
        import shutil
        shutil.rmtree(self.temp_dir)