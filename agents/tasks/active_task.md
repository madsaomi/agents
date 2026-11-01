# 📋 Активная задача: TASK-014 — Жизненный цикл памяти: handoff, archive, lint

**Статус:** ✅ COMPLETED (Завершена)  
**Дата создания:** 2026-11-01  
**Дата завершения:** 2026-11-01  
**Исполнитель:** ZCode (GLM)  
**Приоритет:** MEDIUM  
**Связанный план:** [`PLAN-010`](../plans/plan_010_zhiznennyy_tsikl_pamyati_handoff_archive_lint.md)  

---

## Чек-лист

- [x] **Этап 1:** `agents/tools/memory_lint.py` (4 проверки, warn), `agents/tools/archive_task.py` (валидация → архив → сброс; номер из TASK-ID, перезапись запрещена), `agents/tools/handoff.py` (7 fail-soft секций, `_section()` для h2–h6) — все с `root`-параметром
- [x] **Этап 2:** brain.py — subparsers `handoff [--copy]` / `archive [--force]` + `cmd_handoff`/`cmd_archive` в HANDLERS; check_integrity — секция 12 (lint, warn); тур 7/7 — строка про handoff/archive
- [x] **Этап 3:** `tests/test_lifecycle.py` — 18 тестов (lint: чисто/нарушения/исключения example; archive: отказ/force/перезапись/fallback; handoff: сбор/fail-soft/секции; CLI-смоуки). Попутно вылечен ложный битый линк `../plans/<file>` в тексте плана (валидатор ссылок честно ругался). Suite: **272 tests, 0 failures, 1 skip**
- [x] **Этап 4:** README (+2 команды), STATUS (подсистема, 272), CODEBASE_MAP (3 модуля в дереве и таблице), `sync --check` чист, integrity 100%, коммит `feat(plan-010)`, запись в history

## Примечания

- `brain handoff` на живом репо собрал честную эстафету: фаза, TASK-009 с открытыми пунктами (внешний смоук Codex + TASK-013), открытый BUG-001.
- Логика переноса задач в архив теперь автоматизирована; по завершении сессии: `end` → `handoff` → `archive`.

## Следующая задача

- Из backlog: TASK-010 (PyPI v0.5.0) / TASK-011 (brain graph) / TASK-012 (brain digest) / TASK-013 (root у фабрик) — по выбору заказчика.
