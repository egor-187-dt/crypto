import json
from datetime import datetime
from src.core.events import events
from src.core.vault.encryption_service import AESGCMEncryption


class EntryManager:
    """
    CRUD operations for vault entries with AES-256-GCM encryption
    Implements Sprint 3 requirements: ARC-1, CRUD-1, CRUD-2, CRUD-3, CRUD-4
    """

    def __init__(self, db_connection, key_manager):
        self.db = db_connection
        self.key_manager = key_manager
        self._encryption = None

    def _get_encryption(self):
        if self._encryption is None:
            key = self.key_manager.load_key()
            if not key:
                raise ValueError("Vault is locked. Authentication required.")
            if len(key) != 32:
                import hashlib
                key = hashlib.sha256(key).digest()
            self._encryption = AESGCMEncryption(key)
        return self._encryption

    def create_entry(self, data: dict) -> int:
        """Create new entry with AES-256-GCM encryption"""
        if not self.key_manager.load_key():
            raise ValueError("Vault is locked")

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
        tags_str = ','.join(payload['tags']) if payload['tags'] else ''

        cursor = self.db.execute(
            "INSERT INTO vault_entries (encrypted_data, title, username, url, notes, tags, created_at, updated_at, deleted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (encrypted_blob, payload['title'], payload['username'], payload['url'], payload['notes'], tags_str, now,
             now, 0)
        )

        entry_id = cursor.lastrowid
        events.publish('entry_created', {'entry_id': entry_id})
        return entry_id

    def get_entry(self, entry_id: int) -> dict:
        """Retrieve and decrypt single entry"""
        if not self.key_manager.load_key():
            raise ValueError("Vault is locked")

        row = self.db.fetch_one(
            "SELECT encrypted_data FROM vault_entries WHERE id = ? AND deleted = 0",
            (entry_id,)
        )
        if not row:
            raise ValueError(f"Entry {entry_id} not found")

        data = self._get_encryption().decrypt(row[0])
        data['id'] = entry_id
        return data

    def get_all_entries(self) -> list:
        """Retrieve all non-deleted entries"""
        if not self.key_manager.load_key():
            return []

        rows = self.db.fetch_all(
            "SELECT id, encrypted_data FROM vault_entries WHERE deleted = 0 ORDER BY updated_at DESC"
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
                    continue

        return entries

    def update_entry(self, entry_id: int, data: dict) -> dict:
        """Update existing entry with re-encryption"""
        if not self.key_manager.load_key():
            raise ValueError("Vault is locked")

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
        tags_str = ','.join(payload['tags']) if payload['tags'] else ''

        self.db.execute(
            "UPDATE vault_entries SET encrypted_data=?, title=?, username=?, url=?, notes=?, tags=?, updated_at=? WHERE id=? AND deleted=0",
            (encrypted_blob, payload['title'], payload['username'], payload['url'], payload['notes'], tags_str, now,
             entry_id)
        )

        events.publish('entry_updated', {'entry_id': entry_id})
        return self.get_entry(entry_id)

    def delete_entry(self, entry_id: int, soft_delete: bool = True) -> None:
        """Soft delete or permanent delete entry"""
        if not self.key_manager.load_key():
            raise ValueError("Vault is locked")

        if soft_delete:
            self.db.execute(
                "UPDATE vault_entries SET deleted=1, deleted_at=? WHERE id=?",
                (datetime.now().isoformat(), entry_id)
            )
        else:
            self.db.execute("DELETE FROM vault_entries WHERE id=?", (entry_id,))

        events.publish('entry_deleted', {'entry_id': entry_id})

    def search(self, query: str) -> list:
        """Search entries by title, username, url, notes"""
        if not query:
            return self.get_all_entries()

        query_lower = query.lower()
        results = []

        for entry in self.get_all_entries():
            if (query_lower in entry.get('title', '').lower() or
                    query_lower in entry.get('username', '').lower() or
                    query_lower in entry.get('url', '').lower() or
                    query_lower in entry.get('notes', '').lower()):
                results.append(entry)

        return results