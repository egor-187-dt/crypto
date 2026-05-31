# CryptoSafe Manager

Менеджер паролей с безопасным шифрованием. Хранит пароли в зашифрованном виде с мастер-паролем.

## Sprint 1 (Базовая функциональность)

- Архитектура MVC, система событий (EventBus)
- SQLite база данных с миграциями и таблицами: vault_entries, audit_log, settings, key_store
- Модуль конфигурации (config.py) с сохранением в JSON
- Базовый GUI с главным окном, меню (Файл, Безопасность, Помощь), таблицей и статус-баром
- Компоненты: PasswordEntry, SecureTable, AuditLogViewer
- Мастер первого запуска для создания мастер-пароля
- Заглушка шифрования (XOR для тестов)
- KeyManager заглушка для управления ключами
- Система событий: EntryAdded, EntryUpdated, EntryDeleted, UserLoggedIn, UserLoggedOut, ClipboardCopied, ClipboardCleared
- Безопасность: отсутствие хардкода, валидация ввода, минимальные привилегии
- Тестовая среда: unit-тесты для БД, криптографии, событий

## Sprint 2 (Аутентификация и управление ключами)

- Argon2id для хеширования мастер-пароля (t=3, m=65536, p=4)
- PBKDF2-HMAC-SHA256 для вывода ключа шифрования (100,000 итераций)
- Соли для каждого пользователя (16 байт)
- Два отдельных ключа: аутентификационный (хранится) и шифрования (выводится на лету)
- PasswordValidator: проверка длины (минимум 12 символов), наличие заглавных/строчных букв, цифр, спецсимволов, проверка на распространенные пароли
- Защита от брутфорса: экспоненциальные задержки (1с, 5с, 30с), блокировка на 30 секунд после 5 неудачных попыток
- Управление сессиями: отслеживание времени входа, последней активности, счетчика неудачных попыток
- Безопасная очистка ключей из памяти с затиранием
- Блокировка страниц памяти (VirtualLock на Windows, mlock на Linux)
- Автоблокировка при неактивности (60 минут, настраивается)
- Смена мастер-пароля с перешифровкой всех записей в фоне, атомарный откат при ошибке
- OS Keychain интеграция через библиотеку keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- Кэширование ключа в памяти с таймаутом (60 минут)
- Диалог входа с защитой от брутфорса, отображением задержек и блокировки
- Кнопка блокировки и разблокировки хранилища
- Миграция БД без потери данных (версии 2, 3, 4)
- Таблица key_store: key_type, key_data, version, created_at
- Тесты: Argon2 параметры, PBKDF2 консистентность, очистка ключей, задержки входа, блокировка, валидатор паролей, смена пароля с перешифровкой

## Sprint 3 (AES-256-GCM шифрование и CRUD операции)

- AES-256-GCM шифрование через cryptography.hazmat.primitives.ciphers.aead.AESGCM
- Уникальный 12-байтовый nonce для каждой записи (os.urandom)
- Формат хранения: nonce (12B) + ciphertext + tag (16B) как единый BLOB
- Проверка тега аутентификации при расшифровке (защита от взлома)
- Шифрование всех полей записи: title, username, password, url, notes, tags
- Модель записи: id, encrypted_data, created_at, updated_at, deleted, deleted_at, tags
- Полная структура plaintext с version для будущей совместимости
- EntryManager с методами: create_entry, get_entry, get_all_entries, update_entry, delete_entry (soft/hard)
- Транзакционность операций с rollback при ошибке
- Публикация событий: EntryCreated, EntryUpdated, EntryDeleted
- Генератор паролей на secrets.choice(): длина 8-64, наборы символов, исключение неоднозначных символов (l, I, 1, 0, O)
- Гарантия минимум одного символа из каждого выбранного набора
- Проверка сложности пароля (score от 1 до 5, weak/medium/strong)
- История последних 20 паролей, предотвращение повторов
- Таблица с колонками: ID, Название, Логин (маскировка первых 4 символов + ****), URL, Обновлено
- Сортировка колонок, изменение размеров, контекстное меню (правый клик)
- Диалог создания/редактирования записи с полной формой
- Поле для ввода с кнопкой генерации пароля и конфигурацией
- Индикатор сложности пароля
- Поиск в реальном времени по title, username, url, notes (fuzzy matching)
- Индексы БД на created_at, updated_at, deleted
- Загрузка 1000 записей < 2 секунд, поиск < 200 мс, память < 50 МБ
- Расшифрованные записи хранятся в памяти только во время отображения
- Тесты: round-trip шифрования, CRUD интеграционный, генератора паролей (10,000 без повторов)

## Sprint 4 (Безопасный буфер обмена)

