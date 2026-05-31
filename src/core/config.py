import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'vault.db')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')


class Config:
    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR)
            self.data = self._get_default_config()
            self.save()
        else:
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.data = json.load(f)
                defaults = self._get_default_config()
                for key, value in defaults.items():
                    if key not in self.data:
                        self.data[key] = value
            except Exception:
                self.data = self._get_default_config()

    def _get_default_config(self) -> dict:
        return {
            "db_path": DB_PATH,
            "theme": "default",
            "language": "ru",
            "argon2_time": 3,
            "argon2_memory": 65536,
            "argon2_parallelism": 4,
            "pbkdf2_iterations": 100000,
            "auto_lock_minutes": 60,
            "lock_on_focus_loss": False,
            "min_password_length": 12,
            "require_upper": True,
            "require_lower": True,
            "require_digits": True,
            "require_symbols": True,
            "clipboard_timeout_seconds": 30,
            "max_login_attempts": 5,
            "lockout_seconds": 30,
            "clipboard_timeout": 30,
            "clipboard_notifications": True,
            "clipboard_security_level": "basic",
            "clipboard_accelerate_on_access": False,
            "clipboard_preset": "standard"
        }

    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value
        self.save()

    def get_crypto_params(self) -> dict:
        return {
            'argon2_time': self.get('argon2_time', 3),
            'argon2_memory': self.get('argon2_memory', 65536),
            'argon2_parallelism': self.get('argon2_parallelism', 4),
            'pbkdf2_iterations': self.get('pbkdf2_iterations', 100000),
            'auto_lock_minutes': self.get('auto_lock_minutes', 60)
        }

    def set_crypto_params(self, **params):
        for key, value in params.items():
            if key in ['argon2_time', 'argon2_memory', 'argon2_parallelism', 'pbkdf2_iterations', 'auto_lock_minutes']:
                self.data[key] = value
        self.save()

    def get_password_policy(self) -> dict:
        return {
            'min_length': self.get('min_password_length', 12),
            'require_upper': self.get('require_upper', True),
            'require_lower': self.get('require_lower', True),
            'require_digits': self.get('require_digits', True),
            'require_symbols': self.get('require_symbols', True)
        }

    def get_clipboard_settings(self) -> dict:
        return {
            'clipboard_timeout': self.get('clipboard_timeout', 30),
            'clipboard_notifications': self.get('clipboard_notifications', True),
            'clipboard_security_level': self.get('clipboard_security_level', 'basic'),
            'clipboard_accelerate_on_access': self.get('clipboard_accelerate_on_access', False),
            'clipboard_preset': self.get('clipboard_preset', 'standard')
        }

    def set_clipboard_settings(self, **settings):
        for key, value in settings.items():
            if key in ['clipboard_timeout', 'clipboard_notifications',
                       'clipboard_security_level', 'clipboard_accelerate_on_access',
                       'clipboard_preset']:
                self.set(key, value)


config = Config()