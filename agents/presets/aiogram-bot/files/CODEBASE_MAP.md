# 🗺️ Карта кодовой базы: aiogram-бот (пресет aiogram-bot)

```
.
├── bot/                           # 🤖 Источник бота
│   ├── config.py                  # Настройки (pydantic-settings, из окружения)
│   ├── main.py                    # Точка входа: bot + dispatcher + роутеры
│   ├── handlers/                  # Рouter'ы по фичам
│   │   ├── start.py               # /start, регистрация
│   │   └── <feature>.py           # Фича-роутер
│   ├── keyboards/                 # Сборка клавиатур
│   ├── middlewares/               # DI, rate limit, error handling, logging
│   ├── services/                  # 💼 Бизнес-логика (API-клиенты, фоновые операции)
│   ├── db/                        # SQLAlchemy 2.0 async: models, DAO, session
│   ├── texts.py                   # Пользовательские строки
│   └── utils/                     # Хелперы
├── alembic/                       # 🗄️ Миграции БД
├── tests/                         # Unit-тесты хендлеров и сервисов
├── docker-compose.yml             # 🐳 bot + postgres + redis
├── .env.example                   # 📋 Шаблон окружения
└── agents/                        # 🧠 Second Brain
```

## Карта фич (заполни после генерации)
| Фича | Роутер | FSM-состояние | Сервис |
|---|---|---|---|
| Регистрация | `handlers/start.py` | `Registration:wait_name` | `services/users.py` |

## Интеграции
- **Redis:** FSM-хранилище + rate limit.
- **Celery:** уведомления, парсинг, рассылки (скилл `celery-task`).
- **Внешние API:** *перечисли клиенты в `services/`*.
