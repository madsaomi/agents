---
name: fastapi-endpoint
description: Пошаговое добавление нового эндпоинта в FastAPI: схемы → роутер → сервис → репозиторий → тесты.
---

# 🔌 Новый эндпоинт (FastAPI)

## Порядок (Plan-First: сначала план в `agents/plans/`)
1. **Схемы** `app/schemas/<resource>.py`: `<Name>Create`, `<Name>Read`, `<Name>List` (отдельно request/response).
2. **Репозиторий** `app/repositories/<resource>.py`: async-запросы через сессию из DI.
3. **Сервис** `app/services/<resource>.py`: бизнес-логика, domain-исключения.
4. **Роутер** `app/api/v1/<resource>.py`:
   ```python
   @router.post("/", response_model=ItemRead, status_code=201)
   async def create_item(payload: ItemCreate, session: AsyncSession = Depends(get_session)):
       return await items_service.create(session, payload)
   ```
5. **Подключение:** роутер в `app/api/v1/__init__.py`, prefix + tags.
6. **Тесты** `tests/api/test_<resource>.py`: happy path, 401 без токена, 404 чужой объект, 400 валидация.

## Чек-лист
- [ ] `response_model` указан; наружу не утекают служебные поля.
- [ ] Права проверяются на объект (404 для чужих, не 403).
- [ ] Списки с пагинацией.
- [ ] `pytest`, `ruff check .`, `black --check .` — зелёные.
- [ ] `agents/architecture/CODEBASE_MAP.md` обновлён.
