"""
Main Window for CryptoSafe Manager - Updated for Sprint 2 with working lock
"""
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
from src.gui.entry_dialog import EntryDialog
from src.gui.change_password_dialog import ChangePasswordDialog
from src.gui.login_dialog import LoginDialog
from src.database.db import db


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("CryptoSafe Manager")
        self.root.geometry("900x600")

        self.kd = KeyDerivation()
        self.key_manager = KeyManager()
        self.auth = Authenticator(self.kd)
        self.entry_manager = EntryManager(db, self.key_manager)
        self.password_gen = PasswordGenerator()

        self.last_activity = datetime.now()
        self.auto_lock_id = None
        self.auto_lock_minutes = config.get("auto_lock_timeout", 60)
        self.is_locked_display = False

        self._setup_ui()
        self._bind_events()
        self._start_auto_lock_timer()
        self._refresh_entries()

        state.login()
        state.update_activity()

        events.publish("main_window_ready", {})

    def _setup_ui(self):
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

        self.status_bar = ttk.Label(
            self.root,
            text="Готов | Статус: разблокировано",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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

        self.tree.column("ID", width=50)
        self.tree.column("Название", width=200)
        self.tree.column("Логин", width=150)
        self.tree.column("URL", width=200)
        self.tree.column("Обновлено", width=150)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<Double-Button-1>', lambda e: self._edit_entry())
        self.tree.bind('<Delete>', lambda e: self._delete_entry())

        self.root.bind('<Any-KeyPress>', self._on_activity)
        self.root.bind('<Any-ButtonPress>', self._on_activity)

    def _bind_events(self):
        events.subscribe("entry_created", lambda data: self._refresh_entries())
        events.subscribe("entry_updated", lambda data: self._refresh_entries())
        events.subscribe("entry_deleted", lambda data: self._refresh_entries())
        events.subscribe("user_logged_out", lambda data: self._on_logout())
        events.subscribe("vault_locked", lambda data: self._on_vault_locked())
        events.subscribe("vault_unlocked", lambda data: self._on_vault_unlocked())

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
        self.status_bar.config(text="Статус: ВЫ ВЫШЛИ - перезапустите приложение")

        self.add_btn.config(state='disabled')
        self.edit_btn.config(state='disabled')
        self.delete_btn.config(state='disabled')
        self.lock_btn.config(state='disabled')
        self.search_entry.config(state='disabled')

    def _refresh_entries(self):
        if self.is_locked_display:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            entries = self.entry_manager.get_all_entries()
            for entry in entries:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        entry.get('id', '')[:8],
                        entry.get('title', ''),
                        entry.get('username', ''),
                        entry.get('url', '')[:50],
                        entry.get('updated_at', '')[:19]
                    ),
                    tags=(entry.get('id', ''),)
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
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        entry.get('id', '')[:8],
                        entry.get('title', ''),
                        entry.get('username', ''),
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

        item = self.tree.item(selection[0])
        entry_id = item['values'][0] if item['values'] else None

        if not entry_id:
            return

        try:
            entry = self.entry_manager.get_entry(entry_id)
            dialog = EntryDialog(self.root, self.password_gen, entry)
            if dialog.result:
                self.entry_manager.update_entry(entry_id, dialog.result)
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

        item = self.tree.item(selection[0])
        entry_id = item['values'][0] if item['values'] else None

        if entry_id:
            try:
                self.entry_manager.delete_entry(entry_id)
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

        from src.gui.settings_dialog import SettingsDialog
        SettingsDialog(self.root)

    def _about(self):
        about_text = """CryptoSafe Manager - Безопасный менеджер паролей

Версия: 1.0.0 (Sprint 2)
Криптография: AES-256-GCM, Argon2id, PBKDF2

Особенности:
- Безопасное хранение паролей
- Автоматическая блокировка при неактивности
- Защита от brute-force атак
- Генерация надежных паролей

2025 CryptoSafe Team"""

        messagebox.showinfo("О программе", about_text)

    def _quit(self):
        if messagebox.askokcancel("Выход", "Выйти из приложения?"):
            self.key_manager.clear_key()
            self.root.quit()
            self.root.destroy()