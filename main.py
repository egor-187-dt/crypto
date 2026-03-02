import tkinter as tk
from src.gui.setup_wizard import SetupWizard
from src.gui.main_window import MainWindow
from src.database.db import db
import os

def main():
    root = tk.Tk()

    # Сразу подключаем БД
    db.connect()

    # Если первый запуск - показываем настройку
    # Проверяем есть ли хоть одна запись в БД
    try:
        rows = db.fetch_all("SELECT COUNT(*) FROM vault_entries")
        if rows and rows[0][0] > 0:
            # Уже есть данные - сразу главное окно
            app = MainWindow(root)
        else:
            # Первый запуск - настройка
            root.withdraw()
            def on_setup():
                root.deiconify()
                app = MainWindow(root)
            wizard = SetupWizard(root, on_setup)
    except:
        # Если таблицы нет - тоже настройка
        root.withdraw()
        def on_setup():
            root.deiconify()
            app = MainWindow(root)
        wizard = SetupWizard(root, on_setup)

    root.mainloop()
    db.close()

if __name__ == "__main__":
    main()