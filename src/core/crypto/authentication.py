"""
Authentication Service for CryptoSafe Manager
Manages login, session tracking, and brute-force protection
"""
import time
from datetime import datetime, timedelta
from typing import Tuple, Optional

from src.core.events import events
from src.core.crypto.key_derivation import KeyDerivation


class Authenticator:
    """
    Управляет аутентификацией пользователя:
    - Проверка пароля
    - Защита от brute-force (экспоненциальные задержки)
    - Отслеживание сессии и неактивности
    - Блокировка при превышении попыток
    """

    # Константы для защиты
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 30  # секунд
    SESSION_TIMEOUT_MINUTES = 60  # 1 час

    def __init__(self, key_derivation: KeyDerivation):
        self.kd = key_derivation
        self.failed_attempts = 0
        self.last_fail_time = 0
        self.locked_until: Optional[datetime] = None
        self.session_start: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None

    def _get_delay(self) -> int:
        """
        Вычисляет задержку перед следующей попыткой
        Экспоненциальная стратегия:
        - 0-1 попытка: 0 сек
        - 2 попытка: 1 сек
        - 3-4 попытка: 5 сек
        - 5+ попыток: 30 сек (но потом блокировка)
        """
        if self.failed_attempts <= 1:
            return 0
        elif self.failed_attempts == 2:
            return 1
        elif self.failed_attempts <= 4:
            return 5
        else:
            return 30

    def _check_lockout(self) -> bool:
        """
        Проверяет, не заблокирован ли аккаунт

        Returns:
            bool: True если аккаунт заблокирован
        """
        if self.locked_until:
            if datetime.now() < self.locked_until:
                return True
            else:
                # Блокировка истекла
                self.locked_until = None
        return False

    def login(self, password: str, stored_hash: str, salt: Optional[bytes] = None) -> Tuple[bool, Optional[bytes]]:
        """
        Выполняет вход пользователя

        Args:
            password: Введенный пароль
            stored_hash: Сохраненный Argon2 хэш
            salt: Соль для получения ключа шифрования

        Returns:
            Tuple[bool, Optional[bytes]]: (успех, ключ_шифрования)
        """
        # 1. Проверка блокировки
        if self._check_lockout():
            events.publish("login_blocked", {
                "locked_until": self.locked_until.isoformat() if self.locked_until else None
            })
            return False, None

        # 2. Вычисляем необходимую задержку
        delay = self._get_delay()

        # 3. Применяем задержку ДО проверки пароля (защита от brute-force)
        if self.last_fail_time > 0 and delay > 0:
            elapsed = time.time() - self.last_fail_time
            if elapsed < delay:
                wait_time = delay - elapsed
                events.publish("login_delay", {"seconds": wait_time})
                time.sleep(wait_time)

        # 4. Проверяем пароль
        success = False
        enc_key = None

        try:
            if self.kd.verify_auth_hash(password, stored_hash):
                success = True
                if salt:
                    enc_key = self.kd.derive_encryption_key(password, salt)
        except Exception as e:
            events.publish("login_error", {"error": str(e)})

        # 5. Обработка результата
        if success:
            # Успешный вход - сбрасываем счетчик
            self.failed_attempts = 0
            self.last_fail_time = 0
            self.locked_until = None
            self.session_start = datetime.now()
            self.last_activity = datetime.now()

            events.publish("user_logged_in", {
                "time": self.session_start.isoformat()
            })
            return True, enc_key
        else:
            # Неудачная попытка - увеличиваем счетчик
            self.failed_attempts += 1
            self.last_fail_time = time.time()

            events.publish("login_failed", {
                "attempts": self.failed_attempts,
                "next_delay": self._get_delay()
            })

            # Блокировка при превышении попыток
            if self.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                self.locked_until = datetime.now() + timedelta(seconds=self.LOCKOUT_DURATION)
                events.publish("account_locked", {
                    "locked_until": self.locked_until.isoformat()
                })

            return False, None

    def update_activity(self):
        """Обновляет время последней активности пользователя"""
        self.last_activity = datetime.now()
        events.publish("activity_updated", {"last_activity": self.last_activity.isoformat()})

    def is_session_expired(self, timeout_minutes: Optional[int] = None) -> bool:
        """
        Проверяет, истекла ли сессия по неактивности

        Args:
            timeout_minutes: Таймаут в минутах (если None - используем стандартный)

        Returns:
            bool: True если сессия истекла
        """
        if not self.last_activity:
            return True

        timeout = timeout_minutes or self.SESSION_TIMEOUT_MINUTES
        inactive = datetime.now() - self.last_activity
        expired = inactive > timedelta(minutes=timeout)

        if expired:
            events.publish("session_expired", {
                "inactive_minutes": inactive.total_seconds() / 60,
                "timeout_minutes": timeout
            })

        return expired

    def logout(self):
        """Завершает сессию пользователя"""
        self.session_start = None
        self.last_activity = None
        self.failed_attempts = 0
        self.last_fail_time = 0
        self.locked_until = None

        events.publish("user_logged_out", {})

    def get_session_duration(self) -> float:
        """
        Возвращает длительность текущей сессии в секундах

        Returns:
            float: Длительность сессии или 0 если нет активной сессии
        """
        if not self.session_start:
            return 0
        return (datetime.now() - self.session_start).total_seconds()

    def reset(self):
        """Полностью сбрасывает состояние аутентификатора"""
        self.failed_attempts = 0
        self.last_fail_time = 0
        self.locked_until = None
        self.last_activity = None
        self.session_start = None

    def get_status(self) -> dict:
        """
        Возвращает текущий статус аутентификатора

        Returns:
            dict: Статус с информацией о попытках и блокировке
        """
        return {
            'failed_attempts': self.failed_attempts,
            'is_locked': self.locked_until is not None and datetime.now() < self.locked_until,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'session_active': self.session_start is not None,
            'session_duration': self.get_session_duration()
        }