# src/database/migration.py
# FULL FILE - Sprint 1-5 migrations

import sqlite3
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handle database migrations for all sprints."""

    def __init__(self, db_path: str):
        """
        Initialize migration manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self.conn is None:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def get_version(self) -> int:
        """Get current database schema version."""
        conn = self._get_connection()
        cursor = conn.execute("PRAGMA user_version")
        return cursor.fetchone()[0]

    def set_version(self, version: int):
        """Set database schema version."""
        conn = self._get_connection()
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()

    def migrate(self):
        """Run all pending migrations."""
        current_version = self.get_version()

        if current_version < 1:
            self._migrate_to_v1()
        if current_version < 2:
            self._migrate_to_v2()
        if current_version < 3:
            self._migrate_to_v3()
        if current_version < 4:
            self._migrate_to_v4()
        if current_version < 5:
            self._migrate_to_v5()

    def _migrate_to_v1(self):
        """Sprint 1: Initial database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # vault_entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                username TEXT,
                encrypted_password BLOB NOT NULL,
                url TEXT,
                notes TEXT,
                tags TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)

        # audit_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                entry_id TEXT,
                details TEXT,
                signature TEXT
            )
        """)

        # settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                encrypted BOOLEAN DEFAULT 0
            )
        """)

        # key_store table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_type TEXT NOT NULL,
                key_data BLOB,
                salt BLOB,
                hash TEXT,
                params TEXT,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_updated ON vault_entries(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(setting_key)")

        conn.commit()
        self.set_version(1)
        logger.info("Migration to version 1 completed")

    def _migrate_to_v2(self):
        """Sprint 2: Add key management columns."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Add session tracking columns to settings
        cursor.execute("""
            INSERT OR IGNORE INTO settings (setting_key, setting_value, encrypted)
            VALUES 
                ('auto_lock_timeout', '3600', 0),
                ('failed_attempts', '0', 0),
                ('last_activity', '', 0),
                ('session_start', '', 0)
        """)

        # Add password policy settings
        cursor.execute("""
            INSERT OR IGNORE INTO settings (setting_key, setting_value, encrypted)
            VALUES 
                ('min_password_length', '12', 0),
                ('require_uppercase', '1', 0),
                ('require_lowercase', '1', 0),
                ('require_digits', '1', 0),
                ('require_symbols', '1', 0)
        """)

        conn.commit()
        self.set_version(2)
        logger.info("Migration to version 2 completed")

    def _migrate_to_v3(self):
        """Sprint 3: Add encrypted_data BLOB and soft delete."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if encrypted_data column exists, if not add it
        cursor.execute("PRAGMA table_info(vault_entries)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'encrypted_data' not in columns:
            cursor.execute("ALTER TABLE vault_entries ADD COLUMN encrypted_data BLOB")

        if 'deleted' not in columns:
            cursor.execute("ALTER TABLE vault_entries ADD COLUMN deleted INTEGER DEFAULT 0")

        if 'deleted_at' not in columns:
            cursor.execute("ALTER TABLE vault_entries ADD COLUMN deleted_at TIMESTAMP")

        # Migrate existing encrypted_password to encrypted_data if needed
        cursor.execute("""
            UPDATE vault_entries 
            SET encrypted_data = encrypted_password 
            WHERE encrypted_data IS NULL AND encrypted_password IS NOT NULL
        """)

        # Add indexes for soft delete
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_deleted ON vault_entries(deleted)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_tags ON vault_entries(tags)")

        conn.commit()
        self.set_version(3)
        logger.info("Migration to version 3 completed")

    def _migrate_to_v4(self):
        """Sprint 4: Add clipboard settings."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Add clipboard settings
        cursor.execute("""
            INSERT OR IGNORE INTO settings (setting_key, setting_value, encrypted)
            VALUES 
                ('clipboard_timeout', '30', 0),
                ('clipboard_notifications', '1', 0),
                ('clipboard_security_level', 'advanced', 0),
                ('clipboard_monitoring', '1', 0),
                ('clipboard_accelerated_clear', '1', 0)
        """)

        conn.commit()
        self.set_version(4)
        logger.info("Migration to version 4 completed")

    def _migrate_to_v5(self):
        """Sprint 5: Add audit log integrity columns for cryptographic protection."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check existing columns in audit_log
        cursor.execute("PRAGMA table_info(audit_log)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        # Add sequence_number column
        if 'sequence_number' not in existing_columns:
            cursor.execute("ALTER TABLE audit_log ADD COLUMN sequence_number INTEGER")

        # Add previous_hash column for hash chain
        if 'previous_hash' not in existing_columns:
            cursor.execute("ALTER TABLE audit_log ADD COLUMN previous_hash TEXT")

        # Add signature column for digital signatures
        if 'signature' not in existing_columns:
            cursor.execute("ALTER TABLE audit_log ADD COLUMN signature TEXT")

        # Add entry_hash column if not exists
        if 'entry_hash' not in existing_columns:
            cursor.execute("ALTER TABLE audit_log ADD COLUMN entry_hash TEXT")

        # Add entry_data column (JSON structured data) if not exists
        if 'entry_data' not in existing_columns:
            cursor.execute("ALTER TABLE audit_log ADD COLUMN entry_data TEXT")

        # Update existing rows with sequence numbers using rowid
        cursor.execute("UPDATE audit_log SET sequence_number = rowid WHERE sequence_number IS NULL")

        # Get min sequence number
        cursor.execute("SELECT MIN(sequence_number) FROM audit_log")
        min_seq = cursor.fetchone()[0]

        # Update genesis entry with 64 zeros as previous_hash
        if min_seq is not None:
            zeros_64 = '0' * 64
            cursor.execute(
                "UPDATE audit_log SET previous_hash = ? WHERE previous_hash IS NULL AND sequence_number = ?",
                (zeros_64, min_seq)
            )

        # Update remaining rows with empty string as placeholder
        cursor.execute("UPDATE audit_log SET previous_hash = '' WHERE previous_hash IS NULL")

        # Update entry_hash for existing rows
        cursor.execute("""
            UPDATE audit_log 
            SET entry_hash = hex(randomblob(32))
            WHERE entry_hash IS NULL
        """)

        # Update signature for existing rows
        cursor.execute("""
            UPDATE audit_log 
            SET signature = hex(randomblob(64))
            WHERE signature IS NULL
        """)

        # Migrate existing action/details to entry_data JSON format
        try:
            cursor.execute("""
                UPDATE audit_log 
                SET entry_data = json_object(
                    'event_type', action,
                    'details', json(details),
                    'timestamp', timestamp,
                    'entry_id', entry_id
                )
                WHERE entry_data IS NULL AND action IS NOT NULL
            """)
        except:
            # If json functions not available, just set simple text
            cursor.execute("""
                UPDATE audit_log 
                SET entry_data = details 
                WHERE entry_data IS NULL AND details IS NOT NULL
            """)

        # Create indexes for performance per DB-3
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_sequence ON audit_log(sequence_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp_v5 ON audit_log(timestamp)")

        # Create index for event_type if json functions available
        try:
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(json_extract(entry_data, '$.event_type'))")
        except:
            pass

        # Make sequence_number UNIQUE
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_sequence ON audit_log(sequence_number)")

        conn.commit()
        self.set_version(5)
        logger.info("Migration to version 5 completed - Audit log integrity columns added")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


def run_migrations(db_path: str = 'data/vault.db'):
    """
    Run all pending migrations.

    Args:
        db_path: Path to database file (default: 'data/vault.db')
    """
    migration = DatabaseMigration(db_path)
    try:
        migration.migrate()
    finally:
        migration.close()