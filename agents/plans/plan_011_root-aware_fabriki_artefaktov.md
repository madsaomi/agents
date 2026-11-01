# 📐 План реализации: PLAN-011 — Root-aware фабрики артефактов (TASK-013)

> **Статус:** ✅ COMPLETED  
> **Дата создания:** 2026-11-01  
> **Дата завершения:** 2026-11-01  
> **Автор / Агент:** ZCode (GLM)  
> **Связанная задача:** [TASK-013](../tasks/active_task.md) (из backlog, high)  
> **Целевая ветка / Ревизия:** main

---

## 1. 🎯 Цель и контекст

- **Проблема / Задача:** фабрики артефактов (`create_plan`, `create_bug_report`, `create_adr_record`, `create_task_card`, `create_walkthrough`, `init_project`, `end_session` + `extract_completed_tasks_from_active`) не принимают `root` и пишут в каталог расположения модуля. В dev-режиме из корня репозитория это незаметно; при запуске из другого cwd (проект с `agents/`) или установленного пакета `brain plan` молча создаёт файл не там (site-packages) — тот же класс дефекта, что BUG-002. Блокер для PyPI-релиза (TASK-010).
- **Ожидаемый технический результат:** все фабрики принимают `root=None` (fallback — прежнее поведение); цели (куда пишем) резолвятся от `root`, шаблоны (пакетный ресурс) остаются от модуля; диспетчер передаёт `PROJECT_ROOT` (cwd-детект). Регресс-тест: CLI `plan` из tmp-скелета создаёт файл в tmp.

---

## 2. 🔍 Анализ и затронутые компоненты

### Затронутые файлы:
- `[MODIFY]` `agents/tools/new_plan.py` — `create_plan(..., root=None)`: `plans_dir = (Path(root) if root else AGENTS_DIR) / "plans"`; шаблон — от модуля.
- `[MODIFY]` `agents/tools/brain.py` — 4 фабрики (+`root=None`: decisions/tasks/walkthroughs dirs + нумерация `get_next_number` по target-каталогу); хендлеры `cmd_plan/bug/adr/task/walkthrough/init/end` передают `root=PROJECT_ROOT`.
- `[MODIFY]` `agents/tools/end_session.py` — `end_session(..., root=None)` (history_dir, adr_dir, запись STATUS — от root), `extract_completed_tasks_from_active(root=None)`.
- `[MODIFY]` `agents/tools/init_project.py` — `init_project(..., root=None)`: скан плейсхолдеров и запись — в `root/agents`, шаблоны/словари — от модуля.
- `[NEW]` `tests/test_factories_root.py` — фабрики с `root=tmp` + CLI-регресс-смоук `plan` из tmp.
- `[MODIFY]` `agents/tasks/backlog.md` (TASK-013 → Выполнено), `agents/STATUS.md`, `agents/architecture/CODEBASE_MAP.md`, `agents/tasks/active_task.md`.

### Не меняется:
- `agents/mcp/brain_mcp.py` — MCP-сервер не знает cwd клиента; его root = расположение конфигурации сервера. Вызовы фабрик без `root` сохраняют прежнее поведение (fallback = модульный AGENTS_DIR == корень в dev). Зафиксировано комментарием в плане.
- Шаблоны (`agents/templates/`) — всегда читаются из модуля (пакетный ресурс).

### Зависимости и влияние:
- Новые библиотеки: **НЕТ**. Signature-изменения — только **добавление** keyword-параметра с default → обратно совместимо (brain_mcp и тесты вызывают без root).
- Breaking changes: **НЕТ**.

---

## 3. 📝 Пошаговый план реализации (Atomic Steps)

- [x] **Этап 1: Фабрики**
  - [x] Шаг 1.1: `new_plan.create_plan(+root)`.
  - [x] Шаг 1.2: `brain.py` — `create_bug_report/create_adr_record/create_task_card/create_walkthrough(+root)`.
  - [x] Шаг 1.3: `end_session.extract_completed_tasks_from_active(+root)`, `end_session(+root)`.
  - [x] Шаг 1.4: `init_project(+root)` (скан и запись в root, шаблоны — модуль).
- [x] **Этап 2: Диспетчер**
  - [x] Шаг 2.1: cmd-хендлеры brain.py передают `root=PROJECT_ROOT` во все фабрики/init/end.
- [x] **Этап 3: Тестирование**
  - [x] Шаг 3.1: `tests/test_factories_root.py`: (а) каждая фабрика с `root=tmp` → артефакт в tmp/agents/<раздел>, нумерация по tmp; (б) шаблон подставлен (маркер заголовка); (в) `end_session(root=tmp)` → запись в tmp/history + STATUS в tmp обновлён; (г) `extract_completed_tasks_from_active(root=tmp)`; (д) `init_project(root=tmp)` — без исключений, правки только в tmp; (е) **CLI-регресс**: `brain.py plan "Root Test"` с `cwd=tmp` → файл в tmp/agents/plans/ (ловит весь класс BUG-002); (ж) дефолт root=None — артефакт рядом с модулем? НЕТ: проверяем только tmp-сценарии, чтобы не мусорить (fallback-ветка покрыта тем, что live-репо работает).
  - [x] Шаг 3.2: Полный suite — 0 failures (ожидаемо 272 → ~284); `check`/`sync --check` — чисто.
- [x] **Этап 4: Сдача**
  - [x] Шаг 4.1: backlog (TASK-013 → Выполнено), STATUS, CODEBASE_MAP, active_task; `sync --check`; коммит `feat(plan-011): ...`; запись в history.

---

## 4. 🛡️ Риски, сайд-эффекты и план отката

- **Шаблоны vs цели**: если случайно завязать шаблон на root, в чужом проекте фабрики упадут (нет templates/) — Mitigation: шаблоны строго от модуля, тест (б) проверяет подстановку из канона.
- **Нумерация от root**: в tmp-скелете номера начинаются с 001 — не конфликтует с живым репо (тест (е) также проверяет, что в живом plans/ ничего не появилось).
- **end_session STATUS-обновление**: правит `root/STATUS.md` — тест (в) проверяет tmp, живой STATUS не затрагивается.
- **MCP без root** — осознанно (сервер не знает cwd клиента); зафиксировано, чтобы будущий агент не «починил» случайно.
- **Откат:** `git revert` одного коммита; сигнатуры сужаются обратно к безroot-версии без последствий (новых callers кроме brain.py нет).

---

## 5. 🧪 План тестирования и критерии приемки

1. Автоматические тесты: `python -m unittest discover -s tests -v` — 0 failures, 1 skip (SDK).
2. Ручная проверка: `cd /tmp-проект && python <repo>/agents/tools/brain.py plan "X"` → файл в tmp-проекте; в живом репо plans/ не изменился.
3. Критерий «Готово» (Definition of Done):
   - [x] Все 7 фабрик/функций принимают `root`, цели — от root, шаблоны — от модуля.
   - [x] CLI-регресс-тест из tmp зелёный (класс BUG-002 закрыт полностью).
   - [x] Suite 0 failures; sync --check чист; TASK-013 закрыт в бэклоге; план → ✅ COMPLETED; запись в history.
