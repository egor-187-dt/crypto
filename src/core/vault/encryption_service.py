import os
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AESGCMEncryption:
    """AES-256-GCM encryption service per Sprint 3 requirements"""

    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        self.key = key
        self._cipher = AESGCM(key)

    def encrypt(self, data: dict) -> bytes:
        """Encrypt dictionary with unique nonce (12 bytes)"""
        nonce = os.urandom(12)
        plaintext = json.dumps(data, ensure_ascii=False).encode('utf-8')
        ciphertext = self._cipher.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def decrypt(self, encrypted_blob: bytes) -> dict:
        """Decrypt and verify authentication tag"""
        nonce = encrypted_blob[:12]
        ciphertext = encrypted_blob[12:]
        plaintext = self._cipher.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode('utf-8'))