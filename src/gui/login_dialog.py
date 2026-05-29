import tkinter as tk
from tkinter import ttk
import time

from src.core.events import events
from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.authentication import Authenticator
from src.core.key_manager import KeyManager
from src.database.db import db


class LoginDialog:
    def __init__(self, parent, on_success, is_relogin=False):
        self.parent = parent
        self.on_success = on_success
        self.is_relogin = is_relogin
        self.kd = KeyDerivation()
        self.auth = Authenticator(self.kd)
        self.key_manager = KeyManager()
        self.result = False

        self.dialog = tk.Toplevel(parent)

        if is_relogin:
            self.dialog.title("Разблокировка хранилища")
        else:
            self.dialog.title("Вход в CryptoSafe Manager")

        self.dialog.geometry("450x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (450 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (350 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self.failed_attempts = 0
        self.locked_until = None

        self._create_ui()

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        self.dialog.wait_window()

    def _create_ui(self):
        main_frame = ttk.Frame(self.dialog, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)

        if self.is_relogin:
            title_text = "Хранилище заблокировано"
            subtitle_text = "Введите мастер-пароль для разблокировки"
        else:
            title_text = "CryptoSafe Manager"
            subtitle_text = "Введите мастер-пароль для доступа к хранилищу"

        title_label = ttk.Label(
            main_frame,
            text=title_text,
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        subtitle_label = ttk.Label(
            main_frame,
            text=subtitle_text,
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=(0, 30))

        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(password_frame, text="Мастер-пароль:", font=("Arial", 10)).pack(anchor='w', pady=(0, 5))

        self.password_entry = ttk.Entry(password_frame, show="*", font=("Arial", 12))
        self.password_entry.pack(fill=tk.X, ipady=5)

        show_var = tk.BooleanVar(value=False)

        show_check = ttk.Checkbutton(
            password_frame,
            text="Показать пароль",
            variable=show_var,
            command=lambda: self._toggle_password(show_var.get())
        )
        show_check.pack(anchor='w', pady=(5, 0))

        self.status_label = ttk.Label(main_frame, text="", foreground="red")
        self.status_label.pack(pady=(0, 10))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.login_btn = ttk.Button(
            button_frame,
            text="Войти",
            command=self._do_login,
            width=15
        )
        self.login_btn.pack(side=tk.RIGHT, padx=(10, 0))

        cancel_btn = ttk.Button(
            button_frame,
            text="Отмена",
            command=self._on_close,
            width=10
        )
        cancel_btn.pack(side=tk.RIGHT)

        self.password_entry.bind('<Return>', lambda e: self._do_login())
        self.password_entry.focus()

    def _toggle_password(self, show):
        if show:
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    def _update_status(self, message, is_error=True):
        self.status_label.config(text=message, foreground="red" if is_error else "green")

    def _do_login(self):
        if self.locked_until and time.time() < self.locked_until:
            remaining = int(self.locked_until - time.time())
            self._update_status(f"Аккаунт заблокирован. Попробуйте через {remaining} секунд")
            return

        password = self.password_entry.get()

        if not password:
            self._update_status("Введите мастер-пароль")
            return

        self.login_btn.config(state='disabled', text="Проверка...")
        self._update_status("Проверка пароля...", is_error=False)

        self.dialog.update()

        try:
            result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")

            if not result:
                self._update_status("Ошибка: не найден мастер-пароль в системе")
                self.login_btn.config(state='normal', text="Войти")
                return

            stored_hash, salt_hex = result[0]
            salt = bytes.fromhex(salt_hex)

            success, enc_key = self.auth.login(password, stored_hash, salt)

            if success and enc_key:
                self.key_manager.store_key(enc_key)
                events.publish("user_logged_in", {"method": "master_password", "relogin": self.is_relogin})
                self.result = True
                self.dialog.destroy()
                if self.on_success:
                    self.on_success()
            else:
                self.failed_attempts = self.auth.failed_attempts

                if self.auth.locked_until:
                    self.locked_until = self.auth.locked_until.timestamp()
                    remaining = int(self.locked_until - time.time())
                    self._update_status(f"Аккаунт заблокирован на {remaining} секунд")
                else:
                    remaining_attempts = 5 - self.failed_attempts
                    self._update_status(
                        f"Неверный пароль. Осталось попыток: {remaining_attempts}"
                    )

                self.password_entry.delete(0, tk.END)
                self.login_btn.config(state='normal', text="Войти")

        except Exception as e:
            self._update_status(f"Ошибка: {str(e)}")
            self.login_btn.config(state='normal', text="Войти")

    def _on_close(self):
        self.dialog.destroy()
        if not self.is_relogin and not self.result:
            self.parent.quit()