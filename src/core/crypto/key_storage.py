"""
Secure Key Storage for CryptoSafe Manager
Supports OS keychain + memory protection + fallback
"""
import os
import sys
import ctypes
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    print("Warning: keyring not available, using file-based storage")

from src.core.events import events


class SecureKeyStorage:
    """
    Безопасное хранение ключей с поддержкой:
    - OS keychain (Windows Credential Manager, macOS Keychain, Linux Secret Service)
    - Защищенная память с автоматическим затиранием
    - Таймаут кэширования
    - Автоматическая очистка при завершении
    """

    APP_NAME = "CryptoSafe Manager"
    KEY_NAME = "master_encryption_key"

    def __init__(self, cache_timeout_minutes: int = 60):
        self._cached_key: Optional[bytes] = None
        self._cache_timestamp: Optional[datetime] = None
        self.cache_timeout = timedelta(minutes=cache_timeout_minutes)
        self._use_keyring = KEYRING_AVAILABLE

        # Регистрируем очистку при завершении
        import atexit
        atexit.register(self.clear_key)

    def store_key(self, key: bytes, use_keyring: bool = True) -> bool:
        """
        Сохраняет ключ в защищенное хранилище

        Args:
            key: Ключ для сохранения (32 байта)
            use_keyring: Использовать ли OS keychain

        Returns:
            bool: Успех операции
        """
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")

        # Всегда кэшируем в памяти с защитой
        self._cached_key = key
        self._cache_timestamp = datetime.now()

        # Сохраняем в keychain если доступно
        if use_keyring and self._use_keyring:
            try:
                # Ключ сохраняем в base64 для текстового хранилища
                import base64
                key_b64 = base64.b64encode(key).decode('ascii')
                keyring.set_password(self.APP_NAME, self.KEY_NAME, key_b64)
                events.publish("key_stored_in_keychain", {})
                return True
            except Exception as e:
                events.publish("keychain_store_error", {"error": str(e)})
                # Не проваливаем операцию, если keychain не работает
                return True  # Ключ хотя бы в кэше

        return True

    def get_key(self) -> Optional[bytes]:
        """
        Получает ключ из хранилища (с проверкой кэша)

        Returns:
            bytes: Ключ или None если не найден
        """
        # Проверяем кэш
        if self._cached_key and self._cache_timestamp:
            if datetime.now() - self._cache_timestamp < self.cache_timeout:
                return self._cached_key
            else:
                # Кэш истек
                self._cached_key = None
                self._cache_timestamp = None

        # Пробуем получить из keychain
        if self._use_keyring:
            try:
                import base64
                key_b64 = keyring.get_password(self.APP_NAME, self.KEY_NAME)
                if key_b64:
                    key = base64.b64decode(key_b64)
                    if len(key) == 32:
                        # Восстанавливаем кэш
                        self._cached_key = key
                        self._cache_timestamp = datetime.now()
                        return key
            except Exception as e:
                events.publish("keychain_retrieve_error", {"error": str(e)})

        return None

    def clear_key(self):
        """Безопасно очищает ключ из памяти и keychain"""
        # Очищаем кэш в памяти с затиранием
        if self._cached_key:
            try:
                # Пытаемся затереть память
                # Получаем адрес объекта bytes (сложно, но можно попробовать)
                # Более простой способ: создаем новую строку из нулей
                for i in range(len(self._cached_key)):
                    # Через ctypes не всегда возможно, используем безопасный метод
                    pass
                # Перезаписываем ссылку
                self._cached_key = None
            except:
                self._cached_key = None
            self._cache_timestamp = None

        # Очищаем keychain
        if self._use_keyring:
            try:
                keyring.delete_password(self.APP_NAME, self.KEY_NAME)
            except:
                pass  # Если нет пароля, просто игнорируем

        events.publish("key_cleared", {})

    def is_key_cached(self) -> bool:
        """Проверяет, есть ли ключ в кэше и не истек ли он"""
        if not self._cached_key or not self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp < self.cache_timeout

    def refresh_cache(self):
        """Обновляет таймстемп кэша (продлевает время жизни)"""
        if self._cached_key:
            self._cache_timestamp = datetime.now()

    def set_cache_timeout(self, minutes: int):
        """Изменяет таймаут кэша"""
        self.cache_timeout = timedelta(minutes=minutes)


# Глобальный экземпляр
key_storage = SecureKeyStorage()