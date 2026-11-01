# 📋 Активная задача: TASK-013 — Root-aware фабрики артефактов

**Статус:** ✅ COMPLETED (Завершена)  
**Дата создания:** 2026-11-01  
**Дата завершения:** 2026-11-01  
**Исполнитель:** ZCode (GLM)  
**Приоритет:** HIGH  
**Связанный план:** [`PLAN-011`](../plans/plan_011_root-aware_fabriki_artefaktov.md)  

---

## Чек-лист

- [x] **Этап 1:** `new_plan.create_plan(+root)`; brain.py — `create_bug_report/create_adr_record/create_task_card/create_walkthrough(+root)`; `end_session(+root)` + `extract_completed_tasks_from_active(+root)`; `init_project(+root)`. Канон: цели — от `root/agents`, шаблоны/образцы — ресурсы модуля
- [x] **Этап 2:** cmd-хендлеры brain.py передают `root=PROJECT_ROOT` (cwd-детект) во все фабрики/init/end; MCP не менялся (сервер не знает cwd клиента — fallback = прежнее поведение)
- [x] **Этап 3:** `tests/test_factories_root.py` — 9 тестов: 5 фабрик пишут в tmp + нумерация по tmp + подстановка шаблонов; end_session/extract с root; init_project правит только tmp (живой STATUS побайтово не изменён); **CLI-регресс**: `brain plan` из cwd=tmp создаёт план в tmp. Suite: **281 tests, 0 failures, 1 skip**
- [x] **Этап 4:** backlog (TASK-013 → Выполнено; открыт TASK-015 — остатки класса BUG-002: `run_integrity_check`/`dump`), STATUS (281, фаза 003…011), CODEBASE_MAP, `sync --check` чист, integrity 100%, коммит `feat(plan-011)`, запись в history

## Примечания

- Класс BUG-002 закрыт для фабрик; PyPI-релиз (TASK-010) разблокирован.
- Остаток класса: `run_integrity_check` и цель `brain dump` — вынесено в TASK-015 (Medium).

## Следующая задача

- Из backlog: TASK-010 (PyPI v0.5.0) / TASK-011 (brain graph) / TASK-012 (brain digest) / TASK-015 (root-остатки) — по выбору заказчика.
