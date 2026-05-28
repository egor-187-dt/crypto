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
            if not key:
                raise ValueError("No encryption key available. Vault is locked.")
            if len(key) != 32:
                import hashlib
                key = hashlib.sha256(key).digest()
            self._encryption = AESGCMEncryption(key)
        return self._encryption

    def _check_key_available(self):
        key = self.key_manager.load_key()
        if not key:
            raise ValueError("No encryption key available. Vault is locked.")
        return True

    def create_entry(self, data: dict) -> str:
        self._check_key_available()

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

        encrypted_blob = self._get_encryption().encrypt(payload)

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
        self._check_key_available()

        row = self.db.fetch_all(
            "SELECT encrypted_data FROM vault_entries WHERE id = ? AND (deleted = 0 OR deleted IS NULL)",
            (entry_id,)
        )
        if not row:
            raise ValueError("Entry not found")

        encrypted_blob = row[0][0]

        if encrypted_blob is None:
            raise ValueError(f"Entry {entry_id} has no encrypted data")

        data = self._get_encryption().decrypt(encrypted_blob)
        data['id'] = entry_id
        return data

    def get_all_entries(self) -> list:
        key = self.key_manager.load_key()
        if not key:
            return []

        rows = self.db.fetch_all(
            "SELECT id, encrypted_data FROM vault_entries WHERE deleted = 0 OR deleted IS NULL"
        )
        entries = []

        for row in rows:
            entry_id, encrypted_blob = row
            if encrypted_blob:
                try:
                    self._encryption = None
                    data = self._get_encryption().decrypt(encrypted_blob)
                    data['id'] = entry_id
                    entries.append(data)
                except Exception:
                    pass

        return entries

    def update_entry(self, entry_id: str, data: dict) -> dict:
        self._check_key_available()

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
        self._check_key_available()

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