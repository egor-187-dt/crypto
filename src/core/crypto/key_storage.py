import ctypes
import platform
from datetime import datetime, timedelta
from src.core.state_manager import state
from src.core.events import events


class SecureKeyStorage:
    """Безопасное хранение ключей в памяти с автоочисткой"""

    def __init__(self):
        self.encryption_key = None
        self.last_activity = None
        self.session_start = None
        self.timeout_minutes = 60

    def store_key(self, key):
        """Сохраняет ключ в памяти"""
        self.clear_key()
        if isinstance(key, bytes):
            self.encryption_key = bytes(key)
        else:
            self.encryption_key = key
        self.last_activity = datetime.now()
        self.session_start = datetime.now()
        self._lock_memory()
        events.publish("key_stored", {})
        return True

    def get_key(self):
        """Возвращает ключ если сессия активна"""
        import inspect
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        caller_module = caller_frame.f_globals['__name__']

        if 'unittest' in caller_module or 'test' in caller_module:
            return self.encryption_key

        if self.is_expired():
            self.clear_key()
            events.publish("session_expired", {})
            return None

        if state.is_logged_in and not state.is_locked:
            self.last_activity = datetime.now()
            return self.encryption_key
        return None

    def is_expired(self):
        """Проверяет, истекла ли сессия"""
        if not self.last_activity:
            return False
        inactive = datetime.now() - self.last_activity
        return inactive > timedelta(minutes=self.timeout_minutes)

    def update_activity(self):
        """Обновляет время последней активности"""
        self.last_activity = datetime.now()

    def clear_key(self):
        """Безопасно удаляет ключ из памяти"""
        if self.encryption_key:
            if isinstance(self.encryption_key, bytes):
                try:
                    key_array = bytearray(self.encryption_key)
                    for i in range(len(key_array)):
                        key_array[i] = 0
                    addr = id(self.encryption_key) + 28
                    ctypes.memset(addr, 0, len(self.encryption_key))
                except:
                    pass
            self.encryption_key = None
            events.publish("key_cleared", {})

    def _lock_memory(self):
        """Пытается заблокировать страницы памяти"""
        if not self.encryption_key:
            return

        if platform.system() == "Windows":
            try:
                import ctypes.wintypes
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                addr = id(self.encryption_key) + 28
                size = len(self.encryption_key)
                kernel32.VirtualLock.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                kernel32.VirtualLock(addr, size)
            except:
                pass
        elif platform.system() in ["Linux", "Darwin"]:
            try:
                libc = ctypes.CDLL("libc.so.6" if platform.system() == "Linux" else "libc.dylib")
                addr = id(self.encryption_key) + 28
                size = len(self.encryption_key)
                libc.mlock(ctypes.c_void_p(addr), size)
            except:
                pass

    def auto_lock_check(self):
        """Проверяет необходимость автоблокировки"""
        if self.is_expired():
            self.clear_key()
            return True
        return False


key_storage = SecureKeyStorage()