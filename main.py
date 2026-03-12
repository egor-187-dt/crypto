import tkinter as tk
from src.gui.setup_wizard import SetupWizard
from src.gui.main_window import MainWindow
from src.database.db import db
from src.database.migration import run_migrations
import os


def main():
    root = tk.Tk()

    # Подключаем БД
    db.connect()

    # Запускаем миграции
    try:
        run_migrations()
    except Exception as e:
        print(f"Ошибка миграции: {e}")

    # Проверка, существует ли таблица master_password и есть ли в ней запись
    try:
        tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='master_password'")

        if tables:
            rows = db.fetch_all("SELECT COUNT(*) FROM master_password")
            if rows and rows[0][0] > 0:
                # Мастер-пароль есть - сразу главное окно
                app = MainWindow(root)
            else:
                # Таблица есть, но пароля нет - настройка
                root.withdraw()

                def on_setup():
                    root.deiconify()
                    app = MainWindow(root)

                wizard = SetupWizard(root, on_setup)
        else:
            # Таблицы master_password нет - первый запуск
            root.withdraw()

            def on_setup():
                root.deiconify()
                app = MainWindow(root)

            wizard = SetupWizard(root, on_setup)

    except Exception as e:
        print(f"Ошибка при проверке: {e}")
        root.withdraw()

        def on_setup():
            root.deiconify()
            app = MainWindow(root)

        wizard = SetupWizard(root, on_setup)

    root.mainloop()
    db.close()


if __name__ == "__main__":
    main()