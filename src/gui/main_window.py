import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from src.database.db import db
from src.core.key_manager import KeyManager
from src.core.state_manager import state
from src.gui.setup_wizard import SetupWizard
from src.core.events import events  # ИМПОРТ ДОБАВЛЕН
import hashlib
import os


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("CryptoSafe")
        self.root.geometry("600x400")

        self.key_manager = KeyManager()

        if db.conn is None:
            db.connect()

        from tkinter.simpledialog import askstring

        result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
        if not result:
            messagebox.showerror("Ошибка", "Нет сохраненного пароля. Запустите настройку заново.")
            self.root.quit()
            return

        saved_hash, salt = result[0]

        pwd = askstring("Вход", f"Мастер-пароль для {os.path.basename(db.db_path)}:", show='*')
        if not pwd:
            self.root.quit()
            return

        input_hash = hashlib.sha256((pwd + salt).encode()).hexdigest()

        if input_hash != saved_hash:
            messagebox.showerror("Ошибка", "Неверный пароль!")
            self.root.quit()
            return

        key = self.key_manager.derive_key(pwd, b'salt123')
        self.key_manager.store_key(key)
        state.login()

        self._create_menu()
        self._create_ui()
        self.load_data()

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
        file_menu.add_command(label="Выход", command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Правка", menu=edit_menu)
        edit_menu.add_command(label="Добавить", command=self.add_entry)
        edit_menu.add_command(label="Изменить", command=self.edit_entry)
        edit_menu.add_command(label="Удалить", command=self.delete_entry)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Логи", command=self.show_logs)
        view_menu.add_command(label="Настройки", command=self.show_settings)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.about)

        file_menu.add_separator()
        file_menu.add_command(label=f"Текущая: {os.path.basename(db.db_path)}", state="disabled")

    def _create_ui(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Добавить", command=self.add_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Удалить", command=self.delete_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Обновить", command=self.load_data).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Название", "Логин", "URL")
        self.table = ttk.Treeview(self.root, columns=columns, show="headings")

        self.table.heading("ID", text="ID")
        self.table.column("ID", width=50)

        for col in columns[1:]:
            self.table.heading(col, text=col)
            self.table.column(col, width=150)

        self.table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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
        """Создать новую базу данных с новым мастер-паролем"""
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

        # Закрываем текущее соединение
        db.close()

        # Сохраняем новый путь в конфиг
        from src.core.config import config
        config.set("db_path", filename)

        # Показываем сообщение
        messagebox.showinfo("Новая БД",
                            "Файл создан. Программа перезапустится и попросит создать новый пароль.")

        # Перезапускаем программу
        self.root.quit()
        import main
        main.main()

    def open_other_db(self):
        """Открыть другую существующую базу данных"""
        filename = filedialog.askopenfilename(
            title="Выберите файл базы данных",
            filetypes=[("SQLite DB", "*.db"), ("Все файлы", "*.*")]
        )
        if not filename:
            return

        # Закрываем текущее соединение
        db.close()

        # Сохраняем новый путь в конфиг
        from src.core.config import config
        config.set("db_path", filename)

        # Показываем сообщение
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

    # ========== ФУНКЦИЯ ДОБАВЛЕНИЯ (С СОБЫТИЕМ) ==========
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

        pwd_bytes = password.encode()
        encrypted = bytes([pwd_bytes[i] ^ key[i % len(key)] for i in range(len(pwd_bytes))])

        db.execute(
            "INSERT INTO vault_entries (title, username, encrypted_password, url) VALUES (?, ?, ?, ?)",
            (title, username, encrypted, "")
        )

        self.load_data()
        messagebox.showinfo("Готово", "Запись добавлена")

        # ПУБЛИКУЕМ СОБЫТИЕ
        events.publish("entry_added", {"title": title, "username": username})
        print(f"Событие: добавлена запись {title}")

    # ========== ФУНКЦИЯ УДАЛЕНИЯ (С СОБЫТИЕМ) ==========
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

            # ПУБЛИКУЕМ СОБЫТИЕ
            events.publish("entry_deleted", {"id": entry_id, "name": entry_name})
            print(f"Событие: удалена запись {entry_name}")