import tkinter as tk
from tkinter import messagebox
from src.database.db import db
from src.core.events import events
import base64
import hashlib


class ChangePasswordDialog:
    def __init__(self, parent, key_manager, kd, auth):
        self.parent = parent
        self.key_manager = key_manager
        self.kd = kd
        self.auth = auth

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Смена мастер-пароля")
        self.dialog.geometry("400x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_ui()

    def _create_ui(self):
        tk.Label(self.dialog, text="Смена мастер-пароля",
                 font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(self.dialog, text="Текущий пароль:", font=("Arial", 10)).pack(pady=5)
        self.old_pass = tk.Entry(self.dialog, show="*", width=30)
        self.old_pass.pack(pady=5)

        tk.Label(self.dialog, text="Новый пароль (мин. 12 символов):", font=("Arial", 10)).pack(pady=5)
        self.new_pass = tk.Entry(self.dialog, show="*", width=30)
        self.new_pass.pack(pady=5)
        self.new_pass.bind("<KeyRelease>", self.check_strength)

        self.strength_label = tk.Label(self.dialog, text="", fg="gray")
        self.strength_label.pack()

        tk.Label(self.dialog, text="Подтверждение:", font=("Arial", 10)).pack(pady=5)
        self.confirm_pass = tk.Entry(self.dialog, show="*", width=30)
        self.confirm_pass.pack(pady=5)

        btn_frame = tk.Frame(self.dialog)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="Сменить пароль", command=self.change,
                  bg="lightblue", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.dialog.destroy,
                  width=10).pack(side=tk.LEFT, padx=5)

    def check_strength(self, event=None):
        pwd = self.new_pass.get()

        if len(pwd) < 12:
            self.strength_label.config(text="❌ Слишком короткий (нужно 12+)", fg="red")
            return False

        has_upper = any(c.isupper() for c in pwd)
        has_lower = any(c.islower() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_special = any(not c.isalnum() for c in pwd)

        if has_upper and has_lower and has_digit and has_special:
            self.strength_label.config(text="✅ Очень сильный пароль", fg="green")
            return True
        elif has_upper and has_lower and has_digit:
            self.strength_label.config(text="⚠️ Хороший, добавь спецсимволы", fg="orange")
            return True
        else:
            self.strength_label.config(text="❌ Слабый (нужны буквы, цифры, символы)", fg="red")
            return False

    def change(self):
        old = self.old_pass.get()
        new = self.new_pass.get()
        confirm = self.confirm_pass.get()

        if not old or not new or not confirm:
            messagebox.showerror("Ошибка", "Заполните все поля")
            return

        if new != confirm:
            messagebox.showerror("Ошибка", "Новые пароли не совпадают")
            return

        if len(new) < 12:
            messagebox.showerror("Ошибка", "Новый пароль должен быть минимум 12 символов")
            return

        # Получаем данные из БД
        result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
        if not result:
            messagebox.showerror("Ошибка", "Не удалось получить данные")
            return

        stored_hash, salt_value = result[0]

        # Пробуем разные форматы соли
        try:
            salt = bytes.fromhex(salt_value) if salt_value else b''
        except ValueError:
            salt = salt_value.encode() if salt_value else b''

        # Проверяем текущий пароль
        success = False

        # Сначала пробуем Argon2
        try:
            if stored_hash.startswith('$argon2'):
                success, _ = self.auth.authenticate(old, stored_hash, salt)
        except:
            pass

        # Если нет, пробуем SHA256
        if not success:
            input_hash = hashlib.sha256((old + salt_value).encode()).hexdigest()
            if input_hash == stored_hash:
                success = True

        if not success:
            messagebox.showerror("Ошибка", "Неверный текущий пароль")
            return

        # Создаем новый хеш и соль
        new_auth_hash = self.kd.create_auth_hash(new)
        new_enc_salt = self.kd.create_salt()

        # Получаем все записи для перешифровки
        entries = db.fetch_all("SELECT id, encrypted_password FROM vault_entries")

        # Получаем старый ключ
        old_key = self.key_manager.load_key()

        # Создаем новый ключ
        new_key = self.kd.derive_encryption_key(new, new_enc_salt)

        # Перешифровываем все пароли
        for entry_id, enc_text in entries:
            if enc_text:
                try:
                    # Расшифровываем старым ключом
                    enc_bytes = base64.b64decode(enc_text)
                    dec_bytes = bytes([enc_bytes[i] ^ old_key[i % len(old_key)] for i in range(len(enc_bytes))])

                    # Шифруем новым ключом
                    new_enc_bytes = bytes([dec_bytes[i] ^ new_key[i % len(new_key)] for i in range(len(dec_bytes))])
                    new_enc_text = base64.b64encode(new_enc_bytes).decode('ascii')

                    # Обновляем запись
                    db.execute("UPDATE vault_entries SET encrypted_password = ? WHERE id = ?",
                               (new_enc_text, entry_id))
                except Exception as e:
                    print(f"Ошибка при перешифровке записи {entry_id}: {e}")

        # Обновляем мастер-пароль в БД
        db.execute("UPDATE master_password SET password_hash = ?, salt = ?",
                   (new_auth_hash, new_enc_salt.hex()))

        # Сохраняем новый ключ
        self.key_manager.store_key(new_key)

        messagebox.showinfo("Успех", "Пароль успешно изменен!")
        events.publish("password_changed", {})
        self.dialog.destroy()