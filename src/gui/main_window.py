import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from src.database.db import db
from src.core.key_manager import KeyManager
from src.core.state_manager import state
from src.core.crypto.authentication import Authenticator
from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.key_storage import key_storage
from src.gui.change_password_dialog import ChangePasswordDialog
from src.core.events import events
import hashlib
import os
import base64
import time


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("CryptoSafe")
        self.root.geometry("600x400")

        self.key_manager = KeyManager()
        self.kd = KeyDerivation()
        self.auth = Authenticator(self.kd)

        if db.conn is None:
            db.connect()

        # Проверяем наличие мастер-пароля
        result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
        if not result:
            messagebox.showerror("Ошибка", "Нет сохраненного пароля. Запустите настройку заново.")
            self.root.quit()
            return

        saved_hash, salt_value = result[0]

        # Показываем диалог входа
        if not self.show_login_dialog(saved_hash, salt_value):
            self.root.quit()
            return

        self._create_menu()
        self._create_ui()
        self.load_data()

        # Подписываемся на события
        events.subscribe("user_logged_out", self.on_logout)

        # Запускаем проверку автоблокировки
        self.check_auto_lock()

    def show_login_dialog(self, stored_hash, salt_value):
        """Показывает диалог входа"""
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

        result = [False]  # используем список для изменения в замыкании

        def try_login():
            pwd = pass_entry.get()
            if not pwd:
                return

            # Пробуем разные форматы соли
            try:
                # Сначала пробуем как hex
                salt = bytes.fromhex(salt_value) if salt_value else b''
            except ValueError:
                # Если не hex - это старая БД, используем как есть
                if salt_value:
                    # Конвертируем строку в байты (для "fixed_salt")
                    salt = salt_value.encode('utf-8')
                    print(f"Использую старую соль: {salt_value}")
                else:
                    salt = b''

            # Проверяем, старый это хеш (SHA256) или новый (Argon2)
            success = False
            enc_key = None

            # Пробуем новый способ (Argon2)
            try:
                if stored_hash.startswith('$argon2'):
                    success, enc_key = self.auth.authenticate(pwd, stored_hash, salt)
            except:
                pass

            # Если не получилось, пробуем старый способ (SHA256)
            if not success:
                # Старый формат - SHA256
                input_hash = hashlib.sha256((pwd + salt_value).encode()).hexdigest()
                if input_hash == stored_hash:
                    success = True
                    # Для старого формата выводим ключ через старый способ
                    enc_key = self.key_manager.derive_key(pwd, b'salt123')
                    print("Использую старую аутентификацию (SHA256)")

            if success:
                if enc_key:
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

        # Обработка Enter
        pass_entry.bind("<Return>", lambda e: try_login())

        self.root.wait_window(dialog)
        return result[0]

    def check_auto_lock(self):
        """Проверяет автоблокировку"""
        if key_storage.auto_lock_check():
            self.lock_vault()

        # Проверяем каждую минуту
        self.root.after(60000, self.check_auto_lock)

    def lock_vault(self):
        """Блокирует хранилище"""
        state.lock()
        key_storage.clear_key()
        messagebox.showinfo("Блокировка", "Хранилище заблокировано из-за неактивности")
        self.show_login_dialog_after_lock()

    def show_login_dialog_after_lock(self):
        """Показывает диалог для разблокировки"""
        result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
        if result:
            if self.show_login_dialog(result[0][0], result[0][1]):
                state.unlock("")
                self.load_data()

    def on_logout(self, data):
        """Обработчик выхода"""
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
        file_menu.add_command(label="Открыть запись", command=self.open_entry)
        file_menu.add_command(label="Резервная копия", command=self.backup)
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
        view_menu.add_command(label="Логи", command=self.show_logs)
        view_menu.add_command(label="Настройки", command=self.show_settings)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.about)

        file_menu.add_separator()
        file_menu.add_command(label=f"Текущая: {os.path.basename(db.db_path)}", state="disabled")

    def logout(self):
        """Выход из системы"""
        self.auth.logout()
        self.key_manager.clear_key()
        state.logout()
        events.publish("user_logged_out", {})
        self.root.quit()

    def change_password(self):
        """Смена мастер-пароля"""
        ChangePasswordDialog(self.root, self.key_manager, self.kd, self.auth)

    def _create_ui(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Добавить", command=self.add_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Удалить", command=self.delete_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Показать пароль", command=self.show_password).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Обновить", command=self.load_data).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Название", "Логин", "URL")
        self.table = ttk.Treeview(self.root, columns=columns, show="headings")

        self.table.heading("ID", text="ID")
        self.table.column("ID", width=50)

        for col in columns[1:]:
            self.table.heading(col, text=col)
            self.table.column(col, width=150)

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

        messagebox.showinfo("Расположение БД",
                            f"Файл: {db_file}\n"
                            f"Папка: {db_folder}\n\n"
                            f"Полный путь:\n{db_path}")

    def create_new_db(self):
        result = messagebox.askyesno("Создать новую БД",
                                     "Будет создан новый файл базы данных.\n"
                                     "Продолжить?")
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

        messagebox.showinfo("Новая БД",
                            "Файл создан. Программа перезапустится и попросит создать новый пароль.")

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

        messagebox.showinfo("Открыть БД",
                            f"Переключение на {os.path.basename(filename)}.\n"
                            "Программа перезапустится и запросит пароль от этой БД.")

        self.root.quit()
        import main
        main.main()

    def new_entry(self):
        self.add_entry()

    def open_entry(self):
        selected = self.table.selection()
        if selected:
            self.edit_entry()
        else:
            messagebox.showinfo("Открыть", "Выбери запись из таблицы")

    def backup(self):
        messagebox.showinfo("Резервная копия", "Функция будет позже")

    def edit_entry(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Упс", "Сначала выбери запись")
            return
        messagebox.showinfo("Изменить", "Функция изменения будет позже")

    def show_logs(self):
        messagebox.showinfo("Логи", "Просмотр логов (заглушка)")

    def show_settings(self):
        from src.gui.settings_dialog import SettingsDialog
        SettingsDialog(self.root)

    def about(self):
        messagebox.showinfo("О программе", "CryptoSafe Manager\nВерсия 1.0\n\nНесколько БД поддерживается")

    def load_data(self):
        for row in self.table.get_children():
            self.table.delete(row)

        try:
            rows = db.fetch_all("SELECT id, title, username, url FROM vault_entries")
            for row in rows:
                self.table.insert("", "end", values=row)
            self.status.config(text=f"Записей: {len(rows)} | БД: {os.path.basename(db.db_path)}")
        except Exception as e:
            self.status.config(text=f"Ошибка: {e}")

    # добавление записи( base64)
    def add_entry(self):
        title = simpledialog.askstring("Добавить", "Название:")
        if not title:
            return

        username = simpledialog.askstring("Добавить", "Логин:")
        if not username:
            return

        password = simpledialog.askstring("Добавить", "Пароль:", show="*")
        if not password:
            return

        key = self.key_manager.load_key()
        if not key:
            messagebox.showerror("Ошибка", "Нет ключа")
            return

        # Шифруем пароль (XOR)
        pwd_bytes = password.encode()
        encrypted_bytes = bytes([pwd_bytes[i] ^ key[i % len(key)] for i in range(len(pwd_bytes))])

        # конвертируем байты в текст (base64)
        encrypted_text = base64.b64encode(encrypted_bytes).decode('ascii')

        # Сохраняем в БД (TEXT)
        db.execute(
            "INSERT INTO vault_entries (title, username, encrypted_password, url) VALUES (?, ?, ?, ?)",
            (title, username, encrypted_text, "")
        )

        self.load_data()
        messagebox.showinfo("Готово", "Запись добавлена")

        events.publish("entry_added", {"title": title, "username": username})
        print(f"Событие: добавлена запись {title}")

    # удаление записи
    def delete_entry(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Упс", "Сначала выбери запись")
            return

        item = self.table.item(selected[0])
        entry_id = item['values'][0]
        entry_name = item['values'][1]

        if messagebox.askyesno("Подтверждение", f"Точно удалить '{entry_name}'?"):
            db.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))
            self.load_data()
            messagebox.showinfo("Готово", "Запись удалена")

            events.publish("entry_deleted", {"id": entry_id, "name": entry_name})
            print(f"Событие: удалена запись {entry_name}")

    # фунция показа пароля
    def show_password(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Упс", "Сначала выбери запись")
            return

        item = self.table.item(selected[0])
        entry_id = item['values'][0]
        entry_name = item['values'][1]

        # Получаем зашифрованный пароль из БД
        result = db.fetch_all("SELECT encrypted_password FROM vault_entries WHERE id = ?", (entry_id,))
        if not result:
            messagebox.showerror("Ошибка", "Не удалось получить пароль")
            return

        encrypted_text = result[0][0]  # строка base64

        # Декодируем из base64
        try:
            encrypted_bytes = base64.b64decode(encrypted_text)
        except:
            messagebox.showerror("Ошибка", "Не удалось декодировать пароль")
            return

        # Расшифровываем XOR
        key = self.key_manager.load_key()
        if not key:
            messagebox.showerror("Ошибка", "Нет ключа")
            return

        decrypted_bytes = bytes([encrypted_bytes[i] ^ key[i % len(key)] for i in range(len(encrypted_bytes))])

        try:
            password = decrypted_bytes.decode('utf-8')
        except:
            password = str(decrypted_bytes)

        # Показываем пароль
        messagebox.showinfo(f"Пароль для {entry_name}", f"Логин: {item['values'][2]}\nПароль: {password}")