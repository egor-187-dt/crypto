import sqlite3
from src.database.db import db


class Migration:
    """Управление миграциями схемы БД"""

    @staticmethod
    def get_version():
        """Получает текущую версию БД"""
        try:
            result = db.fetch_all("PRAGMA user_version")
            return result[0][0] if result else 0
        except:
            return 0

    @staticmethod
    def set_version(version):
        """Устанавливает версию БД"""
        db.execute(f"PRAGMA user_version = {version}")

    @staticmethod
    def migrate_to_v2():
        """Миграция с версии 1 на 2"""
        print("Запуск миграции на версию 2...")

        # Проверяем существование таблицы key_store
        tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='key_store'")

        if not tables:
            # Создаем новую таблицу с правильной структурой
            print("Создаем таблицу key_store")
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
        else:
            # Проверяем и добавляем недостающие колонки
            columns = db.fetch_all("PRAGMA table_info(key_store)")
            column_names = [col[1] for col in columns]

            if 'key_data' not in column_names:
                print("Добавляем колонку key_data в таблицу key_store")
                db.execute("ALTER TABLE key_store ADD COLUMN key_data TEXT")

            if 'params' not in column_names:
                print("Добавляем колонку params в таблицу key_store")
                db.execute("ALTER TABLE key_store ADD COLUMN params TEXT")

        # Обновляем версию
        Migration.set_version(2)
        print("Миграция на версию 2 завершена")

    @staticmethod
    def migrate_to_v3():
        """Миграция для спринта 3"""
        print("Запуск миграции на версию 3...")

        # Проверяем существующие колонки в vault_entries
        columns = db.fetch_all("PRAGMA table_info(vault_entries)")
        col_names = [col[1] for col in columns]

        # Добавляем колонку deleted если нет
        if 'deleted' not in col_names:
            print("Добавляем колонку deleted")
            db.execute("ALTER TABLE vault_entries ADD COLUMN deleted INTEGER DEFAULT 0")

        # Добавляем колонку deleted_at если нет
        if 'deleted_at' not in col_names:
            print("Добавляем колонку deleted_at")
            db.execute("ALTER TABLE vault_entries ADD COLUMN deleted_at TIMESTAMP")

        # Добавляем колонку encrypted_data если нет
        if 'encrypted_data' not in col_names:
            print("Добавляем колонку encrypted_data")
            db.execute("ALTER TABLE vault_entries ADD COLUMN encrypted_data BLOB")

        # Добавляем колонку id если еще TEXT (раньше был INTEGER)
        if 'id' in col_names:
            # Проверяем тип колонки id
            for col in columns:
                if col[1] == 'id' and col[2] != 'TEXT':
                    print("Конвертируем id в TEXT")
                    # Создаем временную таблицу
                    db.execute('''
                        CREATE TABLE vault_entries_temp (
                            id TEXT PRIMARY KEY,
                            title TEXT,
                            username TEXT,
                            encrypted_password TEXT,
                            url TEXT,
                            notes TEXT,
                            created_at TIMESTAMP,
                            updated_at TIMESTAMP,
                            tags TEXT,
                            deleted INTEGER DEFAULT 0,
                            deleted_at TIMESTAMP,
                            encrypted_data BLOB
                        )
                    ''')

                    # Копируем данные
                    db.execute('''
                        INSERT INTO vault_entries_temp (id, title, username, encrypted_password, url, notes, created_at, updated_at, tags)
                        SELECT CAST(id AS TEXT), title, username, encrypted_password, url, notes, created_at, updated_at, tags
                        FROM vault_entries
                    ''')

                    # Удаляем старую таблицу
                    db.execute("DROP TABLE vault_entries")

                    # Переименовываем временную
                    db.execute("ALTER TABLE vault_entries_temp RENAME TO vault_entries")

        # Создаем индексы
        print("Создаем индексы...")
        db.execute("CREATE INDEX IF NOT EXISTS idx_entries_title ON vault_entries(title)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_entries_updated ON vault_entries(updated_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_entries_deleted ON vault_entries(deleted)")

        # Обновляем версию
        Migration.set_version(3)
        print("Миграция на версию 3 завершена")


# Функция для автоматического запуска миграций
def run_migrations():
    version = Migration.get_version()
    print(f"Текущая версия БД: {version}")

    if version < 2:
        Migration.migrate_to_v2()
        version = Migration.get_version()

    if version < 3:
        Migration.migrate_to_v3()