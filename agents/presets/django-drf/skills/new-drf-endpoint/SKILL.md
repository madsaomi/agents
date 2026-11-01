---
name: new-drf-endpoint
description: Пошаговое добавление нового REST-эндпоинта в Django DRF: модель → сериализатор → viewset → urls → тесты.
---

# 🔌 Новый DRF-эндпоинт

## Порядок (Plan-First: сначала план в `agents/plans/`)
1. **Модель/данные:** есть ли нужная модель? Новая модель → миграция (см. скилл `db-migration`).
2. **Сериализатор** `apps/<app>/serializers.py`:
   - `fields` явно (никогда `__all__` в публичном API);
   - кастомные `validate_<field>`/`validate` для бизнес-правил.
3. **ViewSet** `apps/<app>/viewsets.py`:
   - наследуй `ModelViewSet`/`ReadOnlyModelViewSet`;
   - `permission_classes` — явно на каждом классе;
   - тяжёлая логика — в `services/`, не в `perform_create`-теле;
   - пагинация из настроек (не кастомная на каждый эндпоинт).
4. **Роутинг** `apps/<app>/urls.py` через `DefaultRouter`, подключение в `config/urls.py`.
5. **Фильтры:** `filterset_fields` через django-filter для списков.
6. **Тесты** `apps/<app>/tests/test_<name>.py` (pytest-django + APIClient):
   - happy-path (создание/чтение/обновление);
   - права: аноним → 401, чужой объект → 403/404;
   - валидация: неверные данные → 400 и понятная ошибка.
7. **Проверка:** `pytest`, `ruff`, `black`; обнови `agents/architecture/CODEBASE_MAP.md`.

## Антипаттерны
- ❌ Бизнес-логика в view/serializer.
- ❌ `__all__` наружу, отдача `password`/`internal_*` полей.
- ❌ Эндпоинт без тестов и явных разрешений.
