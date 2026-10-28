---
name: telegram-bot-handler
description: Пошаговое добавление пользовательского сценария в Telegram-бота на aiogram 3: роутер → FSM → клавиатуры → сервис → тесты.
---

# 💬 Новый сценарий бота (aiogram 3)

## Порядок (Plan-First: сначала план в `agents/plans/`)
1. **Роутер** `bot/handlers/<feature>.py`:
   ```python
   from aiogram import Router, F
   router = Router()
   ```
   Подключи в `bot/main.py` через `dp.include_router(...)`.

2. **FSM-состояние** (если сценарий многошаговый):
   ```python
   class OrderFSI(State):
       waiting_item: State
       waiting_comment: State
   ```
   Вход: `@router.message(Command("order"))` + `state.set_state(...)`.

3. **Хендлеры** на каждое состояние: один хендлер — одно состояние (`state == OrderFSI.waiting_item`), фильтры через `F.text` и т.п.

4. **Клавиатуры** `bot/keyboards/<feature>.py`:
   ```python
   InlineKeyboardBuilder().button(text="✅ Готово", callback_data="order:confirm:42")
   ```

5. **Сервис** `bot/services/<feature>.py` — бизнес-логика (запись в БД, вызов API).

6. **Финал:** `await state.clear()`, ответ с понятным следующим шагом.

7. **Тесты** `tests/test_<feature>.py`: happy path, отмена (`/cancel`), невалидный ввод.

## Чек-лист
- [ ] `/cancel` работает на каждом шаге.
- [ ] Невалидный ввод → подсказка, без падения.
- [ ] Долгая операция → «⏳» + фоновая задача (скилл `celery-task`).
- [ ] `callback_data` формата `<feature>:<action>:<id>`.
