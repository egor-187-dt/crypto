from src.core.crypto.abstract import EncryptionService

class AES256Placeholder(EncryptionService):
    # заглушка,потом заменим на AES
    def encrypt(self, data: bytes, key: bytes) -> bytes:
        # Простой XOR для теста
        return bytes(a ^ b for a, b in zip(data, key * 100))

    def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        # XOR обратимый
        return bytes(a ^ b for a, b in zip(ciphertext, key * 100))