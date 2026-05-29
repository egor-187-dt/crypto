import tkinter as tk
from src.database.db import db
from src.database.migration import run_migrations


class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CryptoSafe Manager")
        self.root.geometry("900x600")

        db.connect()
        run_migrations()

        # Показываем главное окно
        self.root.deiconify()
        self.root.update()

        # Запускаем проверку после того, как окно отобразилось
        self.root.after(100, self._check_first_run)

        self.root.mainloop()

    def _check_first_run(self):
        from src.gui.main_window import MainWindow
        self.main_window = MainWindow(self.root)


if __name__ == "__main__":
    app = Application()