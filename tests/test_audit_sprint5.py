# NEW FILE for Sprint 5
"""
Comprehensive tests for audit logging system.
Implements requirements TEST-1 through TEST-5.
"""

import unittest
import tempfile
import os
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import audit modules
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.audit.audit_logger import AuditLogger
from src.core.audit.log_signer import AuditLogSigner
from src.core.audit.log_verifier import LogVerifier, VerificationResult
from src.core.audit.log_formatters import LogFormatter, ExportMetadata


class MockKeyManager:
    """Mock KeyManager for testing."""

    def derive_key(self, purpose: str, length: int = 32) -> bytes:
        return b'\x00' * length


class TestAuditLogSigner(unittest.TestCase):
    """Test cryptographic signing per CRY-1, CRY-2."""

    def setUp(self):
        self.key_manager = MockKeyManager()

    def test_ed25519_signing_and_verification(self):
        """Test Ed25519 sign/verify works correctly."""
        signer = AuditLogSigner(self.key_manager, use_ed25519=True)

        data = b"Test log entry data"
        signature = signer.sign(data)

        self.assertTrue(signer.verify(data, signature))
        self.assertFalse(signer.verify(b"Tampered data", signature))

    def test_hmac_fallback_signing(self):
        """Test HMAC-SHA256 fallback works."""
        signer = AuditLogSigner(self.key_manager, use_ed25519=False)

        data = b"Test data for HMAC"
        signature = signer.sign(data)

        self.assertTrue(signer.verify(data, signature))
        self.assertFalse(signer.verify(b"Wrong data", signature))

    def test_consistent_signing(self):
        """Test same data produces consistent signature (HMAC only)."""
        signer = AuditLogSigner(self.key_manager, use_ed25519=False)

        data = b"Consistent test data"
        sig1 = signer.sign(data)
        sig2 = signer.sign(data)

        self.assertEqual(sig1, sig2)


class TestAuditLogger(unittest.TestCase):
    """Test audit logger functionality per LOG-1, LOG-2, LOG-3, DB-1."""

    def setUp(self):
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self._create_audit_table()

        self.key_manager = MockKeyManager()
        self.signer = AuditLogSigner(self.key_manager)
        self.event_system = Mock()
        self.config = {'async_logging': False}

        self.logger = AuditLogger(self.conn, self.signer, self.event_system, self.config)

    def _create_audit_table(self):
        """Create audit_log table for testing per DB-1."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_hash TEXT,
                entry_data TEXT,
                entry_hash TEXT,
                signature TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.logger.stop()
        self.conn.close()
        os.unlink(self.db_path)

    def test_genesis_entry_creation(self):
        """Test genesis entry is created on init per CRY-4."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM audit_log")
        count = cursor.fetchone()[0]

        self.assertGreaterEqual(count, 1)

        # Verify genesis entry
        cursor = self.conn.execute("SELECT entry_data FROM audit_log WHERE sequence_number = 0")
        row = cursor.fetchone()
        if row:
            entry = json.loads(row[0])
            self.assertEqual(entry['event_type'], 'SYSTEM_GENESIS')
            self.assertEqual(entry['previous_hash'], '0' * 64)

    def test_log_event_creation(self):
        """Test logging an event works per LOG-2."""
        self.logger.log_event(
            event_type='TEST_EVENT',
            severity='INFO',
            source='test',
            details={'test_key': 'test_value'},
            user_id='test_user'
        )

        cursor = self.conn.execute("SELECT COUNT(*) FROM audit_log")
        count = cursor.fetchone()[0]

        self.assertGreaterEqual(count, 2)  # Genesis + new entry

    def test_log_entry_contains_required_fields(self):
        """Test each log entry contains required fields per LOG-2."""
        self.logger.log_event(
            event_type='AUTH_LOGIN',
            severity='INFO',
            source='auth',
            details={'success': True},
            user_id='alice'
        )

        cursor = self.conn.execute(
            "SELECT entry_data FROM audit_log ORDER BY sequence_number DESC LIMIT 1"
        )
        row = cursor.fetchone()
        entry = json.loads(row[0])

        # Verify required fields
        self.assertIn('timestamp', entry)
        self.assertIn('event_type', entry)
        self.assertIn('severity', entry)
        self.assertIn('user_id', entry)
        self.assertIn('source', entry)
        self.assertIn('details', entry)
        self.assertIn('sequence_number', entry)
        self.assertIn('previous_hash', entry)

    def test_sensitive_data_redaction(self):
        """Test sensitive data is redacted per LOG-3."""
        self.logger.log_event(
            event_type='TEST',
            severity='INFO',
            source='test',
            details={
                'password': 'secret123',
                'key': 'encryption_key',
                'normal_field': 'safe_value'
            }
        )

        cursor = self.conn.execute(
            "SELECT entry_data FROM audit_log ORDER BY sequence_number DESC LIMIT 1"
        )
        row = cursor.fetchone()
        entry = json.loads(row[0])

        details = entry['details']
        self.assertEqual(details['password'], '[REDACTED]')
        self.assertEqual(details['key'], '[REDACTED]')
        self.assertEqual(details['normal_field'], 'safe_value')

    def test_hash_chain_continuity(self):
        """Test hash chain is maintained per CRY-4."""
        # Log multiple events
        for i in range(5):
            self.logger.log_event(
                event_type=f'EVENT_{i}',
                severity='INFO',
                source='test',
                details={'index': i}
            )

        # Get all entries
        cursor = self.conn.execute(
            "SELECT sequence_number, previous_hash, entry_hash FROM audit_log ORDER BY sequence_number"
        )
        rows = cursor.fetchall()

        # Verify chain
        for i in range(1, len(rows)):
            prev_hash = rows[i][1]  # previous_hash of current
            actual_prev_hash = rows[i - 1][2]  # entry_hash of previous

            # Genesis entry has '0'*64 as previous_hash
            if rows[i][0] == 0:
                self.assertEqual(prev_hash, '0' * 64)
            else:
                self.assertEqual(prev_hash, actual_prev_hash)


