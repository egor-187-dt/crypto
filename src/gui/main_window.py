import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from src.database.db import db
from src.core.key_manager import KeyManager
from src.core.state_manager import state


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("CryptoSafe")
        self.root.geometry("600x400")

        self.key_manager = KeyManager()

        if db.conn is None:
            db.connect()

        # Просто спрашиваем пароль
        from tkinter.simpledialog import askstring
        pwd = askstring("Вход", "Мастер-пароль:", show='*')
        if pwd:
            key = self.key_manager.derive_key(pwd, b'salt123')
            self.key_manager.store_key(key)
            state.login()
        else:
            self.root.quit()
            return

        self._create_ui()
        self.load_data()

    def _create_ui(self):
        # Кнопки
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Добавить", command=self.add_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Удалить", command=self.delete_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Обновить", command=self.load_data).pack(side=tk.LEFT, padx=5)

        # Таблица
        columns = ("ID", "Название", "Логин", "URL")
        self.table = ttk.Treeview(self.root, columns=columns, show="headings")

        self.table.heading("ID", text="ID")
        self.table.column("ID", width=50)

        for col in columns[1:]:
            self.table.heading(col, text=col)
            self.table.column(col, width=150)

        self.table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Статус
        self.status = tk.Label(self.root, text="Готов", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X)

    def load_data(self):
        for row in self.table.get_children():
            self.table.delete(row)

        try:
            rows = db.fetch_all("SELECT id, title, username, url FROM vault_entries")
            for row in rows:
                self.table.insert("", "end", values=row)
            self.status.config(text=f"Записей: {len(rows)}")
        except Exception as e:
            self.status.config(text=f"Ошибка: {e}")

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

        # XOR шифрование
        pwd_bytes = password.encode()
        encrypted = bytes([pwd_bytes[i] ^ key[i % len(key)] for i in range(len(pwd_bytes))])

        db.execute(
            "INSERT INTO vault_entries (title, username, encrypted_password, url) VALUES (?, ?, ?, ?)",
            (title, username, encrypted, "")
        )

        self.load_data()
        messagebox.showinfo("Готово", "Запись добавлена")