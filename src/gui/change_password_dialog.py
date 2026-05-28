"""
Change Password Dialog for CryptoSafe Manager
Allows users to securely change their master password with re-encryption
"""
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
from datetime import datetime

from src.core.events import events
from src.core.crypto.password_validator import PasswordValidator
from src.core.crypto.key_derivation import KeyDerivation
from src.core.key_manager import KeyManager


class ChangePasswordDialog:
    """Диалог смены мастер-пароля с перешифровкой всех записей"""

    def __init__(self, parent, db, entry_manager, key_manager, authenticator):
        self.parent = parent
        self.db = db
        self.entry_manager = entry_manager
        self.key_manager = key_manager
        self.auth = authenticator
        self.validator = PasswordValidator(min_length=12)

        self.result = None
        self.is_reencrypting = False

        # Создаем диалог
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Смена мастер-пароля")
        self.dialog.geometry("550x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        # Центрируем окно
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (550 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self._create_ui()

        # Ждем закрытия
        self.dialog.wait_window()

    def _create_ui(self):
        """Создает интерфейс диалога"""
        # Основной фрейм с отступами
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = ttk.Label(
            main_frame,
            text="Смена мастер-пароля",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Описание
        desc_label = ttk.Label(
            main_frame,
            text="Внимание: при смене пароля все записи будут перешифрованы.\n"
                 "Это может занять некоторое время в зависимости от количества записей.",
            wraplength=500,
            justify="center"
        )
        desc_label.pack(pady=(0, 20))

        # Разделитель
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Текущий пароль
        current_frame = ttk.LabelFrame(main_frame, text="Текущий пароль", padding="10")
        current_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(current_frame, text="Текущий пароль:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.current_password = ttk.Entry(current_frame, show="*", width=30)
        self.current_password.grid(row=0, column=1, sticky='ew')

        # Кнопка показать/скрыть
        self.show_current = False
        self.show_current_btn = ttk.Button(
            current_frame,
            text="👁",
            width=3,
            command=self._toggle_current_password
        )
        self.show_current_btn.grid(row=0, column=2, padx=(5, 0))

        current_frame.columnconfigure(1, weight=1)

        # Новый пароль
        new_frame = ttk.LabelFrame(main_frame, text="Новый пароль", padding="10")
        new_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(new_frame, text="Новый пароль:").grid(row=0, column=0, sticky='w', padx=(0, 10), pady=5)
        self.new_password = ttk.Entry(new_frame, show="*", width=30)
        self.new_password.grid(row=0, column=1, sticky='ew', pady=5)

        # Кнопка показать/скрыть для нового пароля
        self.show_new = False
        self.show_new_btn = ttk.Button(
            new_frame,
            text="👁",
            width=3,
            command=self._toggle_new_password
        )
        self.show_new_btn.grid(row=0, column=2, padx=(5, 0), pady=5)

        # Индикатор сложности пароля
        self.strength_label = ttk.Label(new_frame, text="", foreground="gray")
        self.strength_label.grid(row=1, column=1, sticky='w', pady=5)

        # Подтверждение пароля
        ttk.Label(new_frame, text="Подтверждение:").grid(row=2, column=0, sticky='w', padx=(0, 10), pady=5)
        self.confirm_password = ttk.Entry(new_frame, show="*", width=30)
        self.confirm_password.grid(row=2, column=1, sticky='ew', pady=5)

        new_frame.columnconfigure(1, weight=1)

        # Привязываем события проверки сложности
        self.new_password.bind('<KeyRelease>', self._update_strength)
        self.confirm_password.bind('<KeyRelease>', self._update_strength)

        # Настройки (опционально)
        options_frame = ttk.LabelFrame(main_frame, text="Опции", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 15))

        self.lock_after_change = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Заблокировать хранилище после смены пароля (потребуется повторный вход)",
            variable=self.lock_after_change
        ).pack(anchor='w')

        # Прогресс-бар для перешифровки
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 15))

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack()

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            length=400
        )

        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.change_btn = ttk.Button(
            button_frame,
            text="Сменить пароль",
            command=self._change_password,
            width=15
        )
        self.change_btn.pack(side=tk.RIGHT, padx=(10, 0))

        cancel_btn = ttk.Button(
            button_frame,
            text="Отмена",
            command=self._cancel,
            width=10
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Фокус на поле текущего пароля
        self.current_password.focus()

    def _toggle_current_password(self):
        """Показывает/скрывает текущий пароль"""
        self.show_current = not self.show_current
        if self.show_current:
            self.current_password.config(show="")
            self.show_current_btn.config(text="🙈")
        else:
            self.current_password.config(show="*")
            self.show_current_btn.config(text="👁")

    def _toggle_new_password(self):
        """Показывает/скрывает новый пароль"""
        self.show_new = not self.show_new
        if self.show_new:
            self.new_password.config(show="")
            self.confirm_password.config(show="")
            self.show_new_btn.config(text="🙈")
        else:
            self.new_password.config(show="*")
            self.confirm_password.config(show="*")
            self.show_new_btn.config(text="👁")

    def _update_strength(self, event=None):
        """Обновляет индикатор сложности пароля"""
        password = self.new_password.get()
        if not password:
            self.strength_label.config(text="", foreground="gray")
            return

        strength = self.validator.check_strength(password)

        texts = {
            'weak': 'Слабый пароль - добавьте цифры, спецсимволы или увеличьте длину',
            'medium': 'Средний пароль - можно усилить',
            'strong': 'Надежный пароль!'
        }

        colors = {
            'weak': 'red',
            'medium': 'orange',
            'strong': 'green'
        }

        self.strength_label.config(
            text=f"Сложность: {texts.get(strength['strength'], '')}",
            foreground=colors.get(strength['strength'], 'gray')
        )

    def _validate_inputs(self) -> tuple:
        """
        Проверяет введенные данные

        Returns:
            tuple: (is_valid, error_message)
        """
        current = self.current_password.get()
        new_pwd = self.new_password.get()
        confirm = self.confirm_password.get()

        if not current:
            return False, "Введите текущий пароль"

        if not new_pwd:
            return False, "Введите новый пароль"

        if new_pwd != confirm:
            return False, "Пароли не совпадают"

        if new_pwd == current:
            return False, "Новый пароль должен отличаться от текущего"

        # Проверяем сложность пароля
        is_valid, errors = self.validator.validate(new_pwd)
        if not is_valid:
            error_msg = "Пароль недостаточно надежен:\n" + "\n".join(f"• {e}" for e in errors[:3])
            return False, error_msg

        return True, ""

    def _change_password(self):
        """Выполняет смену пароля"""
        # Проверяем ввод
        is_valid, error = self._validate_inputs()
        if not is_valid:
            messagebox.showerror("Ошибка", error, parent=self.dialog)
            return

        # Получаем текущие данные из БД
        try:
            result = self.db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
            if not result:
                messagebox.showerror("Ошибка", "Не найдены данные мастер-пароля", parent=self.dialog)
                return

            stored_hash, salt_hex = result[0]
            salt = bytes.fromhex(salt_hex)

            # Проверяем текущий пароль
            current_pwd = self.current_password.get()
            success, enc_key = self.auth.login(current_pwd, stored_hash, salt)

            if not success:
                messagebox.showerror("Ошибка", "Неверный текущий пароль", parent=self.dialog)
                return

            # Сохраняем ключ для перешифровки
            self.key_manager.store_key(enc_key)

            # Спрашиваем подтверждение
            entries = self.entry_manager.get_all_entries()
            if not messagebox.askyesno(
                    "Подтверждение",
                    f"Будет перешифровано {len(entries)} записей.\n"
                    "Это может занять некоторое время.\n\n"
                    "Продолжить?",
                    parent=self.dialog
            ):
                return

            # Запускаем процесс смены пароля
            self._do_change_password(current_pwd, entries)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при смене пароля: {str(e)}", parent=self.dialog)

    def _do_change_password(self, old_password: str, entries: list):
        """
        Выполняет фактическую смену пароля с перешифровкой

        Args:
            old_password: Старый пароль
            entries: Список записей для перешифровки
        """
        # Блокируем интерфейс
        self.change_btn.config(state='disabled', text="Перешифровка...")
        self.progress_bar.pack(pady=10)
        self.progress_bar.start(10)

        def reencrypt_worker():
            try:
                # 1. Создаем новый хэш и соль
                kd = KeyDerivation()
                new_password = self.new_password.get()
                new_salt = kd.create_salt()
                new_auth_hash = kd.create_auth_hash(new_password)
                new_enc_key = kd.derive_encryption_key(new_password, new_salt)

                # 2. Перешифровываем все записи
                total = len(entries)
                for i, entry in enumerate(entries):
                    # Обновляем прогресс в UI потоке
                    self.dialog.after(0, self._update_progress, i + 1, total, entry.get('title', 'Unknown'))

                    # Перешифровываем запись
                    self.entry_manager.update_entry(entry['id'], entry)

                # 3. Сохраняем новые данные в БД
                self.db.execute("DELETE FROM master_password")
                self.db.execute(
                    "INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
                    (new_auth_hash, new_salt.hex())
                )

                # 4. Обновляем ключ в менеджере
                self.key_manager.store_key(new_enc_key)

                # 5. Успех!
                self.dialog.after(0, self._on_reencrypt_success)

            except Exception as e:
                self.dialog.after(0, self._on_reencrypt_error, str(e))

        # Запускаем в отдельном потоке
        thread = Thread(target=reencrypt_worker, daemon=True)
        thread.start()

    def _update_progress(self, current: int, total: int, title: str):
        """Обновляет прогресс перешифровки"""
        self.progress_label.config(text=f"Перешифровка: {current}/{total} - {title[:30]}...")
        if total > 0:
            percent = (current / total) * 100
            self.progress_bar.config(mode='determinate', value=percent)

    def _on_reencrypt_success(self):
        """Обработчик успешной перешифровки"""
        self.progress_bar.stop()
        self.progress_label.config(text="Перешифровка завершена!")

        # Показываем сообщение
        messagebox.showinfo(
            "Успех",
            "Пароль успешно изменен!\n\n"
            "Все записи перешифрованы с новым ключом.",
            parent=self.dialog
        )

        # Если нужно заблокировать хранилище
        if self.lock_after_change.get():
            self.auth.logout()
            self.key_manager.clear_key()
            events.publish("vault_locked", {"reason": "password_changed"})

        self.result = True
        self.dialog.destroy()

    def _on_reencrypt_error(self, error: str):
        """Обработчик ошибки перешифровки"""
        self.progress_bar.stop()
        messagebox.showerror(
            "Ошибка",
            f"Ошибка при перешифровке: {error}\n\n"
            "Пароль НЕ был изменен. Ваши данные в безопасности.",
            parent=self.dialog
        )
        self.change_btn.config(state='normal', text="Сменить пароль")
        self.progress_bar.pack_forget()

    def _cancel(self):
        """Отмена операции"""
        if self.is_reencrypting:
            if not messagebox.askyesno(
                    "Подтверждение",
                    "Перешифровка еще не завершена.\n"
                    "Прервать операцию? (Данные не будут изменены)",
                    parent=self.dialog
            ):
                return

        self.result = False
        self.dialog.destroy()