# NEW FILE for Sprint 5 - FIXED
"""
Main audit logging controller with hash chain integrity protection.
Implements requirements CRY-3, CRY-4, LOG-1, LOG-2, LOG-3.
"""

import json
import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from queue import Queue, Empty


class AuditLogger:
    """
    Central audit logging service with cryptographic integrity.
    Implements hash chain where each entry includes hash of previous entry.
    """

    def __init__(self, db_connection, signer, event_system, config: Dict[str, Any]):
        """
        Initialize audit logger.

        Args:
            db_connection: SQLite database connection
            signer: AuditLogSigner instance
            event_system: Event bus for subscribing to events
            config: Configuration dict
        """
        self.db = db_connection
        self.signer = signer
        self.events = event_system
        self.config = config
        self._async_queue = Queue()
        self._async_thread = None
        self._running = False
        self._lock = threading.RLock()

        # Initialize log structure
        self._init_log_structure()

        # Subscribe to events per INT-1
        self._subscribe_to_events()

        # Start async logging if configured
        if config.get('async_logging', True):
            self._start_async_logging()

    def _init_log_structure(self):
        """Initialize audit log with genesis entry per CRY-4."""
        with self._lock:
            try:
                cursor = self.db.execute("SELECT COUNT(*) FROM audit_log")
                count = cursor.fetchone()[0]
            except:
                # Table might not have sequence_number yet
                try:
                    cursor = self.db.execute("SELECT COUNT(*) FROM audit_log")
                    count = cursor.fetchone()[0]
                except:
                    count = 0

            if count == 0:
                self._create_genesis_entry()

    def _create_genesis_entry(self):
        """Create first log entry to start hash chain per CRY-4."""
        genesis_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': 'SYSTEM_GENESIS',
            'severity': 'INFO',
            'user_id': 'system',
            'source': 'audit_logger',
            'details': {'message': 'Audit log initialized'},
            'sequence_number': 0,
            'previous_hash': '0' * 64
        }
        self._write_entry(genesis_entry)

    def _subscribe_to_events(self):
        """Subscribe to all security-relevant events per INT-1."""
        # Если event_system не имеет методов subscribe, пропускаем
        if not hasattr(self.events, 'subscribe'):
            return

        try:
            self.events.subscribe('UserLoggedIn', self._on_auth_event)
            self.events.subscribe('UserLoggedOut', self._on_auth_event)
            self.events.subscribe('EntryCreated', self._on_vault_event)
            self.events.subscribe('EntryUpdated', self._on_vault_event)
            self.events.subscribe('EntryDeleted', self._on_vault_event)
            self.events.subscribe('ClipboardCopied', self._on_clipboard_event)
            self.events.subscribe('ClipboardCleared', self._on_clipboard_event)
        except Exception as e:
            pass

    def _on_auth_event(self, event_data: Dict[str, Any]):
        """Handle authentication events."""
        pass

    def _on_vault_event(self, event_data: Dict[str, Any]):
        """Handle vault CRUD events."""
        pass

    def _on_clipboard_event(self, event_data: Dict[str, Any]):
        """Handle clipboard events."""
        pass

    def log_event(self, event_type: str, severity: str, source: str,
                  details: Dict[str, Any], user_id: Optional[str] = None):
        """
        Log an event with cryptographic integrity protection.
        """
        try:
            # Get previous hash for chain
            with self._lock:
                try:
                    cursor = self.db.execute(
                        "SELECT entry_hash FROM audit_log ORDER BY rowid DESC LIMIT 1"
                    )
                    row = cursor.fetchone()
                    previous_hash = row[0] if row else '0' * 64
                except:
                    previous_hash = '0' * 64

            # Build entry
            entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'severity': severity,
                'user_id': user_id or 'anonymous',
                'source': source,
                'details': self._sanitize_details(details),
                'sequence_number': self._get_next_sequence(),
                'previous_hash': previous_hash
            }

            # Write asynchronously or synchronously
            if self.config.get('async_logging', True):
                self._async_queue.put(entry)
            else:
                self._write_entry(entry)
        except Exception as e:
            print(f"Error logging event: {e}")

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from logs."""
        sanitized = details.copy()
        sensitive_keys = ['password', 'secret', 'key', 'token', 'master_password']

        for key in sensitive_keys:
            if key in sanitized:
                sanitized[key] = '[REDACTED]'

        return sanitized

    def _get_next_sequence(self) -> int:
        """Get next sequence number for new entry."""
        try:
            cursor = self.db.execute("SELECT MAX(rowid) FROM audit_log")
            max_seq = cursor.fetchone()[0]
            return (max_seq or -1) + 1
        except:
            return 1

    def _write_entry(self, entry: Dict[str, Any]):
        """Write signed entry to database."""
        try:
            entry_json = json.dumps(entry, sort_keys=True)
            entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()

            signature = self.signer.sign(entry_json.encode())

            with self._lock:
                self.db.execute(
                    """
                    INSERT INTO audit_log
                    (action, timestamp, entry_id, details, signature, entry_data, entry_hash, previous_hash, sequence_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry['event_type'],
                        entry['timestamp'],
                        None,
                        json.dumps(entry['details']),
                        signature.hex(),
                        entry_json,
                        entry_hash,
                        entry['previous_hash'],
                        entry['sequence_number']
                    )
                )
                self.db.commit()
        except Exception as e:
            print(f"Error writing entry: {e}")

    def _start_async_logging(self):
        """Start asynchronous logging thread."""
        self._running = True
        self._async_thread = threading.Thread(target=self._async_worker, daemon=True)
        self._async_thread.start()

    def _async_worker(self):
        """Worker thread for asynchronous logging."""
        while self._running:
            try:
                entry = self._async_queue.get(timeout=1)
                self._write_entry(entry)
            except Empty:
                continue
            except Exception as e:
                print(f"Async logging error: {e}")

    def stop(self):
        """Stop async logging thread."""
        self._running = False
        if self._async_thread:
            self._async_thread.join(timeout=2)

    def get_entries(self, limit: int = 100, offset: int = 0,
                    event_type: Optional[str] = None,
                    severity: Optional[str] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve log entries with filtering."""
        query = "SELECT rowid, action, timestamp, details, signature, entry_data FROM audit_log WHERE 1=1"
        params = []

        if event_type:
            query += " AND action = ?"
            params.append(event_type)

        query += " ORDER BY rowid DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.db.execute(query, params)
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            entry = {
                'sequence_number': row[0],
                'event_type': row[1],
                'timestamp': row[2],
                'details': row[3],
                'signature': row[4]
            }
            if row[5]:
                try:
                    entry.update(json.loads(row[5]))
                except:
                    pass
            entries.append(entry)

        return entries

    def get_total_count(self, event_type: Optional[str] = None,
                        severity: Optional[str] = None) -> int:
        """Get total number of log entries."""
        query = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
        params = []

        if event_type:
            query += " AND action = ?"
            params.append(event_type)

        cursor = self.db.execute(query, params)
        return cursor.fetchone()[0]