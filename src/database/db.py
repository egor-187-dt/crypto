import sqlite3
import os
from src.core.config import config


class Database:
    def __init__(self):
        self.db_path = config.get("db_path", "data/vault.db")
        self.conn = None

    def connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._upgrade_audit_table()  # Добавляем обновление таблицы аудита

    def _upgrade_audit_table(self):
        """Add missing columns to audit_log table for Sprint 5."""
        try:
            # Проверяем существующие колонки
            cursor = self.conn.execute("PRAGMA table_info(audit_log)")
            existing_columns = [col[1] for col in cursor.fetchall()]

            # Добавляем недостающие колонки
            if 'sequence_number' not in existing_columns:
                self.conn.execute("ALTER TABLE audit_log ADD COLUMN sequence_number INTEGER")

            if 'previous_hash' not in existing_columns:
                self.conn.execute("ALTER TABLE audit_log ADD COLUMN previous_hash TEXT")

            if 'entry_hash' not in existing_columns:
                self.conn.execute("ALTER TABLE audit_log ADD COLUMN entry_hash TEXT")

            if 'entry_data' not in existing_columns:
                self.conn.execute("ALTER TABLE audit_log ADD COLUMN entry_data TEXT")

            # Обновляем существующие записи
            self.conn.execute("UPDATE audit_log SET sequence_number = rowid WHERE sequence_number IS NULL")

            self.conn.commit()
        except Exception as e:
            print(f"Error upgrading audit table: {e}")

    def _create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS vault_entries (
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

        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_vault_entries_title ON vault_entries(title)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_vault_entries_updated ON vault_entries(updated_at)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_vault_entries_deleted ON vault_entries(deleted)')

        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS master_password (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS key_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_type TEXT NOT NULL,
                salt TEXT,
                hash TEXT,
                key_data TEXT,
                params TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE,
                setting_value TEXT,
                encrypted INTEGER DEFAULT 0
            )
        ''')

        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                entry_id INTEGER,
                details TEXT,
                signature TEXT,
                sequence_number INTEGER,
                previous_hash TEXT,
                entry_hash TEXT,
                entry_data TEXT
            )
        ''')

        self.conn.commit()

    def execute(self, sql, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        self.conn.commit()
        return cursor

    def fetch_all(self, sql, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()

    def fetch_one(self, sql, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchone()

    def close(self):
        if self.conn:
            self.conn.close()


db = Database()