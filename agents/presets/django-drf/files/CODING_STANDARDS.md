# 📏 Стандарты кодирования: Django + DRF (пресет django-drf)

> Стек: Python 3.11+ · Django 5.x · DRF · Celery · Redis · PostgreSQL · JWT (djangorestframework-simplejwt)

## 1. Структура проекта
- Каждый Django-app — низкосвязанный модуль: `models/`, `serializers/`, `views/`, `services/`, `tests/`, `urls.py`.
- Бизнес-логика — в `services/` (функции или классы), НЕ в view и НЕ в serializers. View — тонкая обработка HTTP, serializer — валидация/сериализация.
- Настройки — `config/settings/{base,dev,prod}.py`; секреты только из окружения (`django-environ`), в репо — только `.env.example`.

## 2. Модели и БД
- `AUTH_USER_MODEL` задаётся при старте проекта; миграции не редактируются задним числом — только новые.
- `ForeignKey` всегда с явными `on_delete` и `related_name`.
- Индексы под реальные запросы (`Meta.indexes` / `Meta.constraints`), `select_related`/`prefetch_related` против N+1.
- Тяжёлые выборки — через итераторы (`iterator()`) или пагинацию.

## 3. API (DRF)
- ViewSets + Router; разрешения явные на каждом view (`IsAuthenticated` и кастомные), perms_or_deny по умолчанию.
- Сериализаторы не отдают полей, которым не место наружу (.ModelSerializer: `fields` явно, не `__all__` в публичных API).
- Пагинация обязательна для списков; фильтрация — `django-filter`.
- Ошибки: единый формат через exception handler; статусы корректные (400/401/403/404/409).

## 4. Celery и асинхронность
- Всё, что дольше ~1 секунды или ходит в внешние API, — в задачу Celery.
- Идемпотентность задач обязательна (`acks_late=True`, повтор при сбое); никаких side-effect без retry-политики.
- Таймауты и retry — явно в декораторе задачи; брокер — Redis.

## 5. Тесты (pytest-django)
- Уровни: `services` unit (без БД через transactions/моки), API через `APIClient`, редкие e2e.
- Фикстуры — `pytest.fixture`; фабрики — `factory_boy`, не голые `Model.objects.create` в 20 местах.
- Каждый новый эндпоинт/сервис приходит с тестами; покрытие критичного пути — 100%.

## 6. Безопасность
- Никаких секретов в коде; `DEBUG=False` в проде; `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` из окружения.
- CORS/CSRF — whitelist, не `*`. Загрузки файлов — валидация типа и размера.
- SQL — только ORM/параметризованные запросы; `raw()` — только с обоснованием и параметрами.
- JWT: короткий access (15 мин), refresh в httpOnly cookie для веб-клиентов.

## 7. Производительность и деплой
- Кэш Redis для дорогих вычислений (`cache.set` с явным TTL), миграции — отдельным шагом деплоя.
- `django-storages` для S3-совместимого хранения; логирование в stdout (12-factor), структурированные логи.
- Health-check эндпоинт для оркестратора.
