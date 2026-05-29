import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from src.database.db import db
from src.core.key_manager import KeyManager
from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.authentication import Authenticator
from src.core.vault.encryption_service import AESGCMEncryption

# 1. Проверяем БД
print("=" * 50)
print("1. ПРОВЕРКА БД")
print("=" * 50)

db.db_path = "data/vault.db"
db.connect()

# Проверяем есть ли мастер-пароль
result = db.fetch_all("SELECT COUNT(*) FROM master_password")
has_master = result and result[0][0] > 0
print(f"Есть мастер-пароль: {has_master}")

if not has_master:
    print("НЕТ МАСТЕР-ПАРОЛЯ! Запусти main.py и создай мастер-пароль сначала")
    sys.exit(1)

# Получаем мастер-пароль
result = db.fetch_all("SELECT password_hash, salt FROM master_password LIMIT 1")
stored_hash, salt_hex = result[0]
salt = bytes.fromhex(salt_hex)
print(f"SALT: {salt_hex[:32]}...")

# 2. Проверяем авторизацию
print("\n" + "=" * 50)
print("2. ПРОВЕРКА АВТОРИЗАЦИИ")
print("=" * 50)

kd = KeyDerivation()
auth = Authenticator(kd)
km = KeyManager()

password = input("Введите мастер-пароль: ")

success, enc_key = auth.login(password, stored_hash, salt)
if not success:
    print("НЕВЕРНЫЙ ПАРОЛЬ!")
    sys.exit(1)

km.store_key(enc_key)
print("Авторизация успешна, ключ получен")

# 3. Проверяем AES-GCM
print("\n" + "=" * 50)
print("3. ПРОВЕРКА AES-Gcm")
print("=" * 50)

aes = AESGCMEncryption(enc_key)
test_data = {"test": "data", "number": 123}
print(f"Исходные данные: {test_data}")

encrypted = aes.encrypt(test_data)
print(f"Зашифровано: тип={type(encrypted)}, длина={len(encrypted)}")

decrypted = aes.decrypt(encrypted)
print(f"Расшифровано: {decrypted}")

# 4. Проверяем вставку в БД напрямую
print("\n" + "=" * 50)
print("4. ПРЯМАЯ ВСТАВКА В БД")
print("=" * 50)

now = "2024-01-01T12:00:00"
payload = {
    'title': 'Тестовая запись',
    'username': 'testuser',
    'password': 'testpass123',
    'url': '',
    'notes': '',
    'category': '',
    'tags': [],
    'version': 2,
    'created_at': now,
    'updated_at': now
}

encrypted_blob = aes.encrypt(payload)
print(f"encrypted_blob тип: {type(encrypted_blob)}")
print(f"encrypted_blob это bytes? {isinstance(encrypted_blob, bytes)}")

tags_str = ''

try:
    cursor = db.conn.cursor()
    cursor.execute(
        """INSERT INTO vault_entries 
           (encrypted_data, title, username, url, notes, tags, created_at, updated_at, deleted) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (encrypted_blob, payload['title'], payload['username'],
         payload['url'], payload['notes'], tags_str, now, now, 0)
    )
    db.conn.commit()
    entry_id = cursor.lastrowid
    print(f"✅ Прямая вставка успешна! ID: {entry_id}")

    # Проверяем что прочиталось
    cursor.execute("SELECT encrypted_data FROM vault_entries WHERE id = ?", (entry_id,))
    row = cursor.fetchone()
    read_blob = row[0]
    print(f"Прочитанный blob тип: {type(read_blob)}")

    decrypted_data = aes.decrypt(read_blob)
    print(f"Расшифрованные данные: {decrypted_data}")

    # Удаляем тестовую запись
    cursor.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))
    db.conn.commit()
    print("✅ Тестовая запись удалена")

except Exception as e:
    print(f"❌ ОШИБКА прямой вставки: {e}")
    import traceback

    traceback.print_exc()

# 5. Проверяем EntryManager
print("\n" + "=" * 50)
print("5. ПРОВЕРКА EntryManager")
print("=" * 50)

from src.core.vault.entry_manager import EntryManager

em = EntryManager(db, km)

try:
    print("Пробуем создать запись через EntryManager...")
    entry_id = em.create_entry({
        'title': 'Тест через EntryManager',
        'username': 'testuser',
        'password': 'testpass123',
        'url': '',
        'notes': '',
        'category': '',
        'tags': []
    })
    print(f"✅ EntryManager создал запись! ID: {entry_id}")

    # Проверяем чтение
    entry = em.get_entry(entry_id)
    print(f"Прочитано: {entry}")

    # Удаляем
    em.delete_entry(entry_id)
    print("✅ Запись удалена")

except Exception as e:
    print(f"❌ ОШИБКА EntryManager: {e}")
    import traceback

    traceback.print_exc()

db.close()
print("\n" + "=" * 50)
print("ДИАГНОСТИКА ЗАВЕРШЕНА")
print("=" * 50)