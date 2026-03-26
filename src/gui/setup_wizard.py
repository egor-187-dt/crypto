import tkinter as tk
from tkinter import messagebox, filedialog
from src.core.key_manager import KeyManager
from src.core.state_manager import state
from src.core.crypto.key_derivation import KeyDerivation
from src.database.db import db
from src.core.config import config
import os


class SetupWizard:
    def __init__(self, root, on_complete):
        self.root = root
        self.on_complete = on_complete
        self.key_manager = KeyManager()
        self.kd = KeyDerivation()

        self.db_path = config.get("db_path", "vault.db")

        self.window = tk.Toplevel(root)
        self.window.title("Мастер настройки")
        self.window.geometry("500x450")
        self.window.resizable(False, False)

        tk.Label(self.window, text="Первоначальная настройка",
                 font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(self.window, text="Мастер-пароль (мин. 8 символов):").pack()
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

        tk.Button(self.window, text="Завершить настройку",
                  command=self.create, bg="lightblue", width=20).pack(pady=20)

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

        if len(pwd) < 8:
            messagebox.showerror("Ошибка", "Пароль должен быть минимум 8 символов")
            return

        if pwd != confirm:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return

        self.db_path = self.db_path_var.get()
        config.set("db_path", self.db_path)

        db.db_path = self.db_path
        db.connect()

        # Создаем Argon2 хеш для аутентификации
        auth_hash = self.kd.create_auth_hash(pwd)

        # Создаем соль для ключа шифрования
        enc_salt = self.kd.create_salt()

        # Сохраняем в master_password
        db.execute("DELETE FROM master_password")
        db.execute(
            "INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
            (auth_hash, enc_salt.hex())
        )

        # Создаем ключ шифрования и сохраняем
        enc_key = self.kd.derive_encryption_key(pwd, enc_salt)
        self.key_manager.store_key(enc_key)

        state.login()
        messagebox.showinfo("Успех", "Мастер-пароль создан!")
        self.window.destroy()
        self.on_complete()