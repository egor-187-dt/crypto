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
        if self._encryption is None:
            key = self.key_manager.load_key()
            print(f"DEBUG: key = {key is not None}, len={len(key) if key else 0}")
            if not key:
                raise ValueError("No encryption key available")
            if len(key) != 32:
                import hashlib
                key = hashlib.sha256(key).digest()
                print(f"DEBUG: key converted to 32 bytes")
            self._encryption = AESGCMEncryption(key)
        return self._encryption

    def create_entry(self, data: dict) -> str:
        print("=== CREATE ENTRY ===")
        print("Data:", data)

        entry_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        payload = {
            'title': data.get('title', ''),
            'username': data.get('username', ''),
            'password': data.get('password', ''),
            'url': data.get('url', ''),
            'notes': data.get('notes', ''),
            'category': data.get('category', ''),
            'tags': data.get('tags', []),
            'version': 2,
            'created_at': now,
            'updated_at': now
        }
        print(f"Payload: {payload['title']}, {payload['username']}")

        encrypted_blob = self._get_encryption().encrypt(payload)
        print(f"Encrypted blob size: {len(encrypted_blob)}")

        self.db.execute(
            """INSERT INTO vault_entries 
               (id, encrypted_data, title, username, url, notes, tags, created_at, updated_at, deleted) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, encrypted_blob, payload['title'], payload['username'],
             payload['url'], payload['notes'], ','.join(payload['tags']), now, now, 0)
        )
        print(f"SAVED: {entry_id}")

        events.publish('entry_created', {'entry_id': entry_id})
        return entry_id

    def get_entry(self, entry_id: str) -> dict:
        row = self.db.fetch_all(
            "SELECT encrypted_data FROM vault_entries WHERE id = ? AND (deleted = 0 OR deleted IS NULL)",
            (entry_id,)
        )
        if not row:
            raise ValueError("Entry not found")

        encrypted_blob = row[0][0]

        try:
            data = self._get_encryption().decrypt(encrypted_blob)
            data['id'] = entry_id
            return data
        except Exception as e:
            print(f"Decrypt error: {e}")
            return self._decrypt_old(entry_id)

    def _decrypt_old(self, entry_id: str) -> dict:
        row = self.db.fetch_all(
            "SELECT encrypted_password, title, username, url, notes, tags FROM vault_entries WHERE id = ?",
            (entry_id,)
        )
        if not row:
            raise ValueError("Entry not found")

        encrypted_text, title, username, url, notes, tags = row[0]
        key = self.key_manager.load_key()

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
        rows = self.db.fetch_all(
            "SELECT id, encrypted_data, title, username, encrypted_password, url, notes, tags FROM vault_entries WHERE deleted = 0 OR deleted IS NULL"
        )
        entries = []

        for row in rows:
            entry_id, encrypted_blob, title, username, old_enc, url, notes, tags = row

            if encrypted_blob:
                try:
                    data = self._get_encryption().decrypt(encrypted_blob)
                    data['id'] = entry_id
                    entries.append(data)
                    continue
                except:
                    pass

            if old_enc:
                try:
                    key = self.key_manager.load_key()
                    encrypted_bytes = base64.b64decode(old_enc)
                    decrypted_bytes = bytes(
                        [encrypted_bytes[i] ^ key[i % len(key)] for i in range(len(encrypted_bytes))])
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
                except:
                    pass

        return entries

    def update_entry(self, entry_id: str, data: dict) -> dict:
        now = datetime.now().isoformat()
        existing = self.get_entry(entry_id)

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

        encrypted_blob = self._get_encryption().encrypt(payload)

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