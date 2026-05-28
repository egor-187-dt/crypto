import tkinter as tk
from tkinter import ttk, messagebox
import os

from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.password_validator import PasswordValidator
from src.core.key_manager import KeyManager
from src.database.db import db
from src.core.config import config
from src.core.events import events


class SetupWizard:
    def __init__(self, parent, on_complete):
        self.parent = parent
        self.on_complete = on_complete
        self.kd = KeyDerivation()
        self.validator = PasswordValidator(min_length=12)

        self.wizard = tk.Toplevel(parent)
        self.wizard.title("CryptoSafe Manager - Первый запуск")
        self.wizard.geometry("500x450")
        self.wizard.transient(parent)
        self.wizard.grab_set()
        self.wizard.resizable(False, False)

        self.wizard.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (450 // 2)
        self.wizard.geometry(f"+{x}+{y}")

        self.current_step = 0
        self.steps = [self._step_welcome, self._step_master_password, self._step_complete]

        self._create_ui()
        self._show_step()

        self.wizard.protocol("WM_DELETE_WINDOW", self._on_close)

        self.wizard.wait_window()

    def _create_ui(self):
        self.main_frame = ttk.Frame(self.wizard, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.step_label = ttk.Label(self.main_frame, font=("Arial", 10, "bold"))
        self.step_label.pack(anchor='w', pady=(0, 10))

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=(20, 0))

        self.prev_btn = ttk.Button(
            self.button_frame,
            text="Назад",
            command=self._prev_step,
            state='disabled'
        )
        self.prev_btn.pack(side=tk.LEFT)

        self.next_btn = ttk.Button(
            self.button_frame,
            text="Далее",
            command=self._next_step
        )
        self.next_btn.pack(side=tk.RIGHT)

    def _clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _show_step(self):
        self._clear_content()
        self.steps[self.current_step]()

    def _next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._update_buttons()
            self._show_step()

    def _prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._update_buttons()
            self._show_step()

    def _update_buttons(self):
        self.prev_btn.config(state='normal' if self.current_step > 0 else 'disabled')

        if self.current_step == len(self.steps) - 1:
            self.next_btn.config(text="Завершить")
        else:
            self.next_btn.config(text="Далее")

    def _step_welcome(self):
        self.step_label.config(text="Шаг 1 из 3: Добро пожаловать")

        welcome_text = """
Добро пожаловать в CryptoSafe Manager!

Этот мастер поможет настроить ваше защищенное хранилище паролей.

Что будет настроено:
• Создание мастер-пароля для доступа к хранилищу
• Настройка параметров шифрования
• Создание базы данных для хранения записей

Ваш мастер-пароль будет использоваться для:
• Расшифровки всех сохраненных паролей
• Подтверждения операций с хранилищем

ВНИМАНИЕ: Мастер-пароль невозможно восстановить!
Сохраните его в надежном месте.
        """

        text_widget = tk.Text(self.content_frame, wrap=tk.WORD, height=15, font=("Arial", 10))
        text_widget.insert("1.0", welcome_text)
        text_widget.config(state='disabled')
        text_widget.pack(fill=tk.BOTH, expand=True)

    def _step_master_password(self):
        self.step_label.config(text="Шаг 2 из 3: Создание мастер-пароля")

        pwd_frame = ttk.Frame(self.content_frame)
        pwd_frame.pack(fill=tk.BOTH, expand=True)

        info_label = ttk.Label(
            pwd_frame,
            text="Создайте надежный мастер-пароль.\nМинимальная длина: 12 символов.",
            font=("Arial", 9)
        )
        info_label.pack(pady=(0, 15))

        ttk.Label(pwd_frame, text="Мастер-пароль:", font=("Arial", 10)).pack(anchor='w', pady=(0, 5))
        self.password_entry = ttk.Entry(pwd_frame, show="*", font=("Arial", 12))
        self.password_entry.pack(fill=tk.X, ipady=5, pady=(0, 10))

        ttk.Label(pwd_frame, text="Подтверждение пароля:", font=("Arial", 10)).pack(anchor='w', pady=(0, 5))
        self.confirm_entry = ttk.Entry(pwd_frame, show="*", font=("Arial", 12))
        self.confirm_entry.pack(fill=tk.X, ipady=5, pady=(0, 10))

        self.strength_label = ttk.Label(pwd_frame, text="", font=("Arial", 9))
        self.strength_label.pack(anchor='w', pady=(0, 10))

        self.error_label = ttk.Label(pwd_frame, text="", foreground="red", font=("Arial", 9))
        self.error_label.pack(anchor='w')

        self.password_entry.bind('<KeyRelease>', self._validate_password)
        self.confirm_entry.bind('<KeyRelease>', self._validate_password)

        self.password_entry.focus()

    def _validate_password(self, event=None):
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if not password:
            self.strength_label.config(text="", foreground="gray")
            self.error_label.config(text="")
            self.next_btn.config(state='disabled')
            return

        strength = self.validator.check_strength(password)

        strength_texts = {
            'weak': 'Слабый пароль',
            'medium': 'Средний пароль',
            'strong': 'Надежный пароль'
        }

        strength_colors = {
            'weak': 'red',
            'medium': 'orange',
            'strong': 'green'
        }

        self.strength_label.config(
            text=f"Сложность: {strength_texts.get(strength['strength'], '')}",
            foreground=strength_colors.get(strength['strength'], 'gray')
        )

        is_valid, errors = self.validator.validate(password)

        if not is_valid:
            error_text = "Ошибки: " + ", ".join(errors[:2])
            self.error_label.config(text=error_text)
            self.next_btn.config(state='disabled')
            return

        if confirm and password != confirm:
            self.error_label.config(text="Пароли не совпадают")
            self.next_btn.config(state='disabled')
            return

        self.error_label.config(text="")
        self.next_btn.config(state='normal')

    def _step_complete(self):
        self.step_label.config(text="Шаг 3 из 3: Завершение настройки")

        complete_frame = ttk.Frame(self.content_frame)
        complete_frame.pack(fill=tk.BOTH, expand=True)

        status_label = ttk.Label(
            complete_frame,
            text="Настройка хранилища...",
            font=("Arial", 10)
        )
        status_label.pack(pady=20)

        self.progress_bar = ttk.Progressbar(
            complete_frame,
            mode='indeterminate',
            length=400
        )
        self.progress_bar.pack(pady=20)
        self.progress_bar.start(10)

        self.wizard.update()

        self.wizard.after(100, lambda: self._finish_setup(status_label))

    def _finish_setup(self, status_label):
        try:
            password = self.password_entry.get()
            salt = self.kd.create_salt()

            auth_hash = self.kd.create_auth_hash(password)
            enc_key = self.kd.derive_encryption_key(password, salt)

            key_manager = KeyManager()
            key_manager.store_key(enc_key)

            db.execute("DELETE FROM master_password")
            db.execute(
                "INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
                (auth_hash, salt.hex())
            )

            config.set("first_run_complete", True)
            config.set("encryption_method", "AES-256")

            status_label.config(text="Настройка успешно завершена!", foreground="green")
            self.progress_bar.stop()
            self.progress_bar.destroy()

            events.publish("setup_complete", {})

            self.wizard.after(1500, self._complete_wizard)

        except Exception as e:
            status_label.config(text=f"Ошибка: {str(e)}", foreground="red")
            self.next_btn.config(state='normal', text="Повторить")
            self.next_btn.config(command=lambda: self._finish_setup(status_label))

    def _complete_wizard(self):
        self.wizard.destroy()
        if self.on_complete:
            self.on_complete()

    def _on_close(self):
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти? Настройка не будет завершена."):
            self.wizard.destroy()
            self.parent.quit()