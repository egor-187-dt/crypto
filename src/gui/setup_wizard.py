import tkinter as tk
from tkinter import messagebox, filedialog
from src.core.key_manager import KeyManager
from src.core.state_manager import state
from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.authentication import Authenticator
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

        # Мастер-пароль с индикатором сложности
        tk.Label(self.window, text="Мастер-пароль (мин. 12 символов):").pack()
        self.pass_entry = tk.Entry(self.window, show="*")
        self.pass_entry.pack(pady=5)
        self.pass_entry.bind("<KeyRelease>", self.check_password_strength)

        self.strength_label = tk.Label(self.window, text="Слабый", fg="red")
        self.strength_label.pack()

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

        tk.Button(self.window, text="Завершить настройку",
                  command=self.create, bg="lightblue", width=20).pack(pady=20)

    def check_password_strength(self, event=None):
        """Проверяет сложность пароля"""
        pwd = self.pass_entry.get()

        if len(pwd) < 12:
            self.strength_label.config(text="Слишком короткий (мин. 12)", fg="red")
            return False

        has_upper = any(c.isupper() for c in pwd)
        has_lower = any(c.islower() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_special = any(not c.isalnum() for c in pwd)

        if has_upper and has_lower and has_digit and has_special:
            self.strength_label.config(text="Очень сильный", fg="green")
            return True
        elif (has_upper or has_lower) and has_digit and len(pwd) >= 12:
            self.strength_label.config(text="Средний (нужны спецсимволы)", fg="orange")
            return True
        else:
            self.strength_label.config(text="Слабый (нужны буквы, цифры, символы)", fg="red")
            return False

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

        # Проверка длины
        if len(pwd) < 12:
            messagebox.showerror("Ошибка", "Пароль должен быть минимум 12 символов")
            return

        # Проверка сложности
        if not self.check_password_strength():
            if not messagebox.askyesno("Предупреждение",
                                       "Пароль недостаточно сложный. Продолжить?"):
                return

        if pwd != confirm:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return

        self.db_path = self.db_path_var.get()
        config.set("db_path", self.db_path)
        config.set("encryption_method", self.enc_var.get())

        db.db_path = self.db_path
        db.connect()

        # Создаем Argon2 хеш для аутентификации
        auth_hash = self.kd.create_auth_hash(pwd)

        # Создаем соль для ключа шифрования
        enc_salt = self.kd.create_salt()

        # Сохраняем в БД
        db.execute("DELETE FROM master_password")
        db.execute(
            "INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
            (auth_hash, enc_salt.hex())
        )

        # Сохраняем параметры в key_store - пробуем разные варианты
        try:
            # Сначала пробуем с key_data (новая структура)
            db.execute('''
                INSERT INTO key_store (key_type, key_data, salt, params)
                VALUES (?, ?, ?, ?)
            ''', ('auth_params', auth_hash, enc_salt.hex(),
                  '{"time":3,"memory":65536,"parallelism":4}'))
        except:
            try:
                # Если не получилось, пробуем старую структуру (hash вместо key_data)
                db.execute('''
                    INSERT INTO key_store (key_type, hash, salt, params)
                    VALUES (?, ?, ?, ?)
                ''', ('auth_params', auth_hash, enc_salt.hex(),
                      '{"time":3,"memory":65536,"parallelism":4}'))
            except:
                # Если и это не получилось, пробуем без params
                db.execute('''
                    INSERT INTO key_store (key_type, hash, salt)
                    VALUES (?, ?, ?)
                ''', ('auth_params', auth_hash, enc_salt.hex()))

        # Выводим ключ шифрования
        enc_key = self.kd.derive_encryption_key(pwd, enc_salt)
        self.key_manager.store_key(enc_key)

        state.login()
        self.window.destroy()
        self.on_complete()