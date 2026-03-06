import unittest
import os
import tempfile
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.core.config import Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        # Временная папка для тестов
        self.temp_dir = tempfile.mkdtemp()
        # Сохраняем старый путь
        self.old_config = Config()

    def test_config_set_get(self):
        config = Config()
        config.set("theme", "dark")
        self.assertEqual(config.get("theme"), "dark")
        print("✅ Тест set/get прошел")

    def test_config_default(self):
        config = Config()
        self.assertEqual(config.get("not_exists", "default"), "default")
        print("✅ Тест default значения прошел")


if __name__ == '__main__':
    unittest.main()