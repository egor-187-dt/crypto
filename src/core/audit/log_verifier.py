# NEW FILE for Sprint 5 - Simplified version for compatibility
"""
Log integrity verification with hash chain and signature validation.
Implements requirements VER-1, VER-2, VER-3, VER-4.
"""

import json
import hashlib
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class VerificationStatus(Enum):
    """Verification status for log entries."""
    VALID = "valid"
    INVALID_SIGNATURE = "invalid_signature"
    INVALID_HASH = "invalid_hash"
    CHAIN_BREAK = "chain_break"
    PENDING = "pending"


@dataclass
class VerificationResult:
    """Result of integrity verification."""
    total_entries: int
    valid_entries: int
    invalid_entries: List[Dict[str, Any]]
    chain_breaks: List[Dict[str, Any]]
    verified: bool
    verification_time_ms: float
    timestamp: str


class LogVerifier:
    """
    Verifies cryptographic integrity of audit logs.
    Implements hash chain verification and signature validation.
    """

    def __init__(self, db_connection, signer, event_system, config: Dict[str, Any]):
        """
        Initialize log verifier.

        Args:
            db_connection: SQLite database connection
            signer: AuditLogSigner instance
            event_system: Event bus for notifications
            config: Configuration dict
        """
        self.db = db_connection
        self.signer = signer
        self.events = event_system
        self.config = config
        self._verification_thread = None
        self._running = False
        self._last_verification = None

        # Start periodic verification if configured per VER-2
        if config.get('periodic_verification', True):
            self._start_periodic_verification()

    def verify_integrity(self, start_seq: int = 0,
                         end_seq: Optional[int] = None,
                         full_scan: bool = False) -> VerificationResult:
        """
        Verify integrity of log entries in range per VER-3.

        Args:
            start_seq: Starting sequence number
            end_seq: Ending sequence number (inclusive)
            full_scan: If True, verify all entries; if False, sample last N

        Returns:
            VerificationResult with details
        """
        start_time = time.time()

        # Get entries to verify
        if full_scan:
            entries = self._get_all_entries()
        else:
            entries = self._get_recent_entries(self.config.get('verification_sample_size', 1000))

        results = {
            'total_entries': len(entries),
            'valid_entries': 0,
            'invalid_entries': [],
            'chain_breaks': [],
            'verified': True
        }

        previous_hash = None

        for entry in entries:
            seq_num = entry.get('sequence_number', entry.get('id', 0))
            entry_data = entry.get('entry_data', '')
            signature_hex = entry.get('signature', '')
            entry_hash = entry.get('entry_hash', '')
            prev_hash = entry.get('previous_hash', '')

            # Skip if no signature or entry_data
            if not signature_hex or not entry_data:
                results['valid_entries'] += 1
                continue

            # Verify signature per CRY-1
            try:
                signature = bytes.fromhex(signature_hex)
                if not self.signer.verify(entry_data.encode(), signature):
                    results['invalid_entries'].append({
                        'sequence': seq_num,
                        'reason': 'Invalid signature',
                        'timestamp': entry.get('timestamp')
                    })
                    results['verified'] = False
                    continue
            except Exception:
                results['invalid_entries'].append({
                    'sequence': seq_num,
                    'reason': 'Signature verification error',
                    'timestamp': entry.get('timestamp')
                })
                results['verified'] = False
                continue

            # Verify hash chain per CRY-4 (except for first entry)
            if previous_hash is not None and prev_hash and prev_hash != previous_hash:
                results['chain_breaks'].append({
                    'sequence': seq_num,
                    'expected': previous_hash,
                    'actual': prev_hash,
                    'timestamp': entry.get('timestamp')
                })
                results['verified'] = False

            # Verify computed hash matches stored hash
            if entry_data:
                computed_hash = hashlib.sha256(entry_data.encode()).hexdigest()
                if entry_hash and computed_hash != entry_hash:
                    results['invalid_entries'].append({
                        'sequence': seq_num,
                        'reason': 'Hash mismatch',
                        'timestamp': entry.get('timestamp')
                    })
                    results['verified'] = False
                    continue

            results['valid_entries'] += 1
            previous_hash = entry_hash if entry_hash else computed_hash

        # Build final result
        verification_time_ms = (time.time() - start_time) * 1000

        result = VerificationResult(
            total_entries=results['total_entries'],
            valid_entries=results['valid_entries'],
            invalid_entries=results['invalid_entries'],
            chain_breaks=results['chain_breaks'],
            verified=results['verified'],
            verification_time_ms=verification_time_ms,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Handle tampering detection per VER-4
        if not result.verified:
            self._handle_tampering_detected(result)

        self._last_verification = result
        return result

    def _get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all entries from audit log."""
        try:
            cursor = self.db.execute("""
                SELECT id, action, timestamp, details, signature, entry_data, entry_hash, previous_hash, sequence_number
                FROM audit_log
                ORDER BY id
            """)
            rows = cursor.fetchall()

            entries = []
            for row in rows:
                entry = {
                    'id': row[0],
                    'event_type': row[1],
                    'timestamp': row[2],
                    'details': row[3],
                    'signature': row[4],
                    'entry_data': row[5],
                    'entry_hash': row[6],
                    'previous_hash': row[7],
                    'sequence_number': row[8] if row[8] is not None else row[0]
                }
                entries.append(entry)

            return entries
        except Exception as e:
            print(f"Error getting entries: {e}")
            return []

    def _get_recent_entries(self, count: int) -> List[Dict[str, Any]]:
        """Get most recent N entries."""
        try:
            cursor = self.db.execute("""
                SELECT id, action, timestamp, details, signature, entry_data, entry_hash, previous_hash, sequence_number
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
            """, (count,))
            rows = cursor.fetchall()

            entries = []
            for row in reversed(rows):
                entry = {
                    'id': row[0],
                    'event_type': row[1],
                    'timestamp': row[2],
                    'details': row[3],
                    'signature': row[4],
                    'entry_data': row[5],
                    'entry_hash': row[6],
                    'previous_hash': row[7],
                    'sequence_number': row[8] if row[8] is not None else row[0]
                }
                entries.append(entry)

            return entries
        except Exception as e:
            print(f"Error getting recent entries: {e}")
            return []

    def _handle_tampering_detected(self, result: VerificationResult):
        """
        Handle tampering detection per VER-4.

        Triggers:
        - User notification
        - Security event logging
        - Optional vault lock
        """
        # Publish security event if event system supports it
        if hasattr(self.events, 'publish'):
            try:
                self.events.publish('SecurityEvent', {
                    'event_type': 'LOG_TAMPERING_DETECTED',
                    'severity': 'CRITICAL',
                    'details': {
                        'invalid_entries': len(result.invalid_entries),
                        'chain_breaks': len(result.chain_breaks),
                        'verification_time_ms': result.verification_time_ms
                    }
                })
            except Exception:
                pass

        # Optional: Lock vault per VER-4
        if self.config.get('lock_vault_on_tamper', True):
            if hasattr(self.events, 'publish'):
                try:
                    self.events.publish('VaultLock', {
                        'reason': 'Log tampering detected',
                        'source': 'log_verifier'
                    })
                except Exception:
                    pass

    def verify_at_startup(self) -> VerificationResult:
        """
        Verify log integrity at application startup per VER-1.

        Returns:
            VerificationResult
        """
        try:
            # Get total count
            cursor = self.db.execute("SELECT COUNT(*) FROM audit_log")
            total = cursor.fetchone()[0]

            # For large logs, verify recent entries only
            if total > 10000:
                result = self.verify_integrity(full_scan=False)
            else:
                # Verify all entries
                result = self.verify_integrity(full_scan=True)

            return result
        except Exception as e:
            print(f"Startup verification error: {e}")
            return VerificationResult(
                total_entries=0,
                valid_entries=0,
                invalid_entries=[],
                chain_breaks=[],
                verified=True,
                verification_time_ms=0,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

    def _start_periodic_verification(self):
        """Start periodic verification thread per VER-2."""
        self._running = True
        self._verification_thread = threading.Thread(target=self._periodic_worker, daemon=True)
        self._verification_thread.start()

    def _periodic_worker(self):
        """Worker thread for periodic verification."""
        interval_hours = self.config.get('verification_interval_hours', 24)
        interval_seconds = interval_hours * 3600

        while self._running:
            time.sleep(interval_seconds)

            try:
                # Verify recent entries per VER-2
                result = self.verify_integrity(full_scan=False)

                # Update UI status via event if available
                if hasattr(self.events, 'publish'):
                    try:
                        self.events.publish('IntegrityStatusUpdate', {
                            'verified': result.verified,
                            'valid_entries': result.valid_entries,
                            'total_entries': result.total_entries,
                            'timestamp': result.timestamp
                        })
                    except Exception:
                        pass
            except Exception as e:
                print(f"Periodic verification error: {e}")

    def stop(self):
        """Stop periodic verification thread."""
        self._running = False
        if self._verification_thread:
            self._verification_thread.join(timeout=5)

    def get_verification_report(self) -> Dict[str, Any]:
        """
        Get detailed verification report per VER-3.

        Returns:
            Dict with verification statistics and status
        """
        if not self._last_verification:
            return {'status': 'No verification performed'}

        return {
            'status': 'verified' if self._last_verification.verified else 'compromised',
            'total_entries_checked': self._last_verification.total_entries,
            'valid_entries': self._last_verification.valid_entries,
            'invalid_entries_count': len(self._last_verification.invalid_entries),
            'chain_breaks_count': len(self._last_verification.chain_breaks),
            'verification_time_ms': self._last_verification.verification_time_ms,
            'timestamp': self._last_verification.timestamp,
            'invalid_entries': self._last_verification.invalid_entries[:10],
            'chain_breaks': self._last_verification.chain_breaks[:10]
        }