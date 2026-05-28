import tkinter as tk
from src.gui.login_dialog import LoginDialog
from src.gui.setup_wizard import SetupWizard
from src.gui.main_window import MainWindow
from src.database.db import db
from src.database.migration import run_migrations
from src.core.config import config


class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CryptoSafe Manager")
        self.root.geometry("900x600")
        self.main_window = None

        db.connect()

        run_migrations()

        self._check_first_run()

    def _check_first_run(self):
        try:
            result = db.fetch_all("SELECT COUNT(*) FROM master_password")
            has_master_password = result and result[0][0] > 0

            if has_master_password:
                LoginDialog(self.root, self._on_login_success)
            else:
                self._show_setup_wizard()

        except Exception as e:
            print(f"Error checking database: {e}")
            self._show_setup_wizard()

    def _show_setup_wizard(self):
        self.root.withdraw()

        def on_setup_complete():
            self.root.deiconify()
            self._on_login_success()

        SetupWizard(self.root, on_setup_complete)

    def _on_login_success(self):
        if self.main_window is None:
            self.main_window = MainWindow(self.root)
        else:
            self._refresh_main_window()

    def _refresh_main_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.main_window = MainWindow(self.root)

    def run(self):
        self.root.mainloop()
        db.close()


if __name__ == "__main__":
    app = Application()
    app.run()