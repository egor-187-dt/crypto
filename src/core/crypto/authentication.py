import time
from datetime import datetime, timedelta


class Authenticator:
    """Управляет аутентификацией и сессиями"""

    def __init__(self, key_derivation):
        self.kd = key_derivation
        self.failed_attempts = 0
        self.last_fail_time = 0
        self.locked_until = None
        self.last_activity = None

    def _get_delay(self):
        """Экспоненциальная задержка при неудачных попытках"""
        if self.failed_attempts <= 1:
            return 0
        elif self.failed_attempts == 2:
            return 1
        elif self.failed_attempts <= 4:
            return 5
        else:
            return 30

    def login(self, password, stored_hash, salt=None):
        """
        Проверяет пароль и запускает сессию
        Возвращает (успех, ключ_шифрования)
        """
        # Проверка блокировки
        if self.locked_until and datetime.now() < self.locked_until:
            return False, None

        # Получаем задержку
        delay = self._get_delay()

        # Ждем если нужно
        if self.last_fail_time > 0:
            elapsed = time.time() - self.last_fail_time
            if elapsed < delay:
                time.sleep(delay - elapsed)

        # Проверяем пароль
        success = False
        enc_key = None

        try:
            if stored_hash.startswith('$argon2') and self.kd.verify_auth_hash(password, stored_hash):
                success = True
                if salt:
                    enc_key = self.kd.derive_encryption_key(password, salt)
        except Exception as e:
            print(f"Auth error: {e}")

        if success:
            # Успешный вход
            self.failed_attempts = 0
            self.last_fail_time = 0
            self.locked_until = None
            self.last_activity = datetime.now()
            return True, enc_key
        else:
            # Неудачная попытка
            self.failed_attempts += 1
            self.last_fail_time = time.time()

            # Блокировка при 5+ попытках
            if self.failed_attempts >= 5:
                self.locked_until = datetime.now() + timedelta(seconds=30)

            return False, None

    def update_activity(self):
        """Обновляет время последней активности"""
        self.last_activity = datetime.now()

    def logout(self):
        """Завершает сессию"""
        self.failed_attempts = 0
        self.last_fail_time = 0
        self.locked_until = None
        self.last_activity = None