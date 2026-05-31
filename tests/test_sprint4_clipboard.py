"""
Sprint 4 clipboard tests
Implements TEST-1, TEST-2, TEST-3, TEST-4, TEST-5 from requirements
"""
import unittest
import time
import threading
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.clipboard.clipboard_service import ClipboardService
from src.core.clipboard.secure_memory import SecureClipboardItem


class MockConfig:
    def __init__(self):
        self.data = {
            'clipboard_timeout': 30,
            'clipboard_notifications': True,
            'clipboard_security_level': 'basic',
            'clipboard_accelerate_on_access': False,
            'clipboard_preset': 'standard'
        }

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


class TestSprint4Clipboard(unittest.TestCase):

    def setUp(self):
        mock_config = MockConfig()
        self.service = ClipboardService(mock_config)
        self.service.is_vault_unlocked = True

    def tearDown(self):
        self.service.shutdown()

    def test_1_auto_clear_timing(self):
        test_data = "test_password_123"
        timeout = 2

        self.service.set_timeout(timeout)
        result = self.service.copy_to_clipboard(test_data, "password", 1)

        self.assertTrue(result)

        status = self.service.get_status()
        self.assertTrue(status['active'])

        time.sleep(timeout + 0.2)

        status = self.service.get_status()
        self.assertFalse(status['active'])

    def test_2_secure_memory_obfuscation(self):
        test_data = "SuperSecretPassword123"

        item = SecureClipboardItem(test_data, "password", 1)
        obfuscated = item._obfuscated_data

        self.assertNotIn(test_data.encode('utf-8'), obfuscated)

        recovered = item.get_plaintext()
        self.assertEqual(recovered, test_data)

        item.secure_wipe()

    def test_3_concurrent_copy_operations(self):
        test_data_list = ["pass1", "pass2", "pass3", "pass4", "pass5"]

        def copy_operation(data):
            self.service.copy_to_clipboard(data, "password", 1)

        threads = []
        for data in test_data_list:
            t = threading.Thread(target=copy_operation, args=(data,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertIsNotNone(self.service.current_item)

    def test_4_clipboard_clear_on_shutdown(self):
        test_data = "sensitive_data_123"

        self.service.copy_to_clipboard(test_data, "password", 1)
        self.assertTrue(self.service.get_status()['active'])

        self.service.shutdown()

        mock_config = MockConfig()
        new_service = ClipboardService(mock_config)
        new_service.is_vault_unlocked = True

        status = new_service.get_status()
        self.assertFalse(status['active'])

        new_service.shutdown()

    def test_5_preset_profiles(self):
        self.service.apply_preset('standard')
        self.assertEqual(self.service.timeout_seconds, 30)
        self.assertTrue(self.service.notifications_enabled)

        self.service.apply_preset('secure')
        self.assertEqual(self.service.timeout_seconds, 15)
        self.assertTrue(self.service.accelerate_on_access)

        self.service.apply_preset('public_computer')
        self.assertEqual(self.service.timeout_seconds, 5)

    def test_6_never_auto_clear(self):
        self.service.set_timeout(0)

        test_data = "persistent_data"
        self.service.copy_to_clipboard(test_data, "password", 1)

        time.sleep(2)

        status = self.service.get_status()
        self.assertTrue(status['active'])

        self.service.clear_clipboard()
        status = self.service.get_status()
        self.assertFalse(status['active'])


if __name__ == '__main__':
    unittest.main()