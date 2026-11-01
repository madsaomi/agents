# 🗺️ Карта кодовой базы: FastAPI (пресет fastapi)

```
.
├── app/
│   ├── main.py                    # create_app(), подключение роутеров/middleware
│   ├── api/                       # 🌐 Роутеры (тонкие)
│   │   └── v1/<resource>.py
│   ├── core/
│   │   ├── config.py              # Настройки (pydantic-settings)
│   │   ├── db.py                  # engine, async sessionmaker
│   │   ├── security.py            # JWT, хеши паролей
│   │   └── exceptions.py          # Domain-исключения → HTTP
│   ├── schemas/                   # Pydantic v2: request/response
│   ├── models/                    # SQLAlchemy 2.0 models
│   ├── repositories/              # Доступ к БД
│   ├── services/                  # 💼 Бизнес-логика
│   └── deps.py                    # Зависимости (get_session, get_current_user)
├── tests/                         # pytest (unit + API + интеграции)
├── alembic/                       # Миграции
├── .env.example
└── agents/                        # 🧠 Second Brain
```

## Карта ресурсов (заполни после генерации)
| Ресурс | Роутер | Сервис | Репозиторий |
|---|---|---|---|
| users | `api/v1/users.py` | `services/users.py` | `repositories/users.py` |
