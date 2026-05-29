import unittest
import sys
import os
import tempfile
import shutil
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.core.vault.encryption_service import AESGCMEncryption
from src.core.vault.password_generator import PasswordGenerator
from src.core.crypto.key_derivation import KeyDerivation
from src.core.key_manager import KeyManager
from src.database.db import Database
from src.core.config import config
from src.core.vault.entry_manager import EntryManager


class TestSprint3(unittest.TestCase):

    def setUp(self):
        self.kd = KeyDerivation()
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test.db")
        self._setup_test_db()

    def _setup_test_db(self):
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vault_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                deleted_at TIMESTAMP,
                version INTEGER DEFAULT 2
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

    def _setup_auth(self, db, km):
        password = "testpass123456"
        salt = self.kd.create_salt()
        auth_hash = self.kd.create_auth_hash(password)
        enc_key = self.kd.derive_encryption_key(password, salt)
        km.store_key(enc_key)

        db.execute("DELETE FROM master_password")
        db.execute("INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
                   (auth_hash, salt.hex()))
        return password

    def test_1_aes_gcm_encrypt_decrypt(self):
        """ENC-1, ENC-5: AES-GCM шифрование и расшифровка с проверкой тега"""
        key = self.kd.derive_encryption_key("testpass", self.kd.create_salt())
        aes = AESGCMEncryption(key)

        original = {"title": "Test", "password": "secret123", "version": 1}
        encrypted = aes.encrypt(original)
        decrypted = aes.decrypt(encrypted)

        self.assertEqual(original["title"], decrypted["title"])
        self.assertEqual(original["password"], decrypted["password"])

    def test_2_aes_gcm_unique_nonce(self):
        """ENC-2: Уникальный nonce для каждой записи"""
        key = self.kd.derive_encryption_key("testpass", self.kd.create_salt())
        aes = AESGCMEncryption(key)

        data = {"test": "data"}
        encrypted1 = aes.encrypt(data)
        encrypted2 = aes.encrypt(data)

        nonce1 = encrypted1[:12]
        nonce2 = encrypted2[:12]
        self.assertNotEqual(nonce1, nonce2)
        self.assertEqual(len(nonce1), 12)

    def test_3_password_generator_length(self):
        """GEN-2: Генерация паролей разной длины"""
        gen = PasswordGenerator()

        self.assertEqual(len(gen.generate(8)), 8)
        self.assertEqual(len(gen.generate(16)), 16)
        self.assertEqual(len(gen.generate(32)), 32)

    def test_4_password_generator_character_sets(self):
        """GEN-3: Минимум 1 символ из каждого выбранного набора"""
        gen = PasswordGenerator()

        pwd = gen.generate(10, use_upper=True, use_lower=False, use_digits=False, use_symbols=False)
        self.assertTrue(all(c.isupper() for c in pwd))

        pwd = gen.generate(10, use_upper=False, use_lower=True, use_digits=False, use_symbols=False)
        self.assertTrue(all(c.islower() for c in pwd))

        pwd = gen.generate(10, use_upper=False, use_lower=False, use_digits=True, use_symbols=False)
        self.assertTrue(all(c.isdigit() for c in pwd))

    def test_5_password_generator_history(self):
        """GEN-5: История паролей предотвращает повторы"""
        gen = PasswordGenerator()
        passwords = set()

        for _ in range(30):
            pwd = gen.generate(12)
            self.assertNotIn(pwd, passwords)
            passwords.add(pwd)

    def test_6_password_strength_check(self):
        """GEN-4: Проверка сложности пароля"""
        gen = PasswordGenerator()

        weak = gen.check_strength("123")
        self.assertEqual(weak['strength'], 'weak')

        medium = gen.check_strength("Password123")
        self.assertEqual(medium['strength'], 'medium')

        strong = gen.check_strength("P@ssw0rd123!@#")
        self.assertEqual(strong['strength'], 'strong')

    def test_7_crud_create_and_read(self):
        """CRUD-1: Создание и чтение записи"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        self._setup_auth(db, km)

        em = EntryManager(db, km)

        entry_id = em.create_entry({
            'title': 'Test Entry',
            'username': 'testuser',
            'password': 'secret123',
            'url': 'https://test.com',
            'notes': 'Test notes',
            'tags': ['test']
        })

        entry = em.get_entry(entry_id)
        self.assertEqual(entry['title'], 'Test Entry')
        self.assertEqual(entry['password'], 'secret123')

        db.close()
        config.set("db_path", old_path)

    def test_8_crud_update(self):
        """CRUD-1: Обновление записи"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        self._setup_auth(db, km)

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

        db.close()
        config.set("db_path", old_path)

    def test_9_crud_delete_soft(self):
        """CRUD-4: Мягкое удаление"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        self._setup_auth(db, km)

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

        em.delete_entry(entry_id, soft_delete=True)

        all_after = em.get_all_entries()
        self.assertEqual(len(all_after), 0)

        db.close()
        config.set("db_path", old_path)

    def test_10_search(self):
        """SEARCH-1: Поиск по записям"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        self._setup_auth(db, km)

        em = EntryManager(db, km)

        em.create_entry({'title': 'Google', 'username': 'user1@gmail.com', 'password': 'p1', 'url': 'https://google.com', 'notes': 'search', 'tags': []})
        em.create_entry({'title': 'GitHub', 'username': 'user2@gmail.com', 'password': 'p2', 'url': 'https://github.com', 'notes': 'code', 'tags': []})
        em.create_entry({'title': 'Facebook', 'username': 'user3@gmail.com', 'password': 'p3', 'url': 'https://facebook.com', 'notes': 'social', 'tags': []})

        results = em.search('Google')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Google')

        results = em.search('user2')
        self.assertEqual(len(results), 1)

        results = em.search('nonexistent')
        self.assertEqual(len(results), 0)

        db.close()
        config.set("db_path", old_path)

    def test_11_encrypted_data_in_db(self):
        """ENC-4: Данные хранятся как BLOB"""
        old_path = config.get("db_path")
        config.set("db_path", self.test_db)

        db = Database()
        db.db_path = self.test_db
        db.connect()

        km = KeyManager()
        self._setup_auth(db, km)

        em = EntryManager(db, km)

        entry_id = em.create_entry({
            'title': 'Secret Entry',
            'username': 'secretuser',
            'password': 'verysecret',
            'url': '',
            'notes': '',
            'tags': []
        })

        row = db.fetch_all("SELECT encrypted_data FROM vault_entries WHERE id = ?", (entry_id,))
        encrypted_blob = row[0][0]

        self.assertIsNotNone(encrypted_blob)
        self.assertIsInstance(encrypted_blob, bytes)
        self.assertGreater(len(encrypted_blob), 12)

        db.close()
        config.set("db_path", old_path)

    def test_12_decrypt_with_wrong_key_fails(self):
        """ENC-5: Неправильный ключ не может расшифровать"""
        key1 = self.kd.derive_encryption_key("correctpass", self.kd.create_salt())
        key2 = self.kd.derive_encryption_key("wrongpass", self.kd.create_salt())

        aes1 = AESGCMEncryption(key1)
        original = {"secret": "data"}
        encrypted = aes1.encrypt(original)

        aes2 = AESGCMEncryption(key2)
        with self.assertRaises(Exception):
            aes2.decrypt(encrypted)


if __name__ == '__main__':
    unittest.main()