"""
Clipboard monitoring and defense system
"""
import threading
import time
from typing import Optional, Callable
from datetime import datetime

WIN32_AVAILABLE = False

try:
    import win32clipboard
    import win32con
    import win32gui
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    pass


class ClipboardMonitor:

    def __init__(self, on_external_access_callback: Optional[Callable] = None,
                 on_content_changed_callback: Optional[Callable] = None):
        self.on_external_access = on_external_access_callback
        self.on_content_changed = on_content_changed_callback
        self.is_running = False
        self.monitor_thread = None
        self._hwnd = None
        self._next_viewer = None
        self._last_content_hash = None
        self._access_count = 0
        self._suspicious_activity_detected = False

    def start(self):
        if not WIN32_AVAILABLE:
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self.is_running = False
        if self._hwnd:
            try:
                win32gui.ChangeClipboardChain(self._hwnd, self._next_viewer)
                win32gui.DestroyWindow(self._hwnd)
            except:
                pass

    def _monitor_loop(self):
        if not WIN32_AVAILABLE:
            return

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = "ClipboardMonitorWindow"
        wc.hInstance = win32api.GetModuleHandle()

        try:
            class_atom = win32gui.RegisterClass(wc)
            self._hwnd = win32gui.CreateWindow(
                class_atom, "ClipboardMonitor", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
            )

            self._next_viewer = win32gui.SetClipboardViewer(self._hwnd)

            while self.is_running:
                win32gui.PumpWaitingMessages()
                time.sleep(0.1)
        except Exception:
            pass

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_DRAWCLIPBOARD:
            self._on_clipboard_change()
            if self._next_viewer:
                win32gui.SendMessage(self._next_viewer, msg, wparam, lparam)
        elif msg == win32con.WM_CHANGECBCHAIN:
            self._next_viewer = wparam
        elif msg == win32con.WM_DESTROY:
            if self._next_viewer:
                win32gui.ChangeClipboardChain(hwnd, self._next_viewer)

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _on_clipboard_change(self):
        try:
            import hashlib

            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                current_data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                current_hash = hashlib.sha256(current_data.encode('utf-8')).hexdigest()
            else:
                current_hash = None
            win32clipboard.CloseClipboard()

            if current_hash != self._last_content_hash:
                self._access_count += 1

                if self._access_count > 3:
                    self._suspicious_activity_detected = True
                    if self.on_external_access:
                        self.on_external_access({
                            'access_count': self._access_count,
                            'timestamp': datetime.now().isoformat(),
                            'suspicious': True
                        })
                else:
                    if self.on_content_changed:
                        self.on_content_changed({
                            'timestamp': datetime.now().isoformat(),
                            'access_count': self._access_count
                        })

                self._last_content_hash = current_hash
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

    def is_suspicious_activity(self) -> bool:
        return self._suspicious_activity_detected

    def reset_suspicious_flag(self):
        self._suspicious_activity_detected = False
        self._access_count = 0

    def get_status(self) -> dict:
        return {
            'is_running': self.is_running,
            'suspicious_activity': self._suspicious_activity_detected,
            'access_count_since_reset': self._access_count
        }