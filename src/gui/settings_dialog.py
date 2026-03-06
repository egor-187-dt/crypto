import tkinter as tk
from tkinter import ttk, messagebox


class SettingsDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Настройки")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)

        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_notebook()
        self._create_buttons()

    def _create_notebook(self):
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="Безопасность")

        tk.Label(security_frame, text="Таймаут буфера обмена (сек):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.StringVar(value="30")
        tk.Entry(security_frame, textvariable=self.timeout_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)

        self.auto_lock_var = tk.BooleanVar(value=True)
        tk.Checkbutton(security_frame, text="Автоблокировка при бездействии",
                       variable=self.auto_lock_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        appearance_frame = ttk.Frame(notebook)
        notebook.add(appearance_frame, text="Внешний вид")

        tk.Label(appearance_frame, text="Тема:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.theme_var = tk.StringVar(value="Светлая")
        theme_combo = ttk.Combobox(appearance_frame, textvariable=self.theme_var,
                                   values=["Светлая", "Темная", "Системная"], state="readonly")
        theme_combo.grid(row=0, column=1, sticky=tk.W, pady=5)

        tk.Label(appearance_frame, text="Язык:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.lang_var = tk.StringVar(value="Русский")
        lang_combo = ttk.Combobox(appearance_frame, textvariable=self.lang_var,
                                  values=["Русский", "Английский"], state="readonly")
        lang_combo.grid(row=1, column=1, sticky=tk.W, pady=5)

        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Дополнительно")

        self.backup_var = tk.BooleanVar(value=False)
        tk.Checkbutton(advanced_frame, text="Автоматическое резервное копирование",
                       variable=self.backup_var).grid(row=0, column=0, sticky=tk.W, pady=5)

        tk.Button(advanced_frame, text="Экспортировать данные",
                  command=self.export_data).grid(row=1, column=0, sticky=tk.W, pady=5)

    def _create_buttons(self):
        btn_frame = tk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(btn_frame, text="OK", command=self.save_settings, width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT, padx=5)

    def save_settings(self):
        messagebox.showinfo("Настройки", "Настройки сохранены (заглушка)")
        self.dialog.destroy()

    def export_data(self):
        messagebox.showinfo("Экспорт", "Функция экспорта будет позже")