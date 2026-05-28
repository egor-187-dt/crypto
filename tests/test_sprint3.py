import unittest
import sys
import os
import tempfile
import shutil
import sqlite3
import base64
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.core.crypto.aes_gcm import AESGCMEncryption
from src.core.vault.password_generator import PasswordGenerator
from src.core.crypto.key_derivation import KeyDerivation
from src.core.key_manager import KeyManager
from src.database.db import Database
from src.core.config import config
from src.core.vault.entry_manager import EntryManager


class TestSprint3(unittest.TestCase):
    """Тесты для проверки спринта 3"""

    def setUp(self):
        self.kd = KeyDerivation()
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test.db")
        self._setup_test_db()

    def _setup_test_db(self):
        """Создает временную БД с правильной структурой"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vault_entries (
                id TEXT PRIMARY KEY,
                title TEXT,
                username TEXT,
                encrypted_password TEXT,
                encrypted_data BLOB,
                url TEXT,
                notes TEXT,
                tags TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_password (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_aes_gcm_encrypt_decrypt(self):
        """ТЕСТ-1: AES-GCM шифрование и расшифровка"""
        key = self.kd.derive_encryption_key("testpass", self.kd.create_salt())
        aes = AESGCMEncryption(key)

        original = {"title": "Test", "password": "secret123", "version": 2}

        encrypted = aes.encrypt(original)
        decrypted = aes.decrypt(encrypted)

        self.assertEqual(original["title"], decrypted["title"])
        self.assertEqual(original["password"], decrypted["password"])
        self.assertEqual(original["version"], decrypted["version"])
        print("AES-GCM шифрование/расшифровка работает")

    def test_aes_gcm_unique_nonce(self):
        """Уникальный nonce для каждой записи"""
        key = self.kd.derive_encryption_key("testpass", self.kd.create_salt())
        aes = AESGCMEncryption(key)

        data = {"test": "data"}
        encrypted1 = aes.encrypt(data)
        encrypted2 = aes.encrypt(data)

        # Первые 12 байт - nonce, они должны быть разными
        nonce1 = encrypted1[:12]
        nonce2 = encrypted2[:12]

        self.assertNotEqual(nonce1, nonce2)
        self.assertEqual(len(nonce1), 12)
        print("Уникальный nonce для каждой записи")

    def test_password_generator_length(self):
        """Генератор паролей - длина"""
        gen = PasswordGenerator()

        pwd8 = gen.generate(8)
        pwd16 = gen.generate(16)
        pwd32 = gen.generate(32)

        self.assertEqual(len(pwd8), 8)
        self.assertEqual(len(pwd16), 16)
        self.assertEqual(len(pwd32), 32)
        print("Генератор паролей - длина работает")

    def test_password_generator_sets(self):
        """ТЕСТ-4: Генератор паролей - наборы символов"""
        gen = PasswordGenerator()

        # Только цифры
        pwd = gen.generate(10, use_upper=False, use_lower=False, use_digits=True, use_symbols=False)
        self.assertTrue(all(c.isdigit() for c in pwd))

        # Только буквы
        pwd = gen.generate(10, use_upper=True, use_lower=True, use_digits=False, use_symbols=False)
        self.assertTrue(all(c.isalpha() for c in pwd))

        # С заглавными
        pwd = gen.generate(10, use_upper=True, use_lower=False, use_digits=False, use_symbols=False)
        self.assertTrue(all(c.isupper() for c in pwd))

        print("Генератор паролей - наборы символов работают")

    def test_password_generator_no_ambiguous(self):
        """ТЕСТ-5: Генератор паролей - исключение неоднозначных символов"""
        gen = PasswordGenerator()
        ambiguous = 'lI1O0'

        pwd = gen.generate(50, exclude_ambiguous=True)
        for c in ambiguous:
            self.assertNotIn(c, pwd)
        print("Генератор паролей - исключение неоднозначных символов")

    def test_password_strength_check(self):
        """ТЕСТ-6: Проверка сложности пароля"""
        gen = PasswordGenerator()

        weak = gen.check_strength("123")
        self.assertEqual(weak['strength'], 'weak')

        medium = gen.check_strength("Password123")
        self.assertEqual(medium['strength'], 'medium')

        strong = gen.check_strength("P@ssw0rd123!@#")
        self.assertEqual(strong['strength'], 'strong')

        print("Проверка сложности пароля работает")

    def test_crud_create_and_read(self):
        """ТЕСТ-7: CRUD - создание и чтение записи"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        password = "testpass123456"
        salt = self.kd.create_salt()
        auth_hash = self.kd.create_auth_hash(password)
        enc_key = self.kd.derive_encryption_key(password, salt)
        km.store_key(enc_key)

        db.execute("DELETE FROM master_password")
        db.execute("INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
                   (auth_hash, salt.hex()))

        em = EntryManager(db, km)

        entry_id = em.create_entry({
            'title': 'Test Entry',
            'username': 'testuser',
            'password': 'secret123',
            'url': 'https://test.com',
            'notes': 'Test notes',
            'tags': ['test', 'demo']
        })

        entry = em.get_entry(entry_id)
        self.assertEqual(entry['title'], 'Test Entry')
        self.assertEqual(entry['username'], 'testuser')
        self.assertEqual(entry['password'], 'secret123')
        self.assertEqual(entry['url'], 'https://test.com')

        db.close()
        config.set("db_path", old_path)

        print("CRUD - создание и чтение работает")

    def test_crud_update(self):
        """ТЕСТ-8: CRUD - обновление записи"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        password = "testpass123456"
        salt = self.kd.create_salt()
        auth_hash = self.kd.create_auth_hash(password)
        enc_key = self.kd.derive_encryption_key(password, salt)
        km.store_key(enc_key)

        db.execute("DELETE FROM master_password")
        db.execute("INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
                   (auth_hash, salt.hex()))

        em = EntryManager(db, km)

        entry_id = em.create_entry({
            'title': 'Old Title',
            'username': 'olduser',
            'password': 'oldpass',
            'url': '',
            'notes': '',
            'tags': []
        })

        updated = em.update_entry(entry_id, {
            'title': 'New Title',
            'password': 'newpass'
        })

        self.assertEqual(updated['title'], 'New Title')
        self.assertEqual(updated['password'], 'newpass')
        self.assertEqual(updated['username'], 'olduser')

        db.close()
        config.set("db_path", old_path)

        print("CRUD - обновление работает")

    def test_crud_delete(self):
        """ТЕСТ-9: CRUD - удаление записи"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        password = "testpass123456"
        salt = self.kd.create_salt()
        auth_hash = self.kd.create_auth_hash(password)
        enc_key = self.kd.derive_encryption_key(password, salt)
        km.store_key(enc_key)

        db.execute("DELETE FROM master_password")
        db.execute("INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
                   (auth_hash, salt.hex()))

        em = EntryManager(db, km)

        entry_id = em.create_entry({
            'title': 'To Delete',
            'username': 'user',
            'password': 'pass',
            'url': '',
            'notes': '',
            'tags': []
        })

        all_before = em.get_all_entries()
        self.assertEqual(len(all_before), 1)

        em.delete_entry(entry_id)

        all_after = em.get_all_entries()
        self.assertEqual(len(all_after), 0)

        db.close()
        config.set("db_path", old_path)

        print("CRUD - удаление работает")

    def test_search(self):
        """ТЕСТ-10: Поиск по записям"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        password = "testpass123456"
        salt = self.kd.create_salt()
        auth_hash = self.kd.create_auth_hash(password)
        enc_key = self.kd.derive_encryption_key(password, salt)
        km.store_key(enc_key)

        db.execute("DELETE FROM master_password")
        db.execute("INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
                   (auth_hash, salt.hex()))

        em = EntryManager(db, km)

        em.create_entry(
            {'title': 'Google', 'username': 'user1@gmail.com', 'password': 'p1', 'url': '', 'notes': '', 'tags': []})
        em.create_entry(
            {'title': 'GitHub', 'username': 'user2@gmail.com', 'password': 'p2', 'url': '', 'notes': '', 'tags': []})
        em.create_entry(
            {'title': 'Facebook', 'username': 'user3@gmail.com', 'password': 'p3', 'url': '', 'notes': '', 'tags': []})

        results = em.search('Google')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Google')

        results = em.search('user2')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['username'], 'user2@gmail.com')

        results = em.search('nonexistent')
        self.assertEqual(len(results), 0)

        db.close()
        config.set("db_path", old_path)

        print("Поиск работает")

    def test_encrypted_data_in_db(self):
        """ТЕСТ-11: Проверка что данные в БД зашифрованы"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        password = "testpass123456"
        salt = self.kd.create_salt()
        auth_hash = self.kd.create_auth_hash(password)
        enc_key = self.kd.derive_encryption_key(password, salt)
        km.store_key(enc_key)

        db.execute("DELETE FROM master_password")
        db.execute("INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
                   (auth_hash, salt.hex()))

        em = EntryManager(db, km)

        entry_id = em.create_entry({
            'title': 'Secret Entry',
            'username': 'secretuser',
            'password': 'verysecret',
            'url': '',
            'notes': '',
            'tags': []
        })

        # Проверяем что encrypted_data заполнен и это BLOB
        row = db.fetch_all("SELECT encrypted_data FROM vault_entries WHERE id = ?", (entry_id,))
        encrypted_blob = row[0][0]

        self.assertIsNotNone(encrypted_blob)
        self.assertIsInstance(encrypted_blob, bytes)
        self.assertGreater(len(encrypted_blob), 12)  # nonce + ciphertext

        # Проверяем что это не base64 строка
        try:
            base64.b64decode(encrypted_blob)
            is_base64 = True
        except:
            is_base64 = False

        self.assertFalse(is_base64, "Данные в BLOB")

        db.close()
        config.set("db_path", old_path)

        print("Данные в БД зашифрованы (BLOB)")


if __name__ == '__main__':
    unittest.main()