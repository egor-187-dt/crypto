import unittest
from src.core.crypto.placeholder import AES256Placeholder


class TestCrypto(unittest.TestCase):
    def test_xor_encrypt_decrypt(self):
        crypto = AES256Placeholder()
        data = b"secret_password"
        key = b"1234"

        encrypted = crypto.encrypt(data, key)
        decrypted = crypto.decrypt(encrypted, key)

        self.assertEqual(data, decrypted)

    def test_key_manager_clear(self):
        from src.core.key_manager import KeyManager
        km = KeyManager()
        key = b"testkey123"
        km.store_key(key)
        self.assertIsNotNone(km.load_key())
        km.clear_key()
        self.assertIsNone(km.load_key())
        print("Тест очистки ключа прошел")
if __name__ == '__main__':
    unittest.main()