import tkinter as tk
from tkinter import messagebox
from src.core.key_manager import KeyManager
from src.core.state_manager import state
from src.database.db import db


class SetupWizard:
    def __init__(self, root, on_complete):
        self.root = root
        self.on_complete = on_complete
        self.key_manager = KeyManager()

        self.window = tk.Toplevel(root)
        self.window.title("Настройка")
        self.window.geometry("300x150")

        tk.Label(self.window, text="Мастер-пароль").pack(pady=10)
        self.pass_entry = tk.Entry(self.window, show="*")
        self.pass_entry.pack()

        tk.Button(self.window, text="Готово", command=self.create).pack(pady=10)

    def create(self):
        pwd = self.pass_entry.get()
        if len(pwd) < 4:
            messagebox.showerror("Ошибка", "Пароль короткий")
            return

        db.connect()

        key = self.key_manager.derive_key(pwd, b'salt123')
        self.key_manager.store_key(key)

        state.login()
        self.window.destroy()
        self.on_complete()