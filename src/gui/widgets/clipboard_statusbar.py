"""
Clipboard status bar widget
"""
import tkinter as tk
from tkinter import ttk


class ClipboardStatusBar(ttk.Frame):

    def __init__(self, master, clipboard_service, **kwargs):
        super().__init__(master, **kwargs)
        self.clipboard_service = clipboard_service
        self.status_var = tk.StringVar(value="Clipboard: Empty")
        self.timer_id = None

        self._create_ui()
        self._start_updates()

    def _create_ui(self):
        self.label = ttk.Label(
            self,
            textvariable=self.status_var,
            font=("Arial", 9),
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.clear_btn = ttk.Button(
            self,
            text="Clear",
            width=6,
            command=self._clear_clipboard
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=5, pady=2)

    def _start_updates(self):
        self._update_status()

    def _update_status(self):
        status = self.clipboard_service.get_status()

        if status['active']:
            remaining = status['remaining_seconds']
            data_type = status['data_type']

            if remaining > 0:
                self.status_var.set(f"Clipboard: {data_type} - clears in {remaining:.0f}s")
            else:
                self.status_var.set(f"Clipboard: {data_type} (no auto-clear)")
        else:
            self.status_var.set("Clipboard: Empty")

        self.timer_id = self.after(500, self._update_status)

    def _clear_clipboard(self):
        self.clipboard_service.clear_clipboard(reason="manual")
        self._update_status()

    def destroy(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
        super().destroy()