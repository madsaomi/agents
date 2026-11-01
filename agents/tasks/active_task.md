# 📋 Активная задача: TASK-009 — Надёжность ядра CLI

**Статус:** ✅ COMPLETED (Завершена)  
**Дата создания:** 2026-11-01  
**Дата завершения:** 2026-11-01  
**Исполнитель:** ZCode (GLM)  
**Приоритет:** MEDIUM  
**Связанный план:** [`PLAN-009`](../plans/plan_009_nadyozhnost_yadra_cli.md)  

---

## Чек-лист

- [x] **Этап 1:** контракт совместимости зафиксирован — из brain.py снаружи импортируются `main` (редиректор), `PROJECT_ROOT`/`show_status`/фабрики (brain_mcp), `transform_opencode_md` (test_sync), `list_presets`/`PRESETS_SOURCE_DIR` (test_presets); TOUR_SCREENS — только внутри
- [x] **Этап 2:** `agents/tools/tour.py` (TOUR_SCREENS + `render_screens`); `main()` в brain.py → тонкий диспетчер `HANDLERS` + 21 хендлер `cmd_*`, поведение не менялось (строки вывода 1-в-1, реэкспорт TOUR_SCREENS сохранён)
- [x] **Этап 3:** `tests/test_cli.py` — 14 смоков (11 read-only на живом репо + 3 на tmp-скелете). Попутно **найден и исправлен BUG-002**: `index_memory` писал индекс в расположение модуля, игнорируя root (смок из tmp затёр индекс живого репо → восстановлен, `search.py` исправлен, запись в `bugs_and_fixes/`). Suite: **254 tests, 0 failures, 1 skip**
- [x] **Этап 4:** backlog.md переписан под реальный бэклог (TASK-010…013); pre-commit хук установлен в сам шаблон (`install_hooks.py`); STATUS/CODEBASE_MAP актуализированы; `sync --check` чист; integrity 100%; коммит `refactor(plan-009)`; запись в `agents/history/`

## Открытые пункты

- [ ] Живой смоук Codex `/hooks` — внешний блокер, перенесён в backlog.
- [ ] **TASK-013** (бэклог, high): фабрики артефактов не принимают `root` — тот же класс дефекта, что BUG-002.

## Следующая задача

- Из backlog: TASK-010 (PyPI v0.5.0) / TASK-011 (brain graph) / TASK-012 (brain digest) / TASK-013 (root у фабрик) — по выбору заказчика.
