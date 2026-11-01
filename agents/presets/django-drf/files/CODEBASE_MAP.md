# 🗺️ Карта кодовой базы: Django + DRF (пресет django-drf)

> Опиши фактическую структуру проекта после генерации скелета. Секция обновляется субагентом docs-keeper.

```
.
├── config/                        # 🛠️ Точка входа Django
│   ├── settings/
│   │   ├── base.py                # Базовые настройки
│   │   ├── dev.py                 # Локальная разработка
│   │   └── prod.py                # Прод (секреты из окружения)
│   ├── urls.py                    # Корневой роутинг
│   ├── celery.py                  # Celery-приложение (autodiscover_tasks)
│   └── wsgi.py / asgi.py
├── apps/                          # 📦 Django-приложения (по доменам)
│   └── <app>/
│       ├── models.py              # Модели БД
│       ├── serializers.py         # DRF-сериализаторы
│       ├── views.py / viewsets.py # HTTP-слой (тонкий)
│       ├── services.py            # 💼 Бизнес-логика (главное место правок)
│       ├── permissions.py         # Кастомные разрешения
│       ├── urls.py                # Роутинг приложения
│       └── tests/                 # pytest-django (unit + API)
├── docker-compose.yml             # 🐳 postgres + redis + web + celery-worker
├── .env.example                   # 📋 Шаблон переменных окружения
└── agents/                        # 🧠 Second Brain (память и регламенты)
```

## Карта доменов (заполни после генерации)
| Модуль | Ответственность | Ключевые файлы |
|---|---|---|
| `apps/users` | Аутентификация, JWT, профиль | `models.py`, `views.py` |
| `apps/<domain>` | *опиши домен* | *файлы* |

## Точки интеграций
- **Celery:** `config/celery.py`, задачи лежат в `apps/<app>/tasks.py`.
- **Redis:** кэш (`CACHES`) + брокер Celery.
- **Внешние API:** *перечисли клиентские модули*.
