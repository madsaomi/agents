# 📋 Активная задача: TASK-008 — `brain doctor`: диагностика окружения

**Статус:** ✅ COMPLETED (Завершена)  
**Дата завершения:** 2026-10-31  
**Дата создания:** 2026-10-31  
**Исполнитель:** ZCode (GLM)  
**Приоритет:** MEDIUM  
**Связанный план:** [`PLAN-008`](../plans/plan_008_brain_doctor_diagnostika_okruzheniya.md)  

---

## Чек-лист

- [x] **Этап 1:** сверены `search.py` (публичные `MEMORY_SECTIONS`/`INDEX_FILE` — импорт без дублирования) и `dump_context.copy_to_clipboard` (бэкенды clip/pbcopy/xclip)
- [x] **Этап 2:** `agents/tools/doctor.py` — `collect_doctor()`/`format_doctor()`, 7 проверок с хинтами; диспетчер `brain.py` (import, subparser `--json`, ветка с exit code), строка в туре 6/7
- [x] **Этап 3:** `tests/test_doctor.py` — 14 тестов (форма, warn-сценарии на tmp-скелете, mock-инъекция fts5/write_access ошибок); полный suite **240 tests, 0 failures, 1 skip**; смоук `brain.py doctor` / `--json` — exit 0, warn-ы честные (индекс устарел, mcp не установлен)
- [x] **Этап 4:** README, STATUS.md, CODEBASE_MAP.md актуализированы; шаг doctor в CI; `sync --check` чист; integrity 100%; коммит `feat(plan-008)`; запись в `agents/history/`

## Примечания

- `check` — память/структура, `stats` — данные памяти, `doctor` — окружение: пересечений нет.
- Warn (git/индекс/буфер/mcp) не валят exit code → CI на чистом checkout зелёный; fail (python/fts5/write_access) → exit 1.
