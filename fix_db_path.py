import json
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data')
config_file = os.path.join(data_dir, 'config.json')
correct_db_path = os.path.join(data_dir, 'vault.db')

print(f"Base dir: {base_dir}")
print(f"Config file: {config_file}")
print(f"Correct DB path: {correct_db_path}")

# Создаём папку data если нет
os.makedirs(data_dir, exist_ok=True)

# Загружаем или создаём конфиг
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config_data = json.load(f)
else:
    config_data = {}

# Исправляем путь
config_data['db_path'] = correct_db_path

# Сохраняем
with open(config_file, 'w') as f:
    json.dump(config_data, f, indent=2)

print(f"\nConfig saved with correct db_path: {correct_db_path}")

# Проверяем что БД существует
if os.path.exists(correct_db_path):
    print(f"\nDatabase exists at: {correct_db_path}")

    import sqlite3

    conn = sqlite3.connect(correct_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, username FROM vault_entries")
    rows = cursor.fetchall()
    print(f"Entries in correct DB: {len(rows)}")
    for row in rows:
        print(f"  ID: {row[0]}, Title: {row[1]}")
    conn.close()
else:
    print(f"\nDatabase NOT found at: {correct_db_path}")
    print("You need to run setup wizard first to create master password")