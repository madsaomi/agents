---
name: celery-task
description: Создание фоновой задачи Celery (рассылки, уведомления, парсинг) с идемпотентностью и retry. Использовать для операций дольше ~1 секунды.
---

# ⚙️ Фоновая задача Celery (бот)

## Когда выносить в Celery
- Рассылки, отправка уведомлений, парсинги, обращения к внешним API, любые операции > ~1 секунды. Хендлер обязан отвечать быстро.

## Шаблон задачи (`bot/tasks.py`)
```python
from celery import shared_task

@shared_task(
    bind=True,
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def broadcast_message(self, campaign_id: int) -> None:
    """Идемпотентна: повтор не отправляет пользователям дубли."""
    campaign = Campaign.objects.get(pk=campaign_id)
    if campaign.status == "done":
        return
    for user_id in campaign.audience_ids():
        try:
            bot.send_message(user_id, campaign.text)   # лимиты Telegram уважаем
        except TelegramForbiddenError:
            campaign.mark_blocked(user_id)             # пользователь заблокировал бота
    campaign.status = "done"
    campaign.save(update_fields=["status"])
```

## Чек-лист
- [ ] **Идемпотентность:** guard по статусу/уникальному ключу — повтор не дублирует отправку.
- [ ] **Лимиты Telegram:** рассылка ~20–30 сообщений/сек, батчи + `asyncio.sleep` (анти-спам).
- [ ] **`TelegramForbiddenError`** ловится: блок бота пользователем — не ошибка задачи.
- [ ] **Retry** только на транзиентные (таймауты, 5xx Telegram), с backoff.
- [ ] Аргументы — только примитивы (ID), не ORM-объекты.
- [ ] Запуск: `broadcast_message.delay(campaign_id)` из хендлера, ответ пользователю — сразу «⏳ запустил».
- [ ] Тесты: вызывай задачу синхронно (`.run()`) с мокнутым `bot.send_message`.
