import unittest
import os
from src.database.db import Database

class TestDatabase(unittest.TestCase):
    def test_connection(self):
        db = Database()
        db.db_path = os.path.join(os.path.dirname(__file__), "test_temp.db")
        db.connect()
        self.assertIsNotNone(db.conn)
        db.close()
        if os.path.exists(db.db_path):
            os.remove(db.db_path)

if __name__ == '__main__':
    unittest.main()