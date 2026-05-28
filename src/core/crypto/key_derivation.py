"""
Key Derivation Service for CryptoSafe Manager
Argon2id for password hashing + PBKDF2 for encryption key derivation
"""
import os
import secrets
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHash
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


@dataclass
class Argon2Params:
    """Параметры Argon2id с валидацией"""
    time_cost: int = 3
    memory_cost: int = 65536  # 64 MiB
    parallelism: int = 4
    hash_len: int = 32
    salt_len: int = 16

    def __post_init__(self):
        """Валидация параметров для защиты от DoS"""
        if self.time_cost < 1 or self.time_cost > 20:
            raise ValueError("time_cost must be between 1 and 20")
        if self.memory_cost < 8192 or self.memory_cost > 1048576:  # Max 1 GiB
            raise ValueError("memory_cost must be between 8 KiB and 1 GiB")
        if self.parallelism < 1 or self.parallelism > 16:
            raise ValueError("parallelism must be between 1 and 16")
        if self.hash_len < 16 or self.hash_len > 64:
            raise ValueError("hash_len must be between 16 and 64")

    def to_dict(self) -> Dict:
        return {
            'time_cost': self.time_cost,
            'memory_cost': self.memory_cost,
            'parallelism': self.parallelism,
            'hash_len': self.hash_len,
            'salt_len': self.salt_len
        }


class KeyDerivation:
    """
    Управляет выводом ключей:
    - Argon2id для хэширования пароля (аутентификация)
    - PBKDF2-HMAC-SHA256 для получения ключа шифрования
    """

    def __init__(self, params: Optional[Argon2Params] = None):
        self.params = params or Argon2Params()
        self.pbkdf2_iterations = 100000  # Рекомендованное NIST значение

        # Инициализируем Argon2 с параметрами
        self._argon2 = PasswordHasher(
            time_cost=self.params.time_cost,
            memory_cost=self.params.memory_cost,
            parallelism=self.params.parallelism,
            hash_len=self.params.hash_len,
            salt_len=self.params.salt_len,
            type=Type.ID
        )

    def create_auth_hash(self, password: str) -> str:
        """
        Создает Argon2id хэш для аутентификации

        Args:
            password: Пароль пользователя

        Returns:
            str: Argon2id хэш в формате $argon2id$...
        """
        if not password or len(password) < 8:
            raise ValueError("Password too short")

        return self._argon2.hash(password)

    def verify_auth_hash(self, password: str, stored_hash: str) -> bool:
        """
        Проверяет пароль против Argon2id хэша (constant-time)

        Args:
            password: Проверяемый пароль
            stored_hash: Сохраненный хэш

        Returns:
            bool: True если пароль верный
        """
        try:
            self._argon2.verify(stored_hash, password)
            return True
        except (VerificationError, InvalidHash):
            # Constant-time dummy verification
            secrets.compare_digest(b'dummy', b'dummy')
            return False

    def create_salt(self) -> bytes:
        """
        Создает криптографически безопасную соль

        Returns:
            bytes: 16 байт случайных данных
        """
        return os.urandom(self.params.salt_len)

    def derive_encryption_key(self, password: str, salt: bytes) -> bytes:
        """
        Выводит ключ шифрования AES-256 из пароля с помощью PBKDF2

        Args:
            password: Пароль пользователя
            salt: Соль (16 байт)

        Returns:
            bytes: 32-байтный ключ для AES-256
        """
        if not password:
            raise ValueError("Password cannot be empty")
        if not salt or len(salt) != self.params.salt_len:
            raise ValueError(f"Salt must be {self.params.salt_len} bytes")

        if isinstance(password, str):
            password = password.encode('utf-8')

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256 key length
            salt=salt,
            iterations=self.pbkdf2_iterations,
            backend=default_backend()
        )
        return kdf.derive(password)

    def needs_rehash(self, stored_hash: str) -> bool:
        """
        Проверяет, нужно ли обновить хэш (при изменении параметров)

        Args:
            stored_hash: Сохраненный хэш

        Returns:
            bool: True если хэш нужно пересоздать
        """
        try:
            return self._argon2.check_needs_rehash(stored_hash)
        except:
            return True

    def get_current_params(self) -> Dict:
        """Возвращает текущие параметры для сохранения"""
        return self.params.to_dict()

    def update_params(self, new_params: Argon2Params):
        """
        Обновляет параметры Argon2 (для будущих хэшей)

        Args:
            new_params: Новые параметры
        """
        self.params = new_params
        self._argon2 = PasswordHasher(
            time_cost=self.params.time_cost,
            memory_cost=self.params.memory_cost,
            parallelism=self.params.parallelism,
            hash_len=self.params.hash_len,
            salt_len=self.params.salt_len,
            type=Type.ID
        )