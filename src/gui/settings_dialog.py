import tkinter as tk
from tkinter import ttk, messagebox

from src.core.config import config
from src.core.events import events
from src.core.clipboard import get_clipboard_service


class SettingsDialog:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Настройки")
        self.dialog.geometry("550x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.clipboard_service = get_clipboard_service(config)

        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (550 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self._create_ui()
        self._load_settings()

        self.dialog.wait_window()

    def _create_ui(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка: Безопасность (существующая)
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

        # Вкладка: Буфер обмена (новая, CFG-1, CFG-3)
        clipboard_frame = ttk.Frame(notebook, padding="10")
        notebook.add(clipboard_frame, text="Буфер обмена")

        # Пресеты (CFG-3)
        preset_frame = ttk.LabelFrame(clipboard_frame, text="Пресеты", padding="10")
        preset_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 15))

        ttk.Button(preset_frame, text="Standard (30 сек)",
                   command=lambda: self._apply_preset('standard')).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="Secure (15 сек)",
                   command=lambda: self._apply_preset('secure')).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="Public Computer (5 сек)",
                   command=lambda: self._apply_preset('public_computer')).pack(side=tk.LEFT, padx=5)

        # Таймаут автоочистки (CLIP-2)
        ttk.Label(clipboard_frame, text="Автоочистка (секунд):").grid(row=1, column=0, sticky='w', pady=5)
        self.clipboard_timeout_var = tk.StringVar()
        self.clipboard_timeout_spinbox = ttk.Spinbox(
            clipboard_frame,
            from_=5,
            to=300,
            textvariable=self.clipboard_timeout_var,
            width=10
        )
        self.clipboard_timeout_spinbox.grid(row=1, column=1, sticky='w', padx=10, pady=5)
        ttk.Label(clipboard_frame, text="0 = никогда не очищать", font=("Arial", 8)).grid(row=1, column=2, padx=5)

        # Уровень безопасности
        ttk.Label(clipboard_frame, text="Уровень безопасности:").grid(row=2, column=0, sticky='w', pady=5)
        self.security_level_var = tk.StringVar()
        self.security_level_combo = ttk.Combobox(
            clipboard_frame,
            textvariable=self.security_level_var,
            values=["basic", "advanced", "paranoid"],
            state="readonly",
            width=15
        )
        self.security_level_combo.grid(row=2, column=1, sticky='w', padx=10, pady=5)

        ttk.Label(clipboard_frame, text="basic=30с, advanced=15с, paranoid=5с",
                  font=("Arial", 8)).grid(row=2, column=2, padx=5)

        # Уведомления
        self.notifications_var = tk.BooleanVar()
        ttk.Checkbutton(
            clipboard_frame,
            text="Показывать уведомления при копировании/очистке",
            variable=self.notifications_var
        ).grid(row=3, column=0, columnspan=3, sticky='w', pady=5)

        # Ускоренная очистка при подозрительной активности
        self.accelerate_var = tk.BooleanVar()
        ttk.Checkbutton(
            clipboard_frame,
            text="Ускорять очистку при обнаружении внешнего доступа",
            variable=self.accelerate_var
        ).grid(row=4, column=0, columnspan=3, sticky='w', pady=5)

        # Информация о текущем состоянии
        status_frame = ttk.LabelFrame(clipboard_frame, text="Текущее состояние", padding="10")
        status_frame.grid(row=5, column=0, columnspan=3, sticky='ew', pady=15)

        self.status_text = tk.StringVar(value="Неактивен")
        ttk.Label(status_frame, textvariable=self.status_text, font=("Arial", 9)).pack(anchor='w')

        # Вкладка: Интерфейс (существующая)
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

        # Кнопки
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

    def _apply_preset(self, preset_name):
        """Применить пресет (CFG-3)"""
        if self.clipboard_service:
            self.clipboard_service.apply_preset(preset_name)
            self._load_settings()
            self._update_status()

    def _update_status(self):
        """Обновить отображение статуса"""
        if self.clipboard_service:
            status = self.clipboard_service.get_status()
            if status['active']:
                self.status_text.set(f"Активен: {status['data_type']}, осталось {status['remaining_seconds']:.0f}с")
            else:
                self.status_text.set("Неактивен")

    def _load_settings(self):
        """Загрузить настройки из конфига"""
        # Безопасность
        self.auto_lock_var.set(str(config.get("auto_lock_timeout", 60)))
        self.cache_timeout_var.set(str(config.get("cache_timeout", 60)))

        # Буфер обмена
        self.clipboard_timeout_var.set(str(config.get("clipboard_timeout", 30)))
        self.security_level_var.set(config.get("clipboard_security_level", "basic"))
        self.notifications_var.set(config.get("clipboard_notifications", True))
        self.accelerate_var.set(config.get("clipboard_accelerate_on_access", False))

        # Интерфейс
        self.theme_var.set(config.get("theme", "dark"))

        self._update_status()

    def _save_settings(self):
        try:
            # Валидация
            auto_lock = int(self.auto_lock_var.get())
            cache_timeout = int(self.cache_timeout_var.get())
            clipboard_timeout = int(self.clipboard_timeout_var.get())

            if auto_lock < 5 or auto_lock > 240:
                raise ValueError("Автоблокировка должна быть от 5 до 240 минут")

            if cache_timeout < 15 or cache_timeout > 120:
                raise ValueError("Таймаут кэша должен быть от 15 до 120 минут")

            if clipboard_timeout < 0 or clipboard_timeout > 300:
                raise ValueError("Таймаут буфера должен быть от 0 до 300 секунд")

            # Сохраняем настройки безопасности
            config.set("auto_lock_timeout", auto_lock)
            config.set("cache_timeout", cache_timeout)

            # Сохраняем настройки буфера обмена (CFG-2)
            config.set("clipboard_timeout", clipboard_timeout)
            config.set("clipboard_security_level", self.security_level_var.get())
            config.set("clipboard_notifications", self.notifications_var.get())
            config.set("clipboard_accelerate_on_access", self.accelerate_var.get())

            # Применяем к сервису
            if self.clipboard_service:
                self.clipboard_service.set_timeout(clipboard_timeout)
                self.clipboard_service.set_security_level(self.security_level_var.get())
                self.clipboard_service.set_notifications(self.notifications_var.get())
                self.clipboard_service.set_accelerate_on_access(self.accelerate_var.get())

            # Сохраняем настройки интерфейса
            config.set("theme", self.theme_var.get())

            events.publish("settings_updated", {
                "auto_lock_timeout": auto_lock,
                "cache_timeout": cache_timeout,
                "clipboard_timeout": clipboard_timeout,
                "clipboard_security_level": self.security_level_var.get(),
                "clipboard_notifications": self.notifications_var.get(),
                "clipboard_accelerate_on_access": self.accelerate_var.get(),
                "theme": self.theme_var.get()
            })

            messagebox.showinfo("Успех", "Настройки сохранены", parent=self.dialog)
            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Ошибка", str(e), parent=self.dialog)