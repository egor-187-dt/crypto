import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.core.state_manager import StateManager


class TestState(unittest.TestCase):
    def setUp(self):
        self.state = StateManager()

    def test_login_logout(self):
        self.state.login()
        self.assertTrue(self.state.is_logged_in)
        self.state.logout()
        self.assertFalse(self.state.is_logged_in)
        print("Тест login/logout прошел")

    def test_lock_unlock(self):
        self.state.login()
        self.state.lock()
        self.assertTrue(self.state.is_locked)
        self.state.unlock("pass")
        self.assertFalse(self.state.is_locked)
        print("Тест lock/unlock прошел")

    def test_initial_state(self):
        self.assertFalse(self.state.is_logged_in)
        self.assertFalse(self.state.is_locked)
        self.assertIsNone(self.state.clipboard_timer)
        print("Тест начального состояния прошел")


if __name__ == '__main__':
    unittest.main()