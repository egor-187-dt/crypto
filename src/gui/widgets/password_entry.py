import tkinter as tk


class PasswordEntry(tk.Entry):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, show="*", **kwargs)
        self.show_pass = False

        # Кнопка показать пароль
        self.btn = tk.Button(master, text="Show", command=self.toggle)
        self.btn.pack(side=tk.RIGHT)

    def toggle(self):
        if self.show_pass:
            self.config(show="*")
            self.show_pass = False
        else:
            self.config(show="")
            self.show_pass = True