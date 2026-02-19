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
        self.window.title("Первоначальная настройка")
        self.window.geometry("300x200")

        tk.Label(self.window, text="Придумайте мастер-пароль").pack(pady=10)
        self.pass_entry = tk.Entry(self.window, show="*")
        self.pass_entry.pack(pady=5)

        tk.Button(self.window, text="Создать хранилище", command=self.create).pack(pady=20)

    def create(self):
        password = self.pass_entry.get()
        if len(password) < 4:
            messagebox.showerror("Ошибка", "Пароль слишком короткий")
            return

        db.connect()

        salt = b'static_salt_for_sprint1'
        key = self.key_manager.derive_key(password, salt)
        self.key_manager.store_key(key)
        state.login()

        self.window.destroy()
        self.on_complete()