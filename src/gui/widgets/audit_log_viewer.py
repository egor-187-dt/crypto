import tkinter as tk


class AuditLogViewer(tk.Text):
    def __init__(self, master, **kwargs):
        super().__init__(master, state='disabled', **kwargs)

    def add_log(self, text):
        self.config(state='normal')
        self.insert(tk.END, text + "\n")
        self.config(state='disabled')