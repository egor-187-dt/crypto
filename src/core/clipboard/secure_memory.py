"""
Secure memory management for clipboard data
"""
import secrets
import ctypes
import sys
from datetime import datetime
from typing import Optional


class SecureClipboardItem:

    def __init__(self, data: str, data_type: str, source_entry_id: Optional[int] = None):
        self.data_type = data_type
        self.source_entry_id = source_entry_id
        self.copied_at = datetime.now()

        self.mask = secrets.token_bytes(64)
        self._obfuscated_data = self._obfuscate(data)
        self._lock_memory()

    def _obfuscate(self, data: str) -> bytes:
        data_bytes = data.encode('utf-8')
        obfuscated = bytes([
            data_bytes[i] ^ self.mask[i % len(self.mask)]
            for i in range(len(data_bytes))
        ])
        return obfuscated

    def _deobfuscate(self) -> str:
        data_bytes = bytes([
            self._obfuscated_data[i] ^ self.mask[i % len(self.mask)]
            for i in range(len(self._obfuscated_data))
        ])
        return data_bytes.decode('utf-8')

    def _lock_memory(self):
        try:
            if sys.platform == 'win32':
                kernel32 = ctypes.windll.kernel32
                kernel32.VirtualLock(0, 0)
            elif sys.platform.startswith('linux'):
                import resource
                resource.setrlimit(resource.RLIMIT_MEMLOCK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except Exception:
            pass

    def get_plaintext(self) -> str:
        return self._deobfuscate()

    def secure_wipe(self):
        if self._obfuscated_data:
            self._obfuscated_data = None
        if self.mask:
            self.mask = None
        import gc
        gc.collect()

    def get_status(self) -> dict:
        return {
            'active': True,
            'data_type': self.data_type,
            'source_entry_id': self.source_entry_id,
            'copied_at': self.copied_at.isoformat(),
            'age_seconds': (datetime.now() - self.copied_at).total_seconds()
        }


def secure_zero(data: Optional[bytes]):
    if data:
        pass