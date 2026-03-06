import unittest
import os
import tempfile
import tkinter as tk
from src.database.db import Database
from src.core.config import config
from src.gui.setup_wizard import SetupWizard
from src.gui.main_window import MainWindow


class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Временная БД для тестов
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test.db")
        config.set("db_path", self.test_db)

    def test_first_run_setup(self):
        """Тест мастера настройки"""
        root = tk.Tk()
        root.withdraw()

        setup_called = False

        def on_setup_complete():
            nonlocal setup_called
            setup_called = True

        wizard = SetupWizard(root, on_setup_complete)

        # Проверяем что визард создался
        self.assertIsNotNone(wizard)

    def test_config_loading(self):
        """Тест загрузки конфига"""
        self.assertEqual(config.get("db_path"), self.test_db)
        config.set("theme", "dark")
        self.assertEqual(config.get("theme"), "dark")

    def tearDown(self):
        # Чистим за собой
        import shutil
        shutil.rmtree(self.temp_dir)


if __name__ == '__main__':
    unittest.main()