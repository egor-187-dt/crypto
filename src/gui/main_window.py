import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from src.core.config import config
from src.core.events import events
from src.core.state_manager import state
from src.core.key_manager import KeyManager
from src.core.crypto.authentication import Authenticator
from src.core.crypto.key_derivation import KeyDerivation
from src.core.vault.entry_manager import EntryManager
from src.core.vault.password_generator import PasswordGenerator
from src.core.clipboard import get_clipboard_service
from src.gui.entry_dialog import EntryDialog
from src.gui.change_password_dialog import ChangePasswordDialog
from src.gui.login_dialog import LoginDialog
from src.gui.settings_dialog import SettingsDialog
from src.gui.widgets.clipboard_statusbar import ClipboardStatusBar
from src.database.db import db


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("CryptoSafe Manager")
        self.root.geometry("950x650")

        self.kd = KeyDerivation()
        self.key_manager = KeyManager()
        self.auth = Authenticator(self.kd)
        self.entry_manager = EntryManager(db, self.key_manager)
        self.password_gen = PasswordGenerator()

        self.clipboard_service = get_clipboard_service(config)

        self.last_activity = datetime.now()
        self.auto_lock_id = None
        self.auto_lock_minutes = config.get("auto_lock_timeout", 60)
        self.is_locked_display = False

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
            print(f"Error: {e}")
            self._show_setup_wizard()

    def _show_setup_wizard(self):
        from src.gui.setup_wizard import SetupWizard
        SetupWizard(self.root, self._on_login_success)

    def _on_login_success(self):
        self._setup_ui()
        self._bind_events()
        self._start_auto_lock_timer()
        self._refresh_entries()

        state.login()
        state.update_activity()

        self.clipboard_service.is_vault_unlocked = True

        events.publish("main_window_ready", {})

    def _setup_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Сменить мастер-пароль", command=self._change_master_password)
        file_menu.add_separator()
        file_menu.add_command(label="Выйти", command=self._quit)

        security_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Безопасность", menu=security_menu)
        security_menu.add_command(label="Заблокировать", command=self._lock_vault)
        security_menu.add_command(label="Выйти из системы", command=self._logout)
        security_menu.add_separator()
        security_menu.add_command(label="Настройки", command=self._show_settings)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="О программе", command=self._about)

        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.add_btn = ttk.Button(toolbar, text="Добавить", command=self._add_entry)
        self.add_btn.pack(side=tk.LEFT, padx=2)

        self.edit_btn = ttk.Button(toolbar, text="Редактировать", command=self._edit_entry)
        self.edit_btn.pack(side=tk.LEFT, padx=2)

        self.delete_btn = ttk.Button(toolbar, text="Удалить", command=self._delete_entry)
        self.delete_btn.pack(side=tk.LEFT, padx=2)

        self.lock_btn = ttk.Button(toolbar, text="Заблокировать", command=self._lock_vault)
        self.lock_btn.pack(side=tk.LEFT, padx=2)

        self.status_bar_frame = ttk.Frame(self.root)
        self.status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_bar = ttk.Label(
            self.status_bar_frame,
            text="Готов | Статус: разблокировано",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.clipboard_status_bar = ClipboardStatusBar(
            self.status_bar_frame,
            self.clipboard_service
        )
        self.clipboard_status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        search_frame = ttk.Frame(self.root)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5))

        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._search_entries())
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        self.tree_frame = ttk.Frame(self.root)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("ID", "Название", "Логин", "URL", "Обновлено")
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        self.tree.heading("ID", text="ID")
        self.tree.heading("Название", text="Название")
        self.tree.heading("Логин", text="Логин")
        self.tree.heading("URL", text="URL")
        self.tree.heading("Обновлено", text="Обновлено")

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Название", width=200)
        self.tree.column("Логин", width=150)
        self.tree.column("URL", width=350)
        self.tree.column("Обновлено", width=150)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<Double-Button-1>', lambda e: self._edit_entry())
        self.tree.bind('<Delete>', lambda e: self._delete_entry())
        self.tree.bind('<Button-3>', self._on_right_click)

        self.root.bind('<Any-KeyPress>', self._on_activity)
        self.root.bind('<Any-ButtonPress>', self._on_activity)

    def _bind_events(self):
        events.subscribe("entry_created", lambda data: self._refresh_entries())
        events.subscribe("entry_updated", lambda data: self._refresh_entries())
        events.subscribe("entry_deleted", lambda data: self._refresh_entries())
        events.subscribe("user_logged_out", lambda data: self._on_logout())
        events.subscribe("vault_locked", lambda data: self._on_vault_locked())
        events.subscribe("vault_unlocked", lambda data: self._on_vault_unlocked())
        events.subscribe("clipboard_notification", self._on_clipboard_notification)
        events.subscribe("clipboard_copied", self._on_clipboard_copied)

    def _on_clipboard_notification(self, data):
        if data and 'message' in data:
            self.status_bar.config(text=data['message'])
            self.root.after(3000, lambda: self._refresh_status_text())

    def _on_clipboard_copied(self, data):
        if data:
            self.status_bar.config(text=f"Скопировано: {data.get('data_type', 'данные')}")
            self.root.after(2000, lambda: self._refresh_status_text())

    def _refresh_status_text(self):
        if not self.is_locked_display:
            self.status_bar.config(text="Готов | Статус: разблокировано")

    def _on_activity(self, event=None):
        if not self.is_locked_display and state.is_logged_in:
            self.last_activity = datetime.now()
            state.update_activity()
            self.auth.update_activity()
            self._reset_auto_lock_timer()

    def _start_auto_lock_timer(self):
        self._check_auto_lock()

    def _reset_auto_lock_timer(self):
        if self.auto_lock_id:
            self.root.after_cancel(self.auto_lock_id)
        self._check_auto_lock()

    def _check_auto_lock(self):
        if state.is_inactive(self.auto_lock_minutes) and not self.is_locked_display and state.is_logged_in:
            self._lock_vault()
        else:
            self.auto_lock_id = self.root.after(60000, self._check_auto_lock)

    def _lock_vault(self):
        if state.is_logged_in and not self.is_locked_display:
            state.lock()
            self.is_locked_display = True
            self.key_manager.clear_key()
            self.clipboard_service.is_vault_unlocked = False
            self.clipboard_service.clear_clipboard(reason="vault_locked")
            self._clear_entries_display()

            self.add_btn.config(state='disabled')
            self.edit_btn.config(state='disabled')
            self.delete_btn.config(state='disabled')
            self.search_entry.config(state='disabled')
            self.tree.config(cursor="arrow")

            self.status_bar.config(text="Статус: ЗАБЛОКИРОВАНО - нажмите Разблокировать для входа")
            self.lock_btn.config(text="Разблокировать", command=self._unlock_vault)

            events.publish("vault_locked", {"timestamp": datetime.now().isoformat()})

    def _unlock_vault(self):
        def on_unlock_success():
            state.unlock()
            self.is_locked_display = False
            self.key_manager.load_key()
            self.clipboard_service.is_vault_unlocked = True
            self._refresh_entries()

            self.add_btn.config(state='normal')
            self.edit_btn.config(state='normal')
            self.delete_btn.config(state='normal')
            self.search_entry.config(state='normal')

            self.status_bar.config(text="Готов | Статус: разблокировано")
            self.lock_btn.config(text="Заблокировать", command=self._lock_vault)

            events.publish("vault_unlocked", {"timestamp": datetime.now().isoformat()})

        LoginDialog(self.root, on_unlock_success, is_relogin=True)

    def _clear_entries_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _on_vault_locked(self):
        if not self.is_locked_display:
            self._lock_vault()

    def _on_vault_unlocked(self):
        pass

    def _on_logout(self):
        self._clear_entries_display()
        state.logout()
        self.key_manager.clear_key()
        self.clipboard_service.is_vault_unlocked = False
        self.clipboard_service.clear_clipboard(reason="logout")
        self.status_bar.config(text="Статус: ВЫ ВЫШЛИ - перезапустите приложение")

        self.add_btn.config(state='disabled')
        self.edit_btn.config(state='disabled')
        self.delete_btn.config(state='disabled')
        self.lock_btn.config(state='disabled')
        self.search_entry.config(state='disabled')

    def _copy_password_to_clipboard(self, entry_id, password):
        if self.is_locked_display:
            messagebox.showwarning("Внимание", "Хранилище заблокировано")
            return
        if not password:
            messagebox.showwarning("Внимание", "Нет пароля для копирования")
            return
        self.clipboard_service.copy_to_clipboard(password, "password", entry_id)

    def _copy_username_to_clipboard(self, entry_id, username):
        if self.is_locked_display:
            messagebox.showwarning("Внимание", "Хранилище заблокировано")
            return
        if not username:
            messagebox.showwarning("Внимание", "Нет логина для копирования")
            return
        self.clipboard_service.copy_to_clipboard(username, "username", entry_id)

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return

        self.tree.selection_set(item)

        values = self.tree.item(item, 'values')
        if not values:
            return

        entry_id = values[0]

        try:
            entry = self.entry_manager.get_entry(int(entry_id))
            password = entry.get('password', '')
            username = entry.get('username', '')

            popup = tk.Menu(self.root, tearoff=0)
            popup.add_command(
                label="Копировать пароль",
                command=lambda eid=entry_id, p=password: self._copy_password_to_clipboard(eid, p)
            )
            popup.add_command(
                label="Копировать логин",
                command=lambda eid=entry_id, u=username: self._copy_username_to_clipboard(eid, u)
            )
            popup.add_separator()
            popup.add_command(label="Редактировать", command=self._edit_entry)
            popup.add_command(label="Удалить", command=self._delete_entry)

            popup.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"Error: {e}")

    def _refresh_entries(self):
        if self.is_locked_display:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            entries = self.entry_manager.get_all_entries()

            for entry in entries:
                entry_id = entry.get('id', '')
                username = entry.get('username', '')

                username_display = username[:4] + '****' if len(username) > 4 else username

                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        entry_id,
                        entry.get('title', ''),
                        username_display,
                        entry.get('url', '')[:50],
                        entry.get('updated_at', '')[:19]
                    )
                )

            self.status_bar.config(text=f"Загружено записей: {len(entries)} | Статус: разблокировано")
        except Exception as e:
            self.status_bar.config(text=f"Ошибка загрузки: {str(e)}")

    def _search_entries(self):
        if self.is_locked_display:
            return

        query = self.search_var.get()
        if not query:
            self._refresh_entries()
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            entries = self.entry_manager.search(query)
            for entry in entries:
                entry_id = entry.get('id', '')
                username = entry.get('username', '')

                username_display = username[:4] + '****' if len(username) > 4 else username

                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        entry_id,
                        entry.get('title', ''),
                        username_display,
                        entry.get('url', '')[:50],
                        entry.get('updated_at', '')[:19]
                    )
                )

            self.status_bar.config(text=f"Найдено: {len(entries)} записей")
        except Exception as e:
            self.status_bar.config(text=f"Ошибка поиска: {str(e)}")

    def _add_entry(self):
        if self.is_locked_display:
            messagebox.showwarning("Внимание", "Хранилище заблокировано")
            return

        dialog = EntryDialog(self.root, self.password_gen)
        if dialog.result:
            try:
                entry_id = self.entry_manager.create_entry(dialog.result)
                self._refresh_entries()
                self.status_bar.config(text=f"Запись создана (ID: {entry_id})")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать запись: {str(e)}")

    def _edit_entry(self):
        if self.is_locked_display:
            messagebox.showwarning("Внимание", "Хранилище заблокировано")
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите запись для редактирования")
            return

        item = selection[0]
        values = self.tree.item(item, 'values')
        if not values:
            return

        entry_id = values[0]

        try:
            entry = self.entry_manager.get_entry(int(entry_id))
            dialog = EntryDialog(self.root, self.password_gen, entry)
            if dialog.result:
                self.entry_manager.update_entry(int(entry_id), dialog.result)
                self._refresh_entries()
                self.status_bar.config(text="Запись обновлена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить запись: {str(e)}")

    def _delete_entry(self):
        if self.is_locked_display:
            messagebox.showwarning("Внимание", "Хранилище заблокировано")
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите запись для удаления")
            return

        if not messagebox.askyesno("Подтверждение", "Удалить выбранную запись?"):
            return

        item = selection[0]
        values = self.tree.item(item, 'values')
        if not values:
            return

        entry_id = values[0]

        if entry_id:
            try:
                self.entry_manager.delete_entry(int(entry_id))
                self._refresh_entries()
                self.status_bar.config(text="Запись удалена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить запись: {str(e)}")

    def _change_master_password(self):
        if self.is_locked_display:
            messagebox.showwarning("Внимание", "Хранилище заблокировано")
            return

        if not self.key_manager.load_key():
            messagebox.showwarning("Внимание", "Необходимо войти в систему")
            return

        dialog = ChangePasswordDialog(
            self.root,
            db,
            self.entry_manager,
            self.key_manager,
            self.auth
        )

        if dialog.result:
            self.status_bar.config(text="Пароль успешно изменен")

    def _logout(self):
        if messagebox.askyesno("Подтверждение", "Выйти из системы? Все несохраненные данные будут сохранены."):
            self._clear_entries_display()
            self.auth.logout()
            self.key_manager.clear_key()
            self.clipboard_service.is_vault_unlocked = False
            self.clipboard_service.clear_clipboard(reason="logout")
            state.logout()
            self.status_bar.config(text="Статус: ВЫ ВЫШЛИ - перезапустите приложение")

            self.add_btn.config(state='disabled')
            self.edit_btn.config(state='disabled')
            self.delete_btn.config(state='disabled')
            self.lock_btn.config(state='disabled')
            self.search_entry.config(state='disabled')

            events.publish("user_logged_out", {})

    def _show_settings(self):
        if self.is_locked_display:
            messagebox.showwarning("Внимание", "Хранилище заблокировано")
            return

        SettingsDialog(self.root)

    def _about(self):
        about_text = """CryptoSafe Manager - Безопасный менеджер паролей

Версия: 1.0.0 (Sprint 4)
Криптография: AES-256-GCM, Argon2id, PBKDF2

Особенности:
- Безопасное хранение паролей
- Автоматическая блокировка при неактивности
- Защита от brute-force атак
- Генерация надежных паролей
- AES-256-GCM шифрование каждой записи
- Защищенный буфер обмена с автоочисткой (Sprint 4)
- Копирование пароля/логина по правому клику (UI-1)
- Статус-бар с таймером обратного отсчета (UI-2)
- Нотификации при копировании (UI-3)

2025 CryptoSafe Team"""

        messagebox.showinfo("О программе", about_text)

    def _quit(self):
        self.clipboard_service.shutdown()
        if messagebox.askokcancel("Выход", "Выйти из приложения?"):
            self.key_manager.clear_key()
            self.root.quit()
            self.root.destroy()