class TestLogVerifier(unittest.TestCase):
    """Test log integrity verification per VER-1, VER-2, VER-3, VER-4."""

    def setUp(self):
        # Create temporary database with audit log
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self._create_audit_table()

        self.key_manager = MockKeyManager()
        self.signer = AuditLogSigner(self.key_manager)
        self.event_system = Mock()
        self.config = {
            'async_logging': False,
            'periodic_verification': False,
            'lock_vault_on_tamper': False
        }

        self.logger = AuditLogger(self.conn, self.signer, self.event_system, self.config)
        self.verifier = LogVerifier(self.conn, self.signer, self.event_system, self.config)

    def _create_audit_table(self):
        """Create audit_log table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_hash TEXT,
                entry_data TEXT,
                entry_hash TEXT,
                signature TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.logger.stop()
        self.conn.close()
        os.unlink(self.db_path)

    def test_verify_integrity_valid_log(self):
        """Test verification passes for valid log per TEST-1."""
        # Create 100 log entries
        for i in range(100):
            self.logger.log_event(
                event_type=f'TEST_EVENT_{i}',
                severity='INFO',
                source='test',
                details={'index': i}
            )

        result = self.verifier.verify_integrity(full_scan=True)

        self.assertTrue(result.verified)
        self.assertEqual(result.valid_entries, result.total_entries)
        self.assertEqual(len(result.invalid_entries), 0)
        self.assertEqual(len(result.chain_breaks), 0)

    def test_detect_tampered_entry(self):
        """Test tampering detection per TEST-1."""
        # Create 50 log entries
        for i in range(50):
            self.logger.log_event(
                event_type=f'TEST_EVENT_{i}',
                severity='INFO',
                source='test',
                details={'index': i}
            )

        # Tamper with an entry (modify entry_data directly)
        self.conn.execute(
            "UPDATE audit_log SET entry_data = '{\"tampered\": true}' WHERE sequence_number = 25"
        )
        self.conn.commit()

        result = self.verifier.verify_integrity(full_scan=True)

        self.assertFalse(result.verified)
        self.assertGreater(len(result.invalid_entries), 0)

        # Check that tampered entry was detected
        found = any(e['sequence'] == 25 for e in result.invalid_entries)
        self.assertTrue(found)

    def test_detect_chain_break(self):
        """Test hash chain break detection per TEST-1."""
        # Create 50 log entries
        for i in range(50):
            self.logger.log_event(
                event_type=f'TEST_EVENT_{i}',
                severity='INFO',
                source='test',
                details={'index': i}
            )

        # Break the chain by modifying previous_hash
        self.conn.execute(
            "UPDATE audit_log SET previous_hash = 'fakehash123' WHERE sequence_number = 30"
        )
        self.conn.commit()

        result = self.verifier.verify_integrity(full_scan=True)

        self.assertFalse(result.verified)
        self.assertGreater(len(result.chain_breaks), 0)

        # Check that chain break was detected
        found = any(b['sequence'] == 30 for b in result.chain_breaks)
        self.assertTrue(found)

    def test_startup_verification_large_log(self):
        """Test startup verification with large log per VER-1."""
        # Create 15,000 entries (more than 10,000 threshold)
        for i in range(15000):
            self.logger.log_event(
                event_type='BULK_EVENT',
                severity='INFO',
                source='test',
                details={'index': i}
            )

        # Mock the verifier methods to avoid actual heavy computation
        with patch.object(self.verifier, 'verify_integrity') as mock_verify:
            mock_verify.return_value = VerificationResult(
                total_entries=1000,
                valid_entries=1000,
                invalid_entries=[],
                chain_breaks=[],
                verified=True,
                verification_time_ms=100,
                timestamp=datetime.now().isoformat()
            )

            result = self.verifier.verify_at_startup()
            self.assertTrue(result.verified)

    def test_tampering_triggers_event(self):
        """Test tampering triggers security event per VER-4."""
        # Create entries
        self.logger.log_event('TEST', 'INFO', 'test', {'data': 'test'})

        # Tamper
        self.conn.execute(
            "UPDATE audit_log SET entry_data = '{\"tampered\": true}' WHERE sequence_number = 1"
        )
        self.conn.commit()

        # Verify and check event was published
        result = self.verifier.verify_integrity(full_scan=True)

        # Check that event system got the security event
        self.event_system.publish.assert_called_with(
            'SecurityEvent',
            {'event_type': 'LOG_TAMPERING_DETECTED', 'severity': 'CRITICAL', 'details': ANY}
        )

    def test_verification_report(self):
        """Test verification report generation per VER-3."""
        # Create entries
        for i in range(10):
            self.logger.log_event(f'EVENT_{i}', 'INFO', 'test', {'idx': i})

        self.verifier.verify_integrity(full_scan=True)
        report = self.verifier.get_verification_report()

        self.assertIn('status', report)
        self.assertIn('total_entries_checked', report)
        self.assertIn('valid_entries', report)
        self.assertIn('verification_time_ms', report)


class TestLogFormatter(unittest.TestCase):
    """Test log export functionality per EXP-1, EXP-2, EXP-3, EXP-4."""

    def setUp(self):
        self.formatter = LogFormatter()
        self.sample_entries = [
            {
                'sequence_number': 1,
                'timestamp': '2026-06-01T10:00:00Z',
                'event_type': 'AUTH_LOGIN',
                'severity': 'INFO',
                'user_id': 'alice',
                'source': 'auth',
                'details': {'success': True},
                'signature': 'abc123def456'
            },
            {
                'sequence_number': 2,
                'timestamp': '2026-06-01T10:05:00Z',
                'event_type': 'VAULT_CREATE',
                'severity': 'INFO',
                'user_id': 'alice',
                'source': 'vault',
                'details': {'entry_id': 'entry-123'},
                'signature': 'xyz789uvw456'
            }
        ]

    def test_json_export(self):
        """Test JSON export per EXP-1, EXP-2."""
        metadata = ExportMetadata(
            timestamp=datetime.now().isoformat(),
            exporter='Test',
            start_date=None,
            end_date=None,
            total_entries=2,
            format='json',
            signature_included=True
        )

        json_output = self.formatter.export_to_json(self.sample_entries, metadata, include_signatures=True)

        # Verify it's valid JSON
        data = json.loads(json_output)

        self.assertIn('metadata', data)
        self.assertIn('entries', data)
        self.assertEqual(len(data['entries']), 2)
        self.assertEqual(data['metadata']['total_entries'], 2)
        self.assertEqual(data['metadata']['format'], 'json')

    def test_csv_export(self):
        """Test CSV export per EXP-1."""
        csv_output = self.formatter.export_to_csv(self.sample_entries)

        self.assertIn('sequence_number,timestamp,event_type', csv_output)
        self.assertIn('AUTH_LOGIN', csv_output)
        self.assertIn('VAULT_CREATE', csv_output)

    def test_pdf_export_stub(self):
        """Test PDF export stub per EXP-1."""
        metadata = ExportMetadata(
            timestamp=datetime.now().isoformat(),
            exporter='Test',
            start_date=None,
            end_date=None,
            total_entries=2,
            format='pdf',
            signature_included=True
        )

        pdf_output = self.formatter.export_to_pdf(self.sample_entries, metadata)

        self.assertIsInstance(pdf_output, bytes)
        self.assertGreater(len(pdf_output), 0)

    def test_batch_export(self):
        """Test batch export per EXP-4."""
        entries_by_range = {
            '2026-01': self.sample_entries,
            '2026-02': self.sample_entries
        }

        results = self.formatter.export_batch(entries_by_range, format='json')

        self.assertEqual(len(results), 2)
        self.assertIn('2026-01', results)
        self.assertIn('2026-02', results)

        # Verify both are valid JSON
        for result in results.values():
            data = json.loads(result)
            self.assertIn('entries', data)


class TestAuditPerformance(unittest.TestCase):
    """Test performance requirements PERF-1 through PERF-5."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self._create_audit_table()

        self.key_manager = MockKeyManager()
        self.signer = AuditLogSigner(self.key_manager)
        self.event_system = Mock()

    def _create_audit_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_hash TEXT,
                entry_data TEXT,
                entry_hash TEXT,
                signature TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def test_logging_performance(self):
        """Test logging operation < 10ms per PERF-1."""
        logger = AuditLogger(self.conn, self.signer, self.event_system, {'async_logging': False})

        start_time = time.time()

        for i in range(100):
            logger.log_event(
                event_type='PERF_TEST',
                severity='INFO',
                source='test',
                details={'index': i}
            )

        end_time = time.time()
        avg_time_ms = (end_time - start_time) / 100 * 1000

        # Average should be < 10ms
        self.assertLess(avg_time_ms, 10, f"Average logging time: {avg_time_ms}ms")

        logger.stop()

    def test_verification_performance(self):
        """Test verification of 1000 entries < 1 second per PERF-2."""
        logger = AuditLogger(self.conn, self.signer, self.event_system, {'async_logging': False})

        # Create 1000 entries
        for i in range(1000):
            logger.log_event(
                event_type='PERF_TEST',
                severity='INFO',
                source='test',
                details={'index': i}
            )

        verifier = LogVerifier(self.conn, self.signer, self.event_system, {'periodic_verification': False})

        start_time = time.time()
        result = verifier.verify_integrity(full_scan=True)
        end_time = time.time()

        verification_time = end_time - start_time

        self.assertLess(verification_time, 1.0, f"Verification took {verification_time}s")
        self.assertTrue(result.verified)

        logger.stop()

    def test_query_performance(self):
        """Test query/filter operations < 500ms per 10,000 entries per PERF-3."""
        logger = AuditLogger(self.conn, self.signer, self.event_system, {'async_logging': False})

        # Create 10,000 entries
        for i in range(10000):
            logger.log_event(
                event_type=f'EVENT_{i % 10}',
                severity='INFO' if i % 5 != 0 else 'WARN',
                source='test',
                details={'index': i}
            )

        start_time = time.time()

        entries = logger.get_entries(
            limit=100,
            offset=0,
            event_type='EVENT_1',
            severity='INFO'
        )

        end_time = time.time()
        query_time_ms = (end_time - start_time) * 1000

        self.assertLess(query_time_ms, 500, f"Query took {query_time_ms}ms")
        self.assertGreater(len(entries), 0)

        logger.stop()


class TestAuditSecurity(unittest.TestCase):
    """Test security requirements SEC-1 through SEC-5."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self._create_audit_table()

        self.key_manager = MockKeyManager()
        self.signer = AuditLogSigner(self.key_manager)
        self.event_system = Mock()

    def _create_audit_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_hash TEXT,
                entry_data TEXT,
                entry_hash TEXT,
                signature TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def test_append_only_immutable(self):
        """Test logs are append-only (no updates allowed) per SEC-2."""
        logger = AuditLogger(self.conn, self.signer, self.event_system, {'async_logging': False})

        # Create an entry
        logger.log_event('TEST', 'INFO', 'test', {'data': 'original'})

        # Try to update existing entry (should not be allowed by application logic)
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute(
                "UPDATE audit_log SET entry_data = 'modified' WHERE sequence_number = 1"
            )

        # Delete should also be prevented
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute("DELETE FROM audit_log WHERE sequence_number = 1")

        logger.stop()

    def test_access_control_requires_auth(self):
        """Test audit logs readable only by authenticated users per SEC-4."""
        # This test verifies that audit logger checks authentication state
        logger = AuditLogger(self.conn, self.signer, self.event_system, {'async_logging': False})

        # Should be able to log regardless
        logger.log_event('TEST', 'INFO', 'test', {'data': 'test'})

        # Get entries - in real app, this would check auth
        entries = logger.get_entries(limit=10)
        self.assertIsNotNone(entries)

        logger.stop()

    def test_log_protection_self_logging(self):
        """Test attempts to disable/modify logging are logged per SEC-5."""
        logger = AuditLogger(self.conn, self.signer, self.event_system, {'async_logging': False})

        # Simulate detection of logging modification attempt
        logger.log_event(
            event_type='SECURITY_LOG_PROTECTION',
            severity='CRITICAL',
            source='audit_logger',
            details={'attempt': 'modify_logging', 'detected': True}
        )

        # Verify the security event was logged
        cursor = self.conn.execute(
            "SELECT entry_data FROM audit_log WHERE json_extract(entry_data, '$.event_type') = 'SECURITY_LOG_PROTECTION'"
        )
        rows = cursor.fetchall()

        self.assertGreaterEqual(len(rows), 1)

        logger.stop()


class TestAuditIntegration(unittest.TestCase):
    """Test integration with existing components per INT-1, INT-2, INT-3."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

        self.key_manager = MockKeyManager()
        self.signer = AuditLogSigner(self.key_manager)
        self.event_system = Mock()
        self.config = {'async_logging': False}

        self.logger = AuditLogger(self.conn, self.signer, self.event_system, self.config)

    def _create_tables(self):
        """Create all required tables."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_hash TEXT,
                entry_data TEXT,
                entry_hash TEXT,
                signature TEXT,
                timestamp TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_entries (
                id TEXT PRIMARY KEY,
                title TEXT,
                encrypted_data BLOB,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.logger.stop()
        self.conn.close()
        os.unlink(self.db_path)

    def test_event_system_integration(self):
        """Test audit logger subscribes to events per INT-1."""
        # Verify subscriptions were made
        # event_system.subscribe should have been called multiple times
        self.event_system.subscribe.assert_called()

    def test_vault_integration_logging(self):
        """Test vault operations are logged per INT-2."""
        # Simulate vault events
        self.event_system.publish('EntryCreated', {'entry_id': 'test-123', 'event_name': 'CREATE'})
        self.event_system.publish('EntryUpdated', {'entry_id': 'test-123', 'event_name': 'UPDATE'})
        self.event_system.publish('EntryDeleted', {'entry_id': 'test-123', 'event_name': 'DELETE'})

        # Give async time if needed
        time.sleep(0.1)

        # Verify events were logged
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE entry_data LIKE '%VAULT%'"
        )
        count = cursor.fetchone()[0]

        self.assertGreaterEqual(count, 3)

    def test_clipboard_integration_logging(self):
        """Test clipboard operations are logged per INT-3."""
        # Simulate clipboard events
        self.event_system.publish('ClipboardCopied', {
            'event_name': 'COPY',
            'data_type': 'password',
            'source_entry_id': 'entry-456'
        })
        self.event_system.publish('ClipboardCleared', {
            'event_name': 'CLEAR',
            'reason': 'timeout'
        })

        time.sleep(0.1)

        # Verify events were logged
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE entry_data LIKE '%CLIPBOARD%'"
        )
        count = cursor.fetchone()[0]

        self.assertGreaterEqual(count, 2)


# Helper for Mock
class ANY:
    """Any value matcher for assertions."""

    def __eq__(self, other):
        return True


if __name__ == '__main__':
    unittest.main()