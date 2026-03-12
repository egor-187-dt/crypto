import os
import secrets
from argon2 import PasswordHasher, Type
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class KeyDerivation:
    def __init__(self):
        # настройки аргона
        self.ph = PasswordHasher(
            time_cost=3,
            memory_cost=65536,  # 64 мб
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID
        )
        self.pbkdf2_iterations = 100000

    def create_auth_hash(self, password):
        # хеш для входа
        return self.ph.hash(password)

    def verify_auth_hash(self, password, stored_hash):
        # проверка пароля
        try:
            self.ph.verify(stored_hash, password)
            return True
        except:
            # защита от timing
            secrets.compare_digest(b'dummy', b'dummy')
            return False

    def create_salt(self):
        # рандомная соль
        return os.urandom(16)

    def derive_encryption_key(self, password, salt):
        # ключ для шифрования записей
        if isinstance(password, str):
            password = password.encode('utf-8')

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.pbkdf2_iterations,
            backend=default_backend()
        )
        return kdf.derive(password)