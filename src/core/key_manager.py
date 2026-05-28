import hashlib
import ctypes
import base64
from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.key_storage import key_storage


class KeyManager:
    def __init__(self):
        self.kd = KeyDerivation()
        self.current_key = None

    def derive_key(self, password, salt):
        if isinstance(salt, str):
            salt = salt.encode()
        if isinstance(password, str):
            password = password.encode()
        return self.kd.derive_encryption_key(password, salt)

    def store_key(self, key):
        self.current_key = key
        key_storage.store_key(key)

    def load_key(self):
        stored = key_storage.get_key()
        if stored:
            self.current_key = stored
            return stored
        return self.current_key

    def decrypt_text(self, encrypted_text):
        if not encrypted_text:
            return b""
        return base64.b64decode(encrypted_text)

    def clear_key(self):
        if self.current_key:
            try:
                addr = id(self.current_key) + 28
                ctypes.memset(addr, 0, len(self.current_key))
            except:
                pass
            self.current_key = None

        key_storage.clear_key()

    def is_key_available(self):
        return self.load_key() is not None