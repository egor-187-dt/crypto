import hashlib

class KeyManager:
    def __init__(self):
        self.current_key = None

    def derive_key(self, password: str, salt: bytes) -> bytes:
        # Заглушка для получения ключа из пароля
        # В спринте 2 сделаем нормально через PBKDF2
        combined = password.encode() + salt
        return hashlib.sha256(combined).digest()

    def store_key(self, key: bytes):
        # Пока просто храним в памяти
        self.current_key = key

    def load_key(self):
        return self.current_key

    def clear_key(self):
        self.current_key = None