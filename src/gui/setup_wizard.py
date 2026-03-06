import tkinter as tk
from tkinter import messagebox, filedialog
from src.core.key_manager import KeyManager
from src.core.state_manager import state
from src.database.db import db
from src.core.config import config
import os
import hashlib


class SetupWizard:
    def __init__(self, root, on_complete):
        self.root = root
        self.on_complete = on_complete
        self.key_manager = KeyManager()

        self.db_path = config.get("db_path", "vault.db")

        self.window = tk.Toplevel(root)
        self.window.title("Мастер настройки")
        self.window.geometry("450x400")
        self.window.resizable(False, False)

        tk.Label(self.window, text="Первоначальная настройка",
                 font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(self.window, text="Мастер-пароль:").pack()
        self.pass_entry = tk.Entry(self.window, show="*")
        self.pass_entry.pack(pady=5)

        tk.Label(self.window, text="Подтверждение пароля:").pack()
        self.confirm_entry = tk.Entry(self.window, show="*")
        self.confirm_entry.pack(pady=5)

        tk.Label(self.window, text="Расположение базы данных:").pack(pady=5)

        db_frame = tk.Frame(self.window)
        db_frame.pack(pady=5)

        self.db_path_var = tk.StringVar(value=self.db_path)
        db_entry = tk.Entry(db_frame, textvariable=self.db_path_var, width=30)
        db_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(db_frame, text="Обзор", command=self.browse_db).pack(side=tk.LEFT)

        tk.Label(self.window, text="Настройки шифрования:", font=("Arial", 10, "bold")).pack(pady=10)

        enc_frame = tk.Frame(self.window)
        enc_frame.pack()

        self.enc_var = tk.StringVar(value="AES-256")
        tk.Radiobutton(enc_frame, text="AES-256 (рекомендуется)",
                       variable=self.enc_var, value="AES-256").pack(anchor=tk.W)
        tk.Radiobutton(enc_frame, text="XOR (только для тестов)",
                       variable=self.enc_var, value="XOR").pack(anchor=tk.W)

        tk.Button(self.window, text="Завершить настройку",
                  command=self.create, bg="lightblue").pack(pady=20)

    def browse_db(self):
        filename = filedialog.asksaveasfilename(
            title="Выберите место для базы данных",
            defaultextension=".db",
            filetypes=[("SQLite DB", "*.db"), ("Все файлы", "*.*")]
        )
        if filename:
            self.db_path_var.set(filename)
            self.db_path = filename

    def create(self):
        pwd = self.pass_entry.get()
        confirm = self.confirm_entry.get()

        if len(pwd) < 4:
            messagebox.showerror("Ошибка", "Пароль должен быть минимум 4 символа")
            return

        if pwd != confirm:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return

        self.db_path = self.db_path_var.get()
        config.set("db_path", self.db_path)
        config.set("encryption_method", self.enc_var.get())

        db.db_path = self.db_path
        db.connect()

        salt = "fixed_salt"
        password_hash = hashlib.sha256((pwd + salt).encode()).hexdigest()

        db.execute("DELETE FROM master_password")
        db.execute(
            "INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
            (password_hash, salt)
        )

        key = self.key_manager.derive_key(pwd, b'salt123')
        self.key_manager.store_key(key)

        state.login()
        self.window.destroy()
        self.on_complete()