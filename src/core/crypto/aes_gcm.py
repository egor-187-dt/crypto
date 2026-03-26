from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import json


class AESGCMEncryption:
    """AES-256-GCM шифрование"""

    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        self.key = key
        self.aesgcm = AESGCM(key)

    def encrypt(self, data: dict) -> bytes:
        """Шифрует словарь, возвращает nonce + ciphertext"""
        nonce = os.urandom(12)
        plaintext = json.dumps(data).encode('utf-8')
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def decrypt(self, encrypted_blob: bytes) -> dict:
        """Расшифровывает, возвращает словарь"""
        nonce = encrypted_blob[:12]
        ciphertext = encrypted_blob[12:]
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode('utf-8'))