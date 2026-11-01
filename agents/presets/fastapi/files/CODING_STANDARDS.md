# 📏 Стандарты кодирования: FastAPI (пресет fastapi)

> Стек: Python 3.11+ · FastAPI · SQLAlchemy 2.0 (async) · Pydantic v2 · PostgreSQL · Redis

## 1. Структура
- Слои: `app/api/` (роутеры, тонкие) → `app/services/` (бизнес-логика) → `app/repositories/` (ДОСТУП к БД) → `app/models/` (SQLAlchemy).
- Схемы Pydantic — в `app/schemas/`, отдельно request/response; никогда не отдавать ORM-модели напрямую.
- Конфигурация — `app/core/config.py` (pydantic-settings), секреты только из окружения.

## 2. Асинхронность
- Все DB-операции — async (asyncpg); `async def` в роутерах осмыслен (ждёт IO), не для чистых вычислений.
- Внешние HTTP-клиены — httpx.AsyncClient, с таймаутами.
- CPU-тяжёлое — в фоновые задачи (BackgroundTasks / Celery / ARQ).

## 3. API
- Типизация всего: параметры, возвраты (`response_model`), ошибки (кастомные HTTPException с единым форматом).
- Валидация — в схемах Pydantic, бизнес-правила — в services (кидают domain-исключения → маппинг в HTTP).
- Пагинация для списков; OpenAPI-описания понятные (summary, description, tags).

## 4. Безопасность
- Секретов в коде нет; JWT — короткий access + refresh (httpOnly).
- Права: dependencies с проверкой доступа к объекту (404, не 403, для чужих объектов).
- Rate limit на эндпоинты через Redis.

## 5. Тесты (pytest + httpx.AsyncClient + testcontainers/postgres)
- Уровни: services unit, API-тесты через `TestClient`/ASGI, интеграции — с реальной PostgreSQL в CI.
- Каждый новый эндпоинт — с тестами (happy path, 401, 404, валидация 400).
