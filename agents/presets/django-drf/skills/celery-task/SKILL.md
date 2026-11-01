---
name: celery-task
description: Создание фоновой задачи Celery в Django: tasks.py, идемпотентность, retry, мониторинг. Использовать для любой операции дольше ~1 секунды.
---

# ⚙️ Фоновая задача Celery

## Когда выносить в Celery
- Вызов внешнего API, генерация файлов/отчётов, отправка писем/уведомлений, массовые операции с БД, любое > ~1 секунды.

## Шаблон задачи (`apps/<app>/tasks.py`)
```python
from celery import shared_task

@shared_task(
    bind=True,
    autoretry_for=(TransientError,),   # ретраи только на транзиентные ошибки
    retry_backoff=True,                 # экспоненциальная пауза
    retry_kwargs={"max_retries": 5},
    acks_late=True,                     # задача не теряется при падении воркера
)
def send_order_confirmation(self, order_id: int) -> None:
    """Идемпотентна: повторный запуск не создаёт дублей."""
    order = Order.objects.get(pk=order_id)
    if order.email_sent_at:             # guard от двойной отправки
        return
    send_email(order)
    Order.objects.filter(pk=order_id).update(email_sent_at=now())
```

## Чек-лист
- [ ] **Идемпотентность:** повторный вызов безопасен (guard или transaction + unique constraint).
- [ ] **Retry:** только транзиентные ошибки, с backoff и лимитом; постоянные — в логи/алерт.
- [ ] **Таймауты** у внешних вызовов внутри задачи (не полагаться на воркер).
- [ ] **Ленивые импорты** тяжёлых зависимостей — внутри задачи (разгон воркера быстрее).
- [ ] **Мелкие задачи батчим:** `group`/`chord`, а не цикл из 10 000 `delay()`.
- [ ] **Монитинг:** Celery Flower или экспорт метрик; failed задачи видны.
- [ ] Тесты задач: вызывай `.run()` напрямую (синхронно) в unit-тестах.

## Типичные баги (смотри также `agents/bugs_and_fixes/`)
- Сериализация: не передавай ORM-объекты в аргументах — только ID.
- `transaction.on_commit(...)` для `delay()` внутри транзакции.
- Задача, меняющая БД, без ретраев при `OperationalError` (connection pool).