- Модуль src/core/clipboard/ с файлами: clipboard_service.py, platform_adapter.py, clipboard_monitor.py, secure_memory.py
- Observer pattern через события: clipboard_copied, clipboard_cleared, clipboard_notification, clipboard_error
- Поддержка типов данных: password, username, note, totp
- Автоочистка буфера с настраиваемым таймером (5-300 секунд)
- Опция "never auto-clear" (0 секунд) - не рекомендуется
- Настройки сохраняются в config.json и шифрованной таблице settings
- Очистка буфера: по таймеру, вручную (кнопка Clear), при блокировке хранилища, при копировании новых данных
- Windows: win32clipboard с EmptyClipboard() и CF_UNICODETEXT
- Fallback на pyperclip для кроссплатформенной совместимости
- Мониторинг буфера через WM_DRAWCLIPBOARD (Windows) для обнаружения внешнего доступа и изменений
- Ускоренная очистка при подозрительной активности (множественные изменения)
- Отсутствие хранения истории буфера
- XOR обфускация данных в памяти с случайной маской (64 байта)
- Блокировка страниц памяти (VirtualLock/mlock)
- Очистка буфера при vault_locked (событие)
- Проверка is_vault_unlocked перед любой операцией копирования
- Контекстное меню по правому клику на записи: Копировать пароль, Копировать логин, Редактировать, Удалить
- Статус-бар с отображением: тип данных в буфере, таймер обратного отсчета (обновление каждые 500 мс)
- Нотификации при копировании и очистке через события
- Статус-бар буфера обмена с кнопкой Clear
- Вкладка "Буфер обмена" в настройках:
  - Spinbox для таймера автоочистки (5-300 сек, 0 = никогда)
  - Пресеты: Standard (30с), Secure (15с), Public Computer (5с)
  - Combobox уровня безопасности: basic (30с), advanced (15с), paranoid (5с)
  - Чекбокс "Показывать уведомления"
  - Чекбокс "Ускорять очистку при подозрительной активности"
  - Отображение текущего состояния буфера
- Интеграция с EntryManager: получение дешифрованных паролей и логинов
- Интеграция с vault: очистка буфера при блокировке хранилища (SEC-3)
- Производительность: копирование < 100 мс, мониторинг < 1% CPU, память < 10 МБ
- Обработка ошибок: fallback на pyperclip, предупреждение при невозможности очистки, graceful degradation мониторинга, логирование ошибок через события

## Установка и запуск

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/cryptosafe-manager.git
cd cryptosafe-manager

# Создание виртуального окружения
python -m venv .venv

# Активация (Windows)
.venv\Scripts\activate

# Активация (Linux/MacOS)
# source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python main.py
cryptosafe-manager/
├── src/
│   ├── core/
│   │   ├── clipboard/
│   │   │   ├── __init__.py
│   │   │   ├── clipboard_service.py
│   │   │   ├── clipboard_monitor.py
│   │   │   ├── platform_adapter.py
│   │   │   └── secure_memory.py
│   │   ├── crypto/
│   │   │   ├── __init__.py
│   │   │   ├── abstract.py
│   │   │   ├── aes_gcm.py
│   │   │   ├── authentication.py
│   │   │   ├── key_derivation.py
│   │   │   ├── key_storage.py
│   │   │   ├── password_validator.py
│   │   │   └── placeholder.py
│   │   ├── vault/
│   │   │   ├── __init__.py
│   │   │   ├── encryption_service.py
│   │   │   ├── entry_manager.py
│   │   │   └── password_generator.py
│   │   ├── config.py
│   │   ├── events.py
│   │   ├── key_manager.py
│   │   └── state_manager.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── migration.py
│   │   └── models.py
│   ├── gui/
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── audit_log_viewer.py
│   │   │   ├── clipboard_statusbar.py
│   │   │   ├── password_entry.py
│   │   │   └── secure_table.py
│   │   ├── __init__.py
│   │   ├── change_password_dialog.py
│   │   ├── entry_dialog.py
│   │   ├── login_dialog.py
│   │   ├── main_window.py
│   │   ├── settings_dialog.py
│   │   └── setup_wizard.py
│   └── __init__.py
├── data/
│   ├── vault.db
│   └── config.json
├── tests/
│   ├── __init__.py
│   ├── fixtures.py
│   ├── test_config.py
│   ├── test_crypto.py
│   ├── test_database.py
│   ├── test_events.py
│   ├── test_imports.py
│   ├── test_integration.py
│   ├── test_sprint2.py
│   ├── test_sprint2_complete.py
│   ├── test_sprint3.py
│   ├── test_sprint4_clipboard.py
│   └── test_state.py
├── main.py
├── requirements.txt
└── README.md