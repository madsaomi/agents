# 📝 Журнал сессии: PLAN-009 — Надёжность ядра CLI

- **Дата и время:** 2026-11-01 11:00 (локальное время, win32)
- **Агент:** ZCode (GLM-5.3-Flash)
- **Среда (IDE / CLI):** ZCode Desktop CLI
- **Операционная система:** win32 10.0.26300 x64 (Git Bash)
- **ID Задачи:** TASK-009

---

### 🔍 1. Что было сделано:
1. Согласован план PLAN-009 (смок-тесты CLI, декомпозиция brain.py, честный бэклог, dogfooding pre-commit).
2. Этап 1: grep-контракт — снаружи из brain.py импортируются `main` (корневой редиректор), `PROJECT_ROOT`/`show_status`/фабрики (brain_mcp), `transform_opencode_md` (test_sync), `list_presets`/`PRESETS_SOURCE_DIR` (test_presets); TOUR_SCREENS — только внутри brain.py.
3. Этап 2: создан `agents/tools/tour.py` (TOUR_SCREENS + `render_screens`); brain.py: блок экранов удалён (реэкспорт сохранён), if/elif-цепочка `main()` заменена на 21 хендлер `cmd_*` + словарь `HANDLERS`; строки вывода не менялись (сверено по git diff).
4. Этап 3: `tests/test_cli.py` — 14 смоков. **Обнаружен BUG-002**: смок `search --reindex` из tmp-скелета перезаписал индекс живого репо — `index_memory` резолвил файлы по `root`, но БД открывал по модульному `INDEX_FILE`. Индекс восстановлен (36 док.), `search.py` исправлен (db от `target_root`, идемпо `search_memory`), запись по шаблону в `bugs_and_fixes/BUG_002_index_memory_ignores_root.md`.
5. Этап 4: backlog.md переписан (TASK-010 PyPI, TASK-011 graph, TASK-012 digest, TASK-013 root-фабрики, смоук Codex); pre-commit хук установлен в сам шаблон; STATUS/CODEBASE_MAP/active_task актуализированы.

### 💡 2. Принятые решения и их мотивация:
- Фабрики артефактов (plan/bug/adr/task/walkthrough) исключены из смоков — они не принимают `root` и пишут в расположение модуля; дефект зафиксирован как TASK-013 (класс BUG-002), а не чинился в рамках декомпозиции (Plan-First: поведение не меняем без плана).
- Декомпозиция — механический перенос тел веток в `cmd_*` в том же файле, без переезда `transform_opencode_md`/фабрик (контракт Шага 1.1); валидация — git diff построчно + смоки.
- BUG-002 чинился в рамках PLAN-009, т.к. смок-тест без фиксы не мог пройти (мутирующий смок в tmp обязателен для изоляции от живого репо).

### 🐛 3. Ошибки, с которыми столкнулся (если были):
- BUG-002 (см. `bugs_and_fixes/BUG_002_index_memory_ignores_root.md`): потеря индекса живого репо при смоке — восстановлен полной переиндексацией, регресс закрыт тестом `test_root_detection_by_cwd`.

### 🧪 4. Результаты проверки и тестов:
- `python -m unittest discover -s tests` — **PASSED: 254 tests, 1 skipped** (SDK), 0 failures.
- Смоуки вручную: `brain.py status/tour --list/--help/doctor --json/links/claims` — rc 0; строки вывода идентичны до/после декомпозиции.
- `python brain.py sync --check` — чисто; integrity — 100%; py_compile — OK.

### 🔜 5. Инструкция для следующего агента:
- Следующая задача — из backlog.md: TASK-010 (PyPI v0.5.0, нужны креды заказчика), TASK-011 (`brain graph`), TASK-012 (`brain digest`), **TASK-013 (root у фабрик артефактов — рекомендую перед PyPI**: иначе `brain plan` из установленного пакета пишет в site-packages).
- Pre-commit хук теперь установлен: каждый коммит прогоняет integrity (~2–5 сек) — это норма шаблона.
- Мутирующие смоки писать только по образцу `tests/test_cli.py` (tmp-скелет + cwd=tmp).
