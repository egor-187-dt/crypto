import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from src.database.db import db
from src.core.key_manager import KeyManager
from src.core.state_manager import state
from src.core.crypto.authentication import Authenticator
from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.key_storage import key_storage
from src.gui.change_password_dialog import ChangePasswordDialog
from src.core.events import events
from src.core.vault.entry_manager import EntryManager
from src.core.vault.password_generator import PasswordGenerator
from src.gui.entry_dialog import EntryDialog
import os


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("CryptoSafe")
        self.root.geometry("700x500")

        self.key_manager = KeyManager()
        self.kd = KeyDerivation()
        self.auth = Authenticator(self.kd)
        self.entry_manager = EntryManager(db, self.key_manager)
        self.password_gen = PasswordGenerator()

        if db.conn is None:
            db.connect()

        result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
        if not result:
            messagebox.showerror("Ошибка", "Нет сохраненного пароля. Запустите настройку заново.")
            self.root.quit()
            return

        saved_hash, salt_value = result[0]

        if not self.show_login_dialog(saved_hash, salt_value):
            self.root.quit()
            return

        self._create_menu()
        self._create_ui()
        self.load_data()

        events.subscribe("user_logged_out", self.on_logout)
        self.check_auto_lock()

    def show_login_dialog(self, stored_hash, salt_value):
        dialog = tk.Toplevel(self.root)
        dialog.title("Вход в CryptoSafe")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Введите мастер-пароль:", font=("Arial", 11)).pack(pady=10)

        pass_entry = tk.Entry(dialog, show="*", width=30)
        pass_entry.pack(pady=5)
        pass_entry.focus()

        status_label = tk.Label(dialog, text="", fg="red")
        status_label.pack()

        result = [False]

        def try_login():
            pwd = pass_entry.get()
            if not pwd:
                return

            try:
                salt = bytes.fromhex(salt_value)
            except:
                salt = b''

            success = False
            enc_key = None

            try:
                if stored_hash.startswith('$argon2'):
                    success, enc_key = self.auth.login(pwd, stored_hash, salt)
            except Exception as e:
                print(f"Auth error: {e}")

            if success and enc_key:
                self.key_manager.store_key(enc_key)
                state.login()
                result[0] = True
                dialog.destroy()
            else:
                self.auth.failed_attempts += 1
                status_label.config(text=f"Неверный пароль (попытка {self.auth.failed_attempts})")
                pass_entry.delete(0, tk.END)
                pass_entry.focus()

        def on_closing():
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_closing)

        tk.Button(dialog, text="Войти", command=try_login, bg="lightblue", width=15).pack(pady=10)
        tk.Button(dialog, text="Отмена", command=on_closing, width=15).pack()

        pass_entry.bind("<Return>", lambda e: try_login())

        self.root.wait_window(dialog)
        return result[0]

    def check_auto_lock(self):
        if key_storage.auto_lock_check():
            self.lock_vault()
        self.root.after(60000, self.check_auto_lock)

    def lock_vault(self):
        state.lock()
        key_storage.clear_key()
        messagebox.showinfo("Блокировка", "Хранилище заблокировано из-за неактивности")
        self.show_login_dialog_after_lock()

    def show_login_dialog_after_lock(self):
        result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
        if result:
            if self.show_login_dialog(result[0][0], result[0][1]):
                state.unlock("")
                self.load_data()

    def on_logout(self, data):
        self.key_manager.clear_key()
        messagebox.showinfo("Выход", "Вы вышли из системы")
        self.root.quit()

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Создать новую БД", command=self.create_new_db)
        file_menu.add_command(label="Открыть другую БД", command=self.open_other_db)
        file_menu.add_command(label="Показать где БД", command=self.show_db_location)
        file_menu.add_separator()
        file_menu.add_command(label="Создать запись", command=self.add_entry)
        file_menu.add_command(label="Открыть запись", command=self.edit_entry)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.logout)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Правка", menu=edit_menu)
        edit_menu.add_command(label="Добавить", command=self.add_entry)
        edit_menu.add_command(label="Изменить", command=self.edit_entry)
        edit_menu.add_command(label="Удалить", command=self.delete_entry)
        edit_menu.add_command(label="Показать пароль", command=self.show_password)
        edit_menu.add_separator()
        edit_menu.add_command(label="Сменить пароль", command=self.change_password)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Настройки", command=self.show_settings)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.about)

        file_menu.add_separator()
        file_menu.add_command(label=f"Текущая: {os.path.basename(db.db_path)}", state="disabled")

    def logout(self):
        self.auth.logout()
        self.key_manager.clear_key()
        state.logout()
        events.publish("user_logged_out", {})
        self.root.quit()

    def change_password(self):
        ChangePasswordDialog(self.root, self.key_manager, self.kd, self.auth)

    def _create_ui(self):
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="🔍 Поиск:").pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind('<KeyRelease>', self.on_search)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Добавить", command=self.add_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Изменить", command=self.edit_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Удалить", command=self.delete_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Показать пароль", command=self.show_password).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Обновить", command=self.load_data).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Название", "Логин", "URL")
        self.table = ttk.Treeview(self.root, columns=columns, show="headings")

        self.table.heading("ID", text="ID")
        self.table.column("ID", width=80)

        for col in columns[1:]:
            self.table.heading(col, text=col)
            self.table.column(col, width=180)

        self.table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.table.bind("<Double-1>", lambda e: self.show_password())

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X)

        self.status = tk.Label(status_frame, text="Готов", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.clipboard_label = tk.Label(status_frame, text="⏱️ Буфер: 30с", bd=1, relief=tk.SUNKEN, width=15)
        self.clipboard_label.pack(side=tk.RIGHT)

    def show_db_location(self):
        db_path = db.db_path
        db_folder = os.path.dirname(db_path)
        db_file = os.path.basename(db_path)
        messagebox.showinfo("Расположение БД", f"Файл: {db_file}\nПапка: {db_folder}\n\nПолный путь:\n{db_path}")

    def create_new_db(self):
        result = messagebox.askyesno("Создать новую БД", "Будет создан новый файл базы данных.\nПродолжить?")
        if not result:
            return

        filename = filedialog.asksaveasfilename(
            title="Создать новую базу данных",
            defaultextension=".db",
            filetypes=[("SQLite DB", "*.db"), ("Все файлы", "*.*")]
        )
        if not filename:
            return

        db.close()
        from src.core.config import config
        config.set("db_path", filename)

        messagebox.showinfo("Новая БД", "Файл создан. Программа перезапустится.")
        self.root.quit()
        import main
        main.main()

    def open_other_db(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл базы данных",
            filetypes=[("SQLite DB", "*.db"), ("Все файлы", "*.*")]
        )
        if not filename:
            return

        db.close()
        from src.core.config import config
        config.set("db_path", filename)

        messagebox.showinfo("Открыть БД", f"Переключение на {os.path.basename(filename)}.")
        self.root.quit()
        import main
        main.main()

    def backup(self):
        messagebox.showinfo("Резервная копия", "Функция будет позже")

    def show_settings(self):
        from src.gui.settings_dialog import SettingsDialog
        SettingsDialog(self.root)

    def about(self):
        messagebox.showinfo("О программе", "CryptoSafe Manager\nВерсия 3.0\nAES-256-GCM шифрование")

    def load_data(self):
        try:
            entries = self.entry_manager.get_all_entries()
            self.refresh_table(entries)
        except Exception as e:
            self.status.config(text=f"Ошибка: {e}")

    def refresh_table(self, entries):
        for row in self.table.get_children():
            self.table.delete(row)

        for e in entries:
            username = e.get('username', '')
            if len(username) > 12:
                username = username[:6] + '...'
            self.table.insert("", "end", values=(
                e.get('id', '')[:8],
                e.get('title', ''),
                username,
                e.get('url', '')
            ))
        self.status.config(text=f"Записей: {len(entries)} | БД: {os.path.basename(db.db_path)}")

    def add_entry(self):
        dialog = EntryDialog(self.root, self.password_gen)
        if dialog.result:
            try:
                self.entry_manager.create_entry(dialog.result)
                self.load_data()
                messagebox.showinfo("Готово", "Запись добавлена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить: {e}")

    def edit_entry(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Упс", "Сначала выбери запись")
            return

        item = self.table.item(selected[0])
        entry_id = item['values'][0]

        try:
            entry = self.entry_manager.get_entry(entry_id)
            dialog = EntryDialog(self.root, self.password_gen, entry)
            if dialog.result:
                self.entry_manager.update_entry(entry_id, dialog.result)
                self.load_data()
                messagebox.showinfo("Готово", "Запись обновлена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось редактировать: {e}")

    def delete_entry(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Упс", "Сначала выбери запись")
            return

        item = self.table.item(selected[0])
        entry_id = item['values'][0]
        entry_name = item['values'][1]

        if messagebox.askyesno("Подтверждение", f"Точно удалить '{entry_name}'?"):
            try:
                self.entry_manager.delete_entry(entry_id)
                self.load_data()
                messagebox.showinfo("Готово", "Запись удалена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")

    def show_password(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Упс", "Сначала выбери запись")
            return

        item = self.table.item(selected[0])
        entry_id = item['values'][0]

        try:
            entry = self.entry_manager.get_entry(entry_id)
            messagebox.showinfo(f"Пароль для {entry['title']}",
                               f"Логин: {entry['username']}\nПароль: {entry['password']}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось расшифровать: {e}")

    def on_search(self, event=None):
        query = self.search_entry.get()
        if query:
            results = self.entry_manager.search(query)
            self.refresh_table(results)
        else:
            self.load_data()