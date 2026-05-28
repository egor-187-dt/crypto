import tkinter as tk
from tkinter import ttk, messagebox

from src.core.config import config
from src.core.events import events


class SettingsDialog:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Настройки")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (400 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self._create_ui()
        self._load_settings()

        self.dialog.wait_window()

    def _create_ui(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        security_frame = ttk.Frame(notebook, padding="10")
        notebook.add(security_frame, text="Безопасность")

        ttk.Label(security_frame, text="Автоблокировка (минуты):").grid(row=0, column=0, sticky='w', pady=5)
        self.auto_lock_var = tk.StringVar()
        self.auto_lock_spinbox = ttk.Spinbox(
            security_frame,
            from_=5,
            to=240,
            textvariable=self.auto_lock_var,
            width=10
        )
        self.auto_lock_spinbox.grid(row=0, column=1, sticky='w', padx=10, pady=5)

        ttk.Label(security_frame, text="Таймаут кэша ключа (минуты):").grid(row=1, column=0, sticky='w', pady=5)
        self.cache_timeout_var = tk.StringVar()
        self.cache_timeout_spinbox = ttk.Spinbox(
            security_frame,
            from_=15,
            to=120,
            textvariable=self.cache_timeout_var,
            width=10
        )
        self.cache_timeout_spinbox.grid(row=1, column=1, sticky='w', padx=10, pady=5)

        interface_frame = ttk.Frame(notebook, padding="10")
        notebook.add(interface_frame, text="Интерфейс")

        ttk.Label(interface_frame, text="Тема:").grid(row=0, column=0, sticky='w', pady=5)
        self.theme_var = tk.StringVar()
        self.theme_combo = ttk.Combobox(
            interface_frame,
            textvariable=self.theme_var,
            values=["light", "dark", "system"],
            state="readonly",
            width=15
        )
        self.theme_combo.grid(row=0, column=1, sticky='w', padx=10, pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(
            button_frame,
            text="Сохранить",
            command=self._save_settings
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Отмена",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT)

    def _load_settings(self):
        self.auto_lock_var.set(str(config.get("auto_lock_timeout", 60)))
        self.cache_timeout_var.set(str(config.get("cache_timeout", 60)))
        self.theme_var.set(config.get("theme", "dark"))

    def _save_settings(self):
        try:
            auto_lock = int(self.auto_lock_var.get())
            cache_timeout = int(self.cache_timeout_var.get())

            if auto_lock < 5 or auto_lock > 240:
                raise ValueError("Автоблокировка должна быть от 5 до 240 минут")

            if cache_timeout < 15 or cache_timeout > 120:
                raise ValueError("Таймаут кэша должен быть от 15 до 120 минут")

            config.set("auto_lock_timeout", auto_lock)
            config.set("cache_timeout", cache_timeout)
            config.set("theme", self.theme_var.get())

            events.publish("settings_updated", {
                "auto_lock_timeout": auto_lock,
                "cache_timeout": cache_timeout,
                "theme": self.theme_var.get()
            })

            messagebox.showinfo("Успех", "Настройки сохранены", parent=self.dialog)
            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Ошибка", str(e), parent=self.dialog)