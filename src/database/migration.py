from src.database.db import db


class Migration:

    @staticmethod
    def get_version():
        try:
            result = db.fetch_one("PRAGMA user_version")
            return result[0] if result else 0
        except:
            return 0

    @staticmethod
    def set_version(version):
        db.execute(f"PRAGMA user_version = {version}")

    @staticmethod
    def migrate_to_v2():
        print("Running migration to version 2...")

        tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='key_store'")
        if not tables:
            db.execute('''
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

        Migration.set_version(2)
        print("Migration to version 2 completed")

    @staticmethod
    def migrate_to_v3():
        print("Running migration to version 3...")

        columns = db.fetch_all("PRAGMA table_info(vault_entries)")
        col_names = [col[1] for col in columns]

        if 'deleted' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN deleted INTEGER DEFAULT 0")

        if 'deleted_at' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN deleted_at TIMESTAMP")

        if 'encrypted_data' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN encrypted_data BLOB")

        db.execute("CREATE INDEX IF NOT EXISTS idx_entries_title ON vault_entries(title)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_entries_updated ON vault_entries(updated_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_entries_deleted ON vault_entries(deleted)")

        Migration.set_version(3)
        print("Migration to version 3 completed")

    @staticmethod
    def migrate_to_v4():
        print("Running migration to version 4 for Sprint 2...")

        columns = db.fetch_all("PRAGMA table_info(vault_entries)")
        col_names = [col[1] for col in columns]

        if 'version' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN version INTEGER DEFAULT 2")

        tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not tables:
            db.execute('''
                CREATE TABLE settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE,
                    setting_value TEXT,
                    encrypted INTEGER DEFAULT 0
                )
            ''')

        Migration.set_version(4)
        print("Migration to version 4 completed")

    @staticmethod
    def migrate_to_v5():
        print("Running migration to version 5 for Sprint 3...")

        columns = db.fetch_all("PRAGMA table_info(vault_entries)")
        col_names = [col[1] for col in columns]

        if 'encrypted_data' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN encrypted_data BLOB")

        if 'deleted' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN deleted INTEGER DEFAULT 0")

        if 'deleted_at' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN deleted_at TIMESTAMP")

        if 'url' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN url TEXT")

        if 'notes' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN notes TEXT")

        if 'tags' not in col_names:
            db.execute("ALTER TABLE vault_entries ADD COLUMN tags TEXT")

        db.execute("CREATE INDEX IF NOT EXISTS idx_entries_deleted ON vault_entries(deleted)")

        Migration.set_version(5)
        print("Migration to version 5 completed")


def run_migrations():
    version = Migration.get_version()
    print(f"Current database version: {version}")

    if version < 2:
        Migration.migrate_to_v2()
        version = Migration.get_version()

    if version < 3:
        Migration.migrate_to_v3()
        version = Migration.get_version()

    if version < 4:
        Migration.migrate_to_v4()
        version = Migration.get_version()

    if version < 5:
        Migration.migrate_to_v5()