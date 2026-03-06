import unittest
from src.core.events import events


class TestEvents(unittest.TestCase):
    def setUp(self):
        # Очищаем подписчиков перед каждым тестом
        events._subscribers = {}

    def test_event_publish_subscribe(self):
        received_data = None

        def callback(data):
            nonlocal received_data
            received_data = data

        # Подписываемся
        events.subscribe("test_event", callback)

        # Публикуем событие
        test_data = {"message": "hello", "value": 42}
        events.publish("test_event", test_data)

        # Проверяем что данные пришли
        self.assertEqual(received_data, test_data)
        print("✅ Тест подписки/публикации прошел")

    def test_multiple_subscribers(self):
        count1 = 0
        count2 = 0

        def callback1(data):
            nonlocal count1
            count1 += 1

        def callback2(data):
            nonlocal count2
            count2 += 1

        # Два подписчика на одно событие
        events.subscribe("multi_event", callback1)
        events.subscribe("multi_event", callback2)

        # Публикуем 3 раза
        for i in range(3):
            events.publish("multi_event", i)

        # Оба должны получить 3 события
        self.assertEqual(count1, 3)
        self.assertEqual(count2, 3)
        print("✅ Тест нескольких подписчиков прошел")

    def test_different_events(self):
        result1 = None
        result2 = None

        def callback1(data):
            nonlocal result1
            result1 = data

        def callback2(data):
            nonlocal result2
            result2 = data

        # Подписываемся на разные события
        events.subscribe("event1", callback1)
        events.subscribe("event2", callback2)

        # Публикуем только первое событие
        events.publish("event1", "data for event1")

        # Второе событие не должно прийти
        self.assertEqual(result1, "data for event1")
        self.assertIsNone(result2)
        print("✅ Тест разных событий прошел")


if __name__ == '__main__':
    unittest.main()