import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.database.db import db
from src.core.key_manager import KeyManager
from src.core.crypto.key_derivation import KeyDerivation
from src.core.vault.entry_manager import EntryManager

# Подключаем БД
db.db_path = "data/vault.db"
db.connect()

# Получаем ключ
kd = KeyDerivation()
km = KeyManager()

# Проверяем мастер-пароль
result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
if not result:
    print("Нет мастер-пароля!")
    sys.exit(1)

saved_hash, salt_value = result[0]
print(f"Hash: {saved_hash[:50]}...")
print(f"Salt: {salt_value}")

# Введи свой мастер-пароль
pwd = input("Введите мастер-пароль: ")

# Проверяем Argon2
from src.core.crypto.authentication import Authenticator

auth = Authenticator(kd)
try:
    salt = bytes.fromhex(salt_value)
    success, enc_key = auth.login(pwd, saved_hash, salt)
    if success and enc_key:
        km.store_key(enc_key)
        print("Ключ получен!")
    else:
        print("Неверный пароль!")
        sys.exit(1)
except Exception as e:
    print(f"Ошибка: {e}")
    sys.exit(1)

# Создаем запись
em = EntryManager(db, km)
try:
    entry_id = em.create_entry({
        'title': 'Тест',
        'username': 'testuser',
        'password': 'testpass123',
        'url': 'https://test.com',
        'notes': 'Тестовая запись',
        'tags': ['test']
    })
    print(f"Запись создана! ID: {entry_id}")

    # Проверяем что прочиталось
    entry = em.get_entry(entry_id)
    print(f"Прочитано: {entry}")

except Exception as e:
    print(f"ОШИБКА: {e}")
    import traceback

    traceback.print_exc()

db.close()