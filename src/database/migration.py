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


# Функция для автоматического запуска миграций
def run_migrations():
    version = Migration.get_version()
    print(f"Текущая версия БД: {version}")
    if version < 2:
        Migration.migrate_to_v2()