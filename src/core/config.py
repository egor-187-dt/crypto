import os
import json

# Путь к папке с данными
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'vault.db')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

class Config:
    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        # Если файла нет, создаем пустой
        if not os.path.exists(CONFIG_FILE):
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR)
            self.data = {"db_path": DB_PATH, "theme": "default"}
            self.save()
        else:
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = {"db_path": DB_PATH}

    def save(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.data, f)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

# Глобальный конфиг
config = Config()