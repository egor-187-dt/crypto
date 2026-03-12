# src/core/crypto/authentication.py
import time
import secrets
from datetime import datetime, timedelta
from src.core.events import events


class Authenticator:
    """Управляет аутентификацией и сессиями"""

    def __init__(self, key_derivation):
        self.kd = key_derivation
        self.failed_attempts = 0
        self.last_failed_time = 0
        self.session_start = None
        self.last_activity = None
        self.lockout_until = None

    def get_login_delay(self):
        """Экспоненциальная задержка при неудачных попытках"""
        if self.failed_attempts <= 1:
            return 0  # первая попытка без задержки
        elif self.failed_attempts == 2:
            return 1  # 1 секунда
        elif self.failed_attempts <= 4:
            return 5  # 5 секунд
        else:
            return 30  # 30 секунд

    def check_lockout(self):
        """Проверяет, не заблокирован ли вход"""
        if self.lockout_until:
            if datetime.now() < self.lockout_until:
                return True
            else:
                self.lockout_until = None
        return False

    def authenticate(self, password, stored_hash, salt=None):
        """
        Проверяет пароль и запускает сессию
        Возвращает (успех, ключ_шифрования)
        """
        # Проверяем блокировку
        if self.check_lockout():
            return False, None

        # Получаем задержку ДО проверки пароля
        delay = self.get_login_delay()

        # Вычисляем сколько времени прошло с последней попытки
        if self.last_failed_time > 0:
            elapsed = time.time() - self.last_failed_time
            if elapsed < delay:
                # Нужно подождать
                time.sleep(delay - elapsed)

        # Проверяем пароль
        try:
            if stored_hash.startswith('$argon2') and self.kd.verify_auth_hash(password, stored_hash):
                # Успешный вход
                self.failed_attempts = 0
                self.lockout_until = None

                enc_key = None
                if salt:
                    enc_key = self.kd.derive_encryption_key(password, salt)

                self.session_start = datetime.now()
                self.last_activity = datetime.now()

                events.publish("user_logged_in", {"time": self.session_start})
                return True, enc_key
        except:
            pass

        # Неудачная попытка
        self.failed_attempts += 1
        self.last_failed_time = time.time()

        # Блокировка при 5+ попытках
        if self.failed_attempts >= 5:
            self.lockout_until = datetime.now() + timedelta(seconds=30)

        events.publish("login_failed", {"attempts": self.failed_attempts})
        return False, None

    def update_activity(self):
        """Обновляет время последней активности"""
        self.last_activity = datetime.now()

    def is_session_expired(self, timeout_minutes=60):
        """Проверяет, истекла ли сессия по неактивности"""
        if not self.last_activity:
            return True

        inactive = datetime.now() - self.last_activity
        return inactive > timedelta(minutes=timeout_minutes)

    def logout(self):
        """Завершает сессию"""
        self.session_start = None
        self.last_activity = None
        events.publish("user_logged_out", {})