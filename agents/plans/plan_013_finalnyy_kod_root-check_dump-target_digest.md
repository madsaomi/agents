# 📐 План реализации: PLAN-013 — Финальный код: root-check, dump-target, digest

> **Статус:** ✅ COMPLETED
> **Дата завершения:** 2026-11-01  
> **Дата создания:** 2026-11-01  
> **Автор / Агент:** ZCode (GLM)  
> **Связанные задачи:** TASK-015 (root-остатки) + TASK-012 (digest)  
> **Целевая ветка / Ревизия:** main

---

## 1. 🎯 Цель и контекст
- **Проблема:** (1) `run_integrity_check` не принимает `root` — в установленном пакете проверяет site-packages, а не проект (последний живой представитель класса BUG-002); (2) `brain dump` пишет `context_dump.md` рядом с модулем; (3) для веб-чатов нет компактной сводки проекта (dump — полный, handoff — для эстафеты).
- **Результат:** `check [--fix]` и `dump` уважают root; `brain digest [--tokens N] [--copy]` — компактный дайджест поверх готовых handoff/stats (без нового парсинга).

## 2. Затронутые файлы
- `[MODIFY]` `agents/tools/check_integrity.py` — `run_integrity_check(fix=False, root=None)`; внутри тела все `AGENTS_DIR`→`base_agents`, `PROJECT_ROOT`→`base_root` (25 использований, все внутри функции); секрет-скан получает base_root.
- `[MODIFY]` `agents/tools/brain.py` — `cmd_check` передаёт `root=PROJECT_ROOT`; `cmd_dump` пишет в `PROJECT_ROOT/agents/tools/context_dump.md`; subparser `digest [--tokens] [--copy]` + `cmd_digest`.
- `[MODIFY]` `agents/tools/end_session.py` — финальный `run_integrity_check(root=root)`.
- `[NEW]` `agents/tools/digest.py` — `render_digest(handoff_report, stats, max_tokens=None)`; переиспользует `handoff.collect_handoff` + `stats.collect_stats`.
- `[NEW]` `tests/test_final.py` — root-check не трогает живой репо; dump в tmp через monkeypatch PROJECT_ROOT; digest-секции и --tokens.
- `[MODIFY]` доки: README, STATUS, CODEBASE_MAP, backlog (TASK-012/015 → Выполнено), active_task, тур 4/7.

## 3. Шаги
- [x] Шаг 1: check_integrity root (скриптовая замена внутри тела функции + сигнатура + callers).
- [x] Шаг 2: dump-target в root.
- [x] Шаг 3: digest.py + диспетчер + тур.
- [x] Шаг 4: тесты (~10), полный suite — 0 failures (ожидаемо 295 → ~305).
- [x] Шаг 5: доки, backlog, sync --check, коммит `feat(plan-013)`.

## 4. Риски и откат
- Массовая замена в check_integrity — только в теле функции (границы: def → if __name__), верификация py_compile + suite + живой `check` (итог 100%).
- digest без дублирования: только делегирование handoff/stats.
- Откат: git revert одного коммита.

## 5. DoD
- [x] `check`/`dump`/`digest` принимают/уважают root; suite 0 failures; sync --check чист; TASK-012/015 закрыты; история записана.
