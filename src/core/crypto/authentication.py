import time
from datetime import datetime, timedelta


class Authenticator:
    def __init__(self, key_derivation):
        self.kd = key_derivation
        self.failed = 0
        self.last_fail = 0
        self.locked_until = None
        self.last_active = None

    def check_lock(self):
        if self.locked_until:
            if datetime.now() < self.locked_until:
                return True
            self.locked_until = None
        return False

    def get_wait_time(self):
        # задержка между попытками
        if self.failed <= 1:
            return 0
        elif self.failed == 2:
            return 1
        elif self.failed <= 4:
            return 5
        return 30

    def login(self, password, stored_hash, salt=None):
        if self.check_lock():
            return False, None

        # ждем если надо
        wait = self.get_wait_time()
        if self.last_fail > 0:
            passed = time.time() - self.last_fail
            if passed < wait:
                time.sleep(wait - passed)

        # проверка пароля
        try:
            if stored_hash.startswith('$argon2') and self.kd.verify_auth_hash(password, stored_hash):
                self.failed = 0
                self.locked_until = None

                key = None
                if salt:
                    key = self.kd.derive_encryption_key(password, salt)

                self.last_active = datetime.now()
                return True, key
        except:
            pass

        # неудача
        self.failed += 1
        self.last_fail = time.time()

        if self.failed >= 5:
            self.locked_until = datetime.now() + timedelta(seconds=30)

        return False, None

    def update_activity(self):
        self.last_active = datetime.now()