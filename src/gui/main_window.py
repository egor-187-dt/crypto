import tkinter as tk
from tkinter import ttk, messagebox
from src.gui.widgets import SecureTable, PasswordEntry



class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("CryptoSafe Manager - Sprint 1")
        self.root.geometry("800x600")

        self._create_menu()
        self._create_ui()
        self.load_data()

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Добавить", command=self.add_entry)
        menubar.add_cascade(label="Правка", menu=edit_menu)

        self.root.config(menu=menubar)

    def _create_ui(self):
        columns = ("Title", "Username", "URL")
        self.table = SecureTable(self.root, columns=columns)
        self.table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.status_var = tk.StringVar()
        self.status_var.set("Статус: Разблокировано")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_data(self):
        pass

    def add_entry(self):
        messagebox.showinfo("Инфо", "Функция добавления в разработке (Спринт 2)")

    def update_status(self, text):
        self.status_var.set(text)