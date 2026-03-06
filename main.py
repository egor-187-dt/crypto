import tkinter as tk
from src.gui.setup_wizard import SetupWizard
from src.gui.main_window import MainWindow
from src.database.db import db
import os


def main():
    root = tk.Tk()

    # Сразу подключаем БД
    db.connect()

    # Проверяем, существует ли таблица master_password и есть ли в ней запись
    try:
        # Проверяем структуру таблицы
        tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='master_password'")

        if tables:
            # Таблица есть, проверяем есть ли пароль
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
        # Если ошибка - тоже настройка
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