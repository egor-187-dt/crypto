import tkinter as tk
from tkinter import ttk, messagebox


class EntryDialog:
    def __init__(self, parent, password_gen, entry_data=None):
        self.parent = parent
        self.pwd_gen = password_gen
        self.entry_data = entry_data
        self.result = None

        self.dialog = tk.Toplevel(parent)
        if entry_data:
            self.dialog.title("Редактировать запись")
        else:
            self.dialog.title("Новая запись")
        self.dialog.geometry("500x550")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_ui()
        if entry_data:
            self._fill_data()

        self.dialog.wait_window()

    def _create_ui(self):
        row = 0

        tk.Label(self.dialog, text="Название *").grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.title_entry = tk.Entry(self.dialog, width=40)
        self.title_entry.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        tk.Label(self.dialog, text="Логин").grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.username_entry = tk.Entry(self.dialog, width=40)
        self.username_entry.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        tk.Label(self.dialog, text="URL").grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.url_entry = tk.Entry(self.dialog, width=40)
        self.url_entry.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        tk.Label(self.dialog, text="Пароль *").grid(row=row, column=0, sticky='w', padx=10, pady=5)
        pwd_frame = tk.Frame(self.dialog)
        pwd_frame.grid(row=row, column=1, padx=10, pady=5)

        self.password_entry = tk.Entry(pwd_frame, width=25)
        self.password_entry.pack(side=tk.LEFT)

        tk.Button(pwd_frame, text="Сгенерировать", command=self._generate_password).pack(side=tk.LEFT, padx=5)

        self.strength_label = tk.Label(pwd_frame, text="", fg="gray", font=("Arial", 8))
        self.strength_label.pack(side=tk.LEFT, padx=5)
        row += 1

        tk.Label(self.dialog, text="Категория").grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.category_entry = tk.Entry(self.dialog, width=40)
        self.category_entry.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        tk.Label(self.dialog, text="Теги (через запятую)").grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.tags_entry = tk.Entry(self.dialog, width=40)
        self.tags_entry.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        tk.Label(self.dialog, text="Заметки").grid(row=row, column=0, sticky='nw', padx=10, pady=5)
        self.notes_text = tk.Text(self.dialog, height=5, width=40)
        self.notes_text.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        btn_frame = tk.Frame(self.dialog)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

        tk.Button(btn_frame, text="OK", command=self._save, bg="lightblue", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self._cancel, width=10).pack(side=tk.LEFT, padx=5)

        self.password_entry.bind('<KeyRelease>', self._update_strength)

    def _fill_data(self):
        self.title_entry.insert(0, self.entry_data.get('title', ''))
        self.username_entry.insert(0, self.entry_data.get('username', ''))
        self.url_entry.insert(0, self.entry_data.get('url', ''))
        self.password_entry.insert(0, self.entry_data.get('password', ''))
        self.category_entry.insert(0, self.entry_data.get('category', ''))
        tags = self.entry_data.get('tags', [])
        if tags:
            if isinstance(tags, list):
                self.tags_entry.insert(0, ', '.join(tags))
            else:
                self.tags_entry.insert(0, str(tags))
        self.notes_text.insert('1.0', self.entry_data.get('notes', ''))
        self._update_strength()

    def _generate_password(self):
        pwd = self.pwd_gen.generate()
        self.password_entry.delete(0, tk.END)
        self.password_entry.insert(0, pwd)
        self._update_strength()

    def _update_strength(self, event=None):
        pwd = self.password_entry.get()
        if pwd:
            strength = self.pwd_gen.check_strength(pwd)
            colors = {'weak': 'red', 'medium': 'orange', 'strong': 'green'}
            texts = {'weak': 'Слабый', 'medium': 'Средний', 'strong': 'Сильный'}
            self.strength_label.config(
                text=texts.get(strength['strength'], ''),
                fg=colors.get(strength['strength'], 'gray')
            )
        else:
            self.strength_label.config(text="")

    def _save(self):
        title = self.title_entry.get().strip()
        password = self.password_entry.get()

        if not title or not password:
            messagebox.showerror("Ошибка", "Заполните название и пароль")
            return

        tags_raw = self.tags_entry.get().strip()
        if tags_raw:
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
        else:
            tags = []

        self.result = {
            'title': title,
            'username': self.username_entry.get().strip(),
            'password': password,
            'url': self.url_entry.get().strip(),
            'notes': self.notes_text.get('1.0', tk.END).strip(),
            'category': self.category_entry.get().strip(),
            'tags': tags
        }
        self.dialog.destroy()

    def _cancel(self):
        self.result = None
        self.dialog.destroy()