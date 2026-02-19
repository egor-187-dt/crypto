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


if __name__ == '__main__':
    unittest.main()