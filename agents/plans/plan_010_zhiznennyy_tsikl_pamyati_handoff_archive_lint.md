# 📐 План реализации: PLAN-010 — Жизненный цикл памяти: handoff, archive, lint

> **Статус:** ✅ COMPLETED  
> **Дата создания:** 2026-11-01  
> **Дата завершения:** 2026-11-01  
> **Автор / Агент:** ZCode (GLM)  
> **Связанная задача:** [TASK-014](../tasks/active_task.md)  
> **Целевая ветка / Ревизия:** main

---

## 1. 🎯 Цель и контекст

- **Проблема / Задача:** три последних ручных операции агента: (1) эстафету собирают руками из STATUS + active_task + плана + последней записи history; (2) завершённую задачу переносят в `tasks/archive/` копированием вручную; (3) дисциплина записей (план без рисков, задача без чек-листа) никем не проверяется — только глазами при ревью.
- **Ожидаемый технический результат:** `brain handoff` — готовый блок передачи следующему агенту за 1 команду; `brain archive` — валидация → перенос карточки в архив → чистая active_task; `memory lint` — 12-я секция в `check_integrity`, warn-ами ловящая недокормленные записи. Всё stdlib-only, root-параметры везде (урок BUG-002).

---

## 2. 🔍 Анализ и затронутые компоненты

### Затронутые файлы:
- `[NEW]` `agents/tools/handoff.py` — `collect_handoff(root=None) -> dict`, `format_handoff(report) -> str` (паттерн doctor.py: collect/format, fail-soft по каждой секции).
- `[NEW]` `agents/tools/archive_task.py` — `archive_active_task(root=None, force=False) -> (ok, msg)`; имя архива `task_NNN_completed.md` (следующий номер сканом `tasks/archive/`, сейчас максимум 006); сброс active_task в заглушку.
- `[NEW]` `agents/tools/memory_lint.py` — `lint_memory(root=None) -> list[dict]` (findings: `{name, passed, details}`); подключается в `check_integrity` как секция 12.
- `[MODIFY]` `agents/tools/brain.py` — subparsers `handoff [--copy]`, `archive [--force]`; хендлеры `cmd_handoff`, `cmd_archive` (HANDLERS + парсер).
- `[MODIFY]` `agents/tools/check_integrity.py` — секция 12: `memory_lint.lint_memory()` перед «Итоговым выводом», warn-уровень.
- `[NEW]` `tests/test_lifecycle.py` — handoff/archive/lint на tmp-скелете.
- `[MODIFY]` `README.md` (2 команды), `agents/STATUS.md`, `agents/architecture/CODEBASE_MAP.md`, `agents/tasks/active_task.md`.
- `[MODIFY]` `agents/tools/tour.py` — экран 7/7: +1 строка про handoff/archive.

### Зависимости и влияние:
- Новые библиотеки: **НЕТ** (re, json, shutil, datetime, pathlib; `task_locks` импорт для локов — ленивый внутри collect).
- Влияние на существующие API: только добавление (2 команды CLI, 1 секция check). Существующие команды/секции не меняются.
- Breaking changes: **НЕТ**. `check` может начать выдавать новые warn-ы (lint) — это ожидаемое поведение, не fail.

### Контракты:

**`collect_handoff(root)` → секции отчёта (каждая fail-soft, пропущена при отсутствии):**
1. **status** — `STATUS.md`: строка `**Текущая фаза:**` + блок «Что делается прямо сейчас» (до следующего `## `).
2. **active_task** — заголовок, `**Статус:**`, список незакрытых `- [ ]` (кроме строки-заглушки).
3. **plan** — из active_task: ссылка на план вида `../plans/<файл>` → файл плана, его статус, открытые шаги.
4. **bugs** — `bugs_and_fixes/BUG_*.md` (без README/example), `**Статус:**` без «РЕШЕНО» → открытые.
5. **claims** — `locks.list_claims(root=root)` (ленивый импорт).
6. **backlog_next** — первый `- [x] **TASK-` из блока «Высокий приоритет» backlog.md.
7. **last_session** — свежайший `history/session_*.md` (без README): заголовок + секция «Инструкция для следующего агента».
- Формат — markdown с эмодзи-заголовками; пустые секции → «(нет данных)». `--copy` — через `dump_context.copy_to_clipboard`.

**`archive_active_task(root, force)`:**
- Активной задачи нет / она заглушка → `(False, "нет активной задачи")`.
- Есть незакрытые `- [ ]` и не `--force` → `(False, "остались открытые пункты: N — закрой или используй --force")`.
- Иначе: прочитать active_task → записать в `tasks/archive/task_{next:03d}_completed.md` (next = max+1 сканом) → заменить active_task заглушкой («Задача не выбрана — см. backlog.md») → `(True, msg с именем архива)`.
- История не трогается (ANTI-PATTERN №2 соблюдён: создаются только новые файлы).

**`lint_memory(root)` — 4 проверки (все warn-уровень):**
- каждый `plans/plan_*.md` (без example): содержит `Статус:` и ≥1 чекбокс;
- `tasks/active_task.md`: содержит чекбоксы (если не заглушка);
- каждый `decisions/ADR_*.md` (без README/example): содержит `Статус`;
- каждый `bugs_and_fixes/BUG_*.md` (без README/example): содержит `Симптом` и `Первопричина`.

---

## 3. 📝 Пошаговый план реализации (Atomic Steps)

- [x] **Этап 1: Модули**
  - [x] Шаг 1.1: `agents/tools/memory_lint.py` (самый простой, без зависимостей).
  - [x] Шаг 1.2: `agents/tools/archive_task.py` (валидация + перенос + сброс).
  - [x] Шаг 1.3: `agents/tools/handoff.py` (collect/format, 7 секций, fail-soft).
- [x] **Этап 2: Интеграция**
  - [x] Шаг 2.1: brain.py — парсеры и хендлеры `handoff [--copy]` / `archive [--force]`, строка в туре 7/7.
  - [x] Шаг 2.2: check_integrity.py — секция 12 (lint) перед итоговым выводом.
- [x] **Этап 3: Тестирование**
  - [x] Шаг 3.1: `tests/test_lifecycle.py`: (а) lint: скелет с «плохим» планом → finding, с хорошим → чисто; (б) archive: с открытыми пунктами → отказ; `--force` → архив создан `task_007_completed.md`, active_task — заглушка; (в) handoff: секции заполнены из фикстуры, отсутствующие секции fail-soft; (г) смоки CLI: `brain.py handoff` (живое репо, rc 0), `brain.py archive --force` на tmp.
  - [x] Шаг 3.2: Полный suite — 0 failures (ожидаемо 254 → ~268); `check` на живом репо — секция 12 зелёная.
- [x] **Этап 4: Документирование и сдача**
  - [x] Шаг 4.1: README, STATUS, CODEBASE_MAP, active_task, тур.
  - [x] Шаг 4.2: `sync --check` чист; коммит `feat(plan-010): ...`; запись в history.

---

## 4. 🛡️ Риски, сайд-эффекты и план отката

- **Ложные warn-ы lint на живом репо** — Mitigation: секция warn-уровень (не валит check/CI); исключения example/README; перед коммитом прогнать `check` и убедиться в честности находок.
- **`archive` необратимо переносит карточку** — Mitigation: refusal при открытых пунктах, `--force` осознанный; старый контент сохраняется в архиве (не удаляется); файл active_task перезаписывается только заглушкой после успешной записи архива (порядок: сначала архив, потом сброс).
- **Хрупкий парсинг markdown в handoff** — Mitigation: все секции fail-soft (OSError/«нет секции» → пропуск с пометкой), фикстурные тесты на оба сценария.
- **Нумерация архива при гонке** — Mitigation: приемлемо (одиночная сессия); лок `claim TASK` — вне рамок.
- **Откат:** `git revert` одного коммита; секция 12 отключается удалением вызова lint из check_integrity.

---

## 5. 🧪 План тестирования и критерии приемки

1. Автоматические тесты: `python -m unittest discover -s tests -v` — 0 failures, 1 skip (SDK).
2. Ручная проверка: `python brain.py handoff` на живом репо — секции заполнены реальными данными, rc 0; `python brain.py check` — секция 12 без ложных warn; `brain.py archive` без задач — вежливый отказ.
3. Критерий «Готово» (Definition of Done):
   - [x] handoff собирает 7 секций, archive — полный цикл с защитой от открытых пунктов, lint — 4 проверки в секции 12.
   - [x] Все новые функции принимают `root` (урок BUG-002).
   - [x] Тесты 0 failures; `sync --check` чист; доки актуальны; план → ✅ COMPLETED, запись в history.
