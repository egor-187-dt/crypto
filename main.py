import tkinter as tk
from src.gui.setup_wizard import SetupWizard
from src.gui.main_window import MainWindow
from src.database.db import db


def main():
    root = tk.Tk()
    root.withdraw()  # Скрываем главное окно пока

    def on_setup_complete():
        root.deiconify()  # Показываем главное окно
        app = MainWindow(root)

    wizard = SetupWizard(root, on_setup_complete)

    root.mainloop()
    db.close()


if __name__ == "__main__":
    main()