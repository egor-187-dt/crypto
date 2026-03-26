import json
import uuid
from datetime import datetime
from src.core.events import events
from src.core.crypto.aes_gcm import AESGCMEncryption
import base64


class EntryManager:
    def __init__(self, db_connection, key_manager):
        self.db = db_connection
        self.key_manager = key_manager
        self._encryption = None

    def _get_encryption(self):
        """Получает AES-GCM шифровальщик"""
        if self._encryption is None:
            key = self.key_manager.load_key()
            if not key:
                raise ValueError("No encryption key available")
            # Убедимся что ключ 32 байта
            if len(key) != 32:
                # Если ключ старый (XOR), создаем новый из него
                import hashlib
                key = hashlib.sha256(key).digest()
            self._encryption = AESGCMEncryption(key)
        return self._encryption

    def create_entry(self, data: dict) -> str:
        """Создает новую запись с AES-GCM шифрованием"""
        entry_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # Подготовка данных для шифрования
        payload = {
            'title': data.get('title', ''),
            'username': data.get('username', ''),
            'password': data.get('password', ''),
            'url': data.get('url', ''),
            'notes': data.get('notes', ''),
            'category': data.get('category', ''),
            'tags': data.get('tags', []),
            'version': 2,  # Версия 2 = AES-GCM
            'created_at': now,
            'updated_at': now
        }

        # Шифруем
        encrypted_blob = self._get_encryption().encrypt(payload)

        # Сохраняем в БД
        self.db.execute(
            """INSERT INTO vault_entries 
               (id, encrypted_data, title, username, url, notes, tags, created_at, updated_at, deleted) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, encrypted_blob, payload['title'], payload['username'],
             payload['url'], payload['notes'], ','.join(payload['tags']), now, now, 0)
        )

        events.publish('entry_created', {'entry_id': entry_id})
        return entry_id

    def get_entry(self, entry_id: str) -> dict:
        """Получает и расшифровывает запись"""
        row = self.db.fetch_all(
            "SELECT encrypted_data FROM vault_entries WHERE id = ? AND (deleted = 0 OR deleted IS NULL)",
            (entry_id,)
        )
        if not row:
            raise ValueError("Entry not found")

        encrypted_blob = row[0][0]

        # Пробуем расшифровать AES-GCM
        try:
            data = self._get_encryption().decrypt(encrypted_blob)
            data['id'] = entry_id
            return data
        except:
            # Если не получилось, пробуем старый XOR (для обратной совместимости)
            return self._decrypt_old(entry_id, encrypted_blob)

    def _decrypt_old(self, entry_id: str, encrypted_blob=None) -> dict:
        """Старый метод для XOR шифрования"""
        if encrypted_blob is None:
            row = self.db.fetch_all(
                "SELECT encrypted_password, title, username, url, notes, tags FROM vault_entries WHERE id = ?",
                (entry_id,)
            )
            if not row:
                raise ValueError("Entry not found")
            encrypted_text, title, username, url, notes, tags = row[0]
        else:
            # Если передан blob, значит это старая запись в новом формате?
            # Пробуем декодировать как base64
            try:
                encrypted_text = encrypted_blob.decode('ascii')
            except:
                encrypted_text = base64.b64encode(encrypted_blob).decode('ascii')
            row = self.db.fetch_all(
                "SELECT title, username, url, notes, tags FROM vault_entries WHERE id = ?",
                (entry_id,)
            )
            if row:
                title, username, url, notes, tags = row[0]
            else:
                title, username, url, notes, tags = '', '', '', '', ''

        key = self.key_manager.load_key()
        if not key:
            raise ValueError("No key")

        encrypted_bytes = base64.b64decode(encrypted_text)
        decrypted_bytes = bytes([encrypted_bytes[i] ^ key[i % len(key)] for i in range(len(encrypted_bytes))])
        password = decrypted_bytes.decode('utf-8')

        return {
            'id': entry_id,
            'title': title,
            'username': username,
            'password': password,
            'url': url,
            'notes': notes,
            'tags': tags.split(',') if tags else [],
            'version': 1
        }

    def get_all_entries(self) -> list:
        """Получает все записи"""
        rows = self.db.fetch_all(
            "SELECT id, encrypted_data, title, username, encrypted_password, url, notes, tags FROM vault_entries WHERE deleted = 0 OR deleted IS NULL"
        )
        entries = []

        for row in rows:
            entry_id, encrypted_blob, title, username, old_enc, url, notes, tags = row

            # Пробуем расшифровать AES-GCM
            try:
                if encrypted_blob:
                    data = self._get_encryption().decrypt(encrypted_blob)
                    data['id'] = entry_id
                    entries.append(data)
                    continue
            except:
                pass

            # Пробуем старый XOR
            try:
                if old_enc:
                    key = self.key_manager.load_key()
                    encrypted_bytes = base64.b64decode(old_enc)
                    decrypted_bytes = bytes([encrypted_bytes[i] ^ key[i % len(key)] for i in range(len(encrypted_bytes))])
                    password = decrypted_bytes.decode('utf-8')

                    entries.append({
                        'id': entry_id,
                        'title': title,
                        'username': username,
                        'password': password,
                        'url': url,
                        'notes': notes,
                        'tags': tags.split(',') if tags else [],
                        'version': 1
                    })
            except Exception as e:
                print(f"Failed to decrypt entry {entry_id}: {e}")

        return entries

    def update_entry(self, entry_id: str, data: dict) -> dict:
        """Обновляет запись с AES-GCM"""
        now = datetime.now().isoformat()

        # Получаем существующую запись
        existing = self.get_entry(entry_id)

        # Обновляем данные
        payload = {
            'title': data.get('title', existing.get('title', '')),
            'username': data.get('username', existing.get('username', '')),
            'password': data.get('password', existing.get('password', '')),
            'url': data.get('url', existing.get('url', '')),
            'notes': data.get('notes', existing.get('notes', '')),
            'category': data.get('category', existing.get('category', '')),
            'tags': data.get('tags', existing.get('tags', [])),
            'version': 2,
            'created_at': existing.get('created_at', now),
            'updated_at': now
        }

        # Шифруем
        encrypted_blob = self._get_encryption().encrypt(payload)

        # Обновляем в БД
        self.db.execute(
            """UPDATE vault_entries 
               SET encrypted_data = ?, title = ?, username = ?, url = ?, notes = ?, tags = ?, updated_at = ? 
               WHERE id = ?""",
            (encrypted_blob, payload['title'], payload['username'],
             payload['url'], payload['notes'], ','.join(payload['tags']), now, entry_id)
        )

        events.publish('entry_updated', {'entry_id': entry_id})
        return self.get_entry(entry_id)

    def delete_entry(self, entry_id: str, soft_delete: bool = True):
        """Удаляет запись"""
        if soft_delete:
            now = datetime.now().isoformat()
            self.db.execute(
                "UPDATE vault_entries SET deleted = 1, deleted_at = ? WHERE id = ?",
                (now, entry_id)
            )
        else:
            self.db.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))
        events.publish('entry_deleted', {'entry_id': entry_id})

    def search(self, query: str) -> list:
        """Поиск по записям"""
        if not query:
            return self.get_all_entries()

        query_lower = query.lower()
        entries = self.get_all_entries()
        results = []

        for e in entries:
            if (query_lower in e.get('title', '').lower() or
                query_lower in e.get('username', '').lower() or
                query_lower in e.get('url', '').lower() or
                query_lower in e.get('notes', '').lower()):
                results.append(e)
        return results