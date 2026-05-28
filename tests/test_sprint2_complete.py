import unittest
import time
import os
import tempfile
import shutil
import sqlite3
import gc
from datetime import datetime, timedelta

from src.core.crypto.key_derivation import KeyDerivation, Argon2Params
from src.core.crypto.authentication import Authenticator
from src.core.crypto.key_storage import key_storage
from src.core.key_manager import KeyManager
from src.database.db import Database
from src.core.config import config
from src.core.vault.entry_manager import EntryManager
from src.core.crypto.password_validator import PasswordValidator


class TestSprint2Complete(unittest.TestCase):

    def setUp(self):
        self.kd = KeyDerivation()
        self.validator = PasswordValidator(min_length=12)
        self.temp_dir = None
        self.test_db_path = None
        self.db_connections = []

    def tearDown(self):
        for conn in self.db_connections:
            try:
                conn.close()
            except:
                pass

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                import time
                time.sleep(0.5)
                try:
                    shutil.rmtree(self.temp_dir)
                except:
                    pass

    def _create_test_db(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_vault.db")

        conn = sqlite3.connect(self.test_db_path)
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS key_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_type TEXT NOT NULL,
                salt TEXT,
                hash TEXT,
                key_data TEXT,
                params TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

        return self.test_db_path

    def test_1_argon2_params_validation(self):
        params = Argon2Params(3, 65536, 4)
        self.assertEqual(params.time_cost, 3)
        self.assertEqual(params.memory_cost, 65536)
        self.assertEqual(params.parallelism, 4)

        with self.assertRaises(ValueError):
            Argon2Params(0, 65536, 4)

        with self.assertRaises(ValueError):
            Argon2Params(3, 4096, 4)

        password = "MySecurePassword123!"
        auth_hash = self.kd.create_auth_hash(password)

        self.assertTrue(auth_hash.startswith('$argon2id'))
        self.assertIn('m=65536', auth_hash)
        self.assertIn('t=3', auth_hash)
        self.assertIn('p=4', auth_hash)

    def test_2_pbkdf2_consistency(self):
        password = "test123456789Secure!"
        salt = self.kd.create_salt()

        key1 = self.kd.derive_encryption_key(password, salt)
        key2 = self.kd.derive_encryption_key(password, salt)

        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)

    def test_3_key_clearing(self):
        test_key = os.urandom(32)

        key_storage.store_key(test_key)
        retrieved = key_storage.get_key()
        self.assertEqual(retrieved, test_key)

        key_storage.clear_key()
        self.assertIsNone(key_storage.get_key())

    def test_4_login_delay_logic(self):
        auth = Authenticator(self.kd)

        auth.failed_attempts = 0
        self.assertEqual(auth._get_delay(), 0)

        auth.failed_attempts = 2
        self.assertEqual(auth._get_delay(), 1)

        auth.failed_attempts = 3
        self.assertEqual(auth._get_delay(), 5)

        auth.failed_attempts = 5
        self.assertEqual(auth._get_delay(), 30)

    def test_5_lockout_after_5_failures(self):
        auth = Authenticator(self.kd)
        stored_hash = self.kd.create_auth_hash("correct123456Secure!")

        for i in range(5):
            auth.login(f"wrong_{i}", stored_hash)

        self.assertIsNotNone(auth.locked_until)

    def test_6_password_validator(self):
        validator = PasswordValidator(min_length=12)

        is_valid, _ = validator.validate("weak")
        self.assertFalse(is_valid)

        is_valid, _ = validator.validate("MySecureP@ssw0rd2024!")
        self.assertTrue(is_valid)

        strength = validator.check_strength("MySecureP@ssw0rd2024!")
        self.assertEqual(strength['strength'], 'strong')

    def test_7_full_authentication_flow(self):
        auth = Authenticator(self.kd)

        password = "MyMasterPassword123!"
        salt = self.kd.create_salt()
        stored_hash = self.kd.create_auth_hash(password)

        success, key = auth.login("wrong", stored_hash, salt)
        self.assertFalse(success)

        success, key = auth.login(password, stored_hash, salt)
        self.assertTrue(success)
        self.assertEqual(len(key), 32)

        auth.logout()
        self.assertIsNone(auth.session_start)

    def test_8_password_change_with_reencryption(self):
        self._create_test_db()

        old_db_path = config.get("db_path")
        config.set("db_path", self.test_db_path)

        db = Database()
        db.db_path = self.test_db_path
        db.connect()
        self.db_connections.append(db)

        km = KeyManager()
        kd = KeyDerivation()

        old_password = "OldMasterPassword123!"
        new_password = "NewMasterPassword456!"

        salt = kd.create_salt()
        auth_hash = kd.create_auth_hash(old_password)
        enc_key = kd.derive_encryption_key(old_password, salt)
        km.store_key(enc_key)

        db.execute("DELETE FROM master_password")
        db.execute(
            "INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
            (auth_hash, salt.hex())
        )

        em = EntryManager(db, km)

        entry_id = em.create_entry({
            'title': "Test Entry",
            'username': "testuser",
            'password': "testpass123",
            'url': "https://test.com",
            'notes': "Test",
            'tags': ["test"]
        })

        retrieved = em.get_entry(entry_id)
        self.assertEqual(retrieved['password'], "testpass123")

        new_salt = kd.create_salt()
        new_auth_hash = kd.create_auth_hash(new_password)
        new_enc_key = kd.derive_encryption_key(new_password, new_salt)

        all_entries = em.get_all_entries()
        for entry in all_entries:
            em.update_entry(entry['id'], entry)

        db.execute(
            "UPDATE master_password SET password_hash = ?, salt = ?",
            (new_auth_hash, new_salt.hex())
        )
        km.store_key(new_enc_key)

        retrieved_after = em.get_entry(entry_id)
        self.assertEqual(retrieved_after['password'], "testpass123")

        db.close()
        config.set("db_path", old_db_path)

    def test_9_vault_lock_without_key(self):
        self._create_test_db()

        old_db_path = config.get("db_path")
        config.set("db_path", self.test_db_path)

        db = Database()
        db.db_path = self.test_db_path
        db.connect()
        self.db_connections.append(db)

        km = KeyManager()
        kd = KeyDerivation()

        password = "TestPassword123!"
        salt = kd.create_salt()
        auth_hash = kd.create_auth_hash(password)
        enc_key = kd.derive_encryption_key(password, salt)
        km.store_key(enc_key)

        db.execute("DELETE FROM master_password")
        db.execute(
            "INSERT INTO master_password (password_hash, salt) VALUES (?, ?)",
            (auth_hash, salt.hex())
        )

        em = EntryManager(db, km)

        entry_id = em.create_entry({
            'title': "Test Entry",
            'username': "testuser",
            'password': "testpass123",
            'url': "https://test.com",
            'notes': "Test",
            'tags': ["test"]
        })

        retrieved = em.get_entry(entry_id)
        self.assertEqual(retrieved['password'], "testpass123")

        km.clear_key()
        self.assertIsNone(km.load_key())

        get_all_result = em.get_all_entries()
        self.assertEqual(len(get_all_result), 0)

        with self.assertRaises(ValueError):
            em.get_entry(entry_id)

        with self.assertRaises(ValueError):
            em.create_entry({
                'title': "New Entry",
                'username': "newuser",
                'password': "newpass123",
                'url': "https://new.com",
                'notes': "New",
                'tags': ["new"]
            })

        db.close()
        config.set("db_path", old_db_path)


if __name__ == '__main__':
    unittest.main()