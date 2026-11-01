# 📐 План реализации: PLAN-009 — Надёжность ядра CLI

> **Статус:** ✅ COMPLETED  
> **Дата создания:** 2026-10-31  
> **Дата завершения:** 2026-11-01  
> **Автор / Агент:** ZCode (GLM)  
> **Связанная задача:** [TASK-009](../tasks/active_task.md)  
> **Целевая ветка / Ревизия:** main

---

## 1. 🎯 Цель и контекст

- **Проблема / Задача:** `agents/tools/brain.py` (~1000 строк) — самый используемый вход в проект, но **единственный крупный модуль без тестов**: все ~18 подкоманд inline в `main()` (строки ~636–988), TOUR_SCREENS и тур-рендер тоже внутри файла. Любая правка диспетчера может молча сломать команду — CI этого не видит. Попутно: `agents/tasks/backlog.md` содержит заглушки TASK-002…005 и не отражает реальный бэклог (PyPI, graph, digest, смоук Codex); pre-commit-хук шаблона не установлен в самом шаблоне (`.git/hooks/` — только samples), т.е. dogfooding нарушен.
- **Ожидаемый технический результат:** (1) смок-тесты всех подкоманд CLI через subprocess — read-only на живом репо, мутирующие на tmp-скелете; (2) декомпозиция `brain.py` без смены поведения: тур → `agents/tools/tour.py`, ветки `main()` → функции-хендлеры; (3) честный `backlog.md`; (4) pre-commit хук установлен в этом репозитории.

---

## 2. 🔍 Анализ и затронутые компоненты

### Затронутые файлы:
- `[NEW]` `agents/tools/tour.py` — `TOUR_SCREENS` (переезд из brain.py) + `render_screens(screens, interactive=False)` (логика ветки `tour` из main(), включая input-цикл). Только stdlib.
- `[MODIFY]` `agents/tools/brain.py` — import из `tour.py` (TOUR_SCREENS остаётся доступен как `brain.TOUR_SCREENS` для совместимости, если где-то импортируется); декомпозиция `main()`: тело каждой ветки → `cmd_<name>(args)` в том же файле, `main()` — тонкий диспетчер. Поведение не меняется (вывод, exit codes, аргументы — байт-в-байт).
- `[NEW]` `tests/test_cli.py` — смок-тесты subprocess-ом: read-only на живом репо; мутирующие — на tmp-скелете с `cwd=tmp` (brain.py сам определяет root по `cwd/agents`).
- `[MODIFY]` `agents/tasks/backlog.md` — реальный бэклог: TASK-010 PyPI v0.5.0, TASK-011 `brain graph`, TASK-012 `brain digest`, смоук Codex `/hooks` (внешний блокер), Dockerfile, README EN.
- `[MODIFY]` `agents/STATUS.md`, `agents/architecture/CODEBASE_MAP.md` — счётчики, tour.py в дереве/таблице.
- `[MODIFY]` `agents/tasks/active_task.md` — карточка TASK-009.
- `[N/A]` `.git/hooks/pre-commit` — устанавливается штатной `python agents/tools/install_hooks.py` (в git не коммитится).

### Ограничения смок-тестов (чтобы не загрязнить репозиторий):
- **Разрешено на живом репо (read-only):** `--help`, `status`, `tour --list`, `presets`, `claims`, `stats --json`, `doctor --json` (exit 0), `sync --check`, `links` (без аргументов), `check` (без `--fix`).
- **Только на tmp-скелете:** `plan/bug/adr/task/walkthrough` (создают файлы → проверить появление + exit 0), `search --reindex` + `search "..."`, `claim/claims/release` (локи в tmp).
- **Исключены из смока (root привязан к расположению модуля или меняет репо):** `end` (пишет history живого репо), `init`, `preset <имя>` (применяет к живому репо), `upgrade`, `dump` (пишет `agents/tools/context_dump.md` рядом с модулем).
- `transform_opencode_md` и `_opencode_transform_specs` **остаются в brain.py** — их импортирует `tests/test_sync.py` (проверено по карте кодовой базы); переезд = отдельная задача, если понадобится.

### Зависимости и влияние:
- Новые библиотеки: **НЕТ**.
- Влияние на существующие API: CLI-интерфейс не меняется (те же команды/флаги/вывод); `TOUR_SCREENS` переезжает в `tour.py`, в brain.py — реэкспорт.
- Breaking changes: **НЕТ**.

---

## 3. 📝 Пошаговый план реализации (Atomic Steps)

- [x] **Этап 1: Подготовка**
  - [x] Шаг 1.1: Проверить grep'ом, кто импортирует `TOUR_SCREENS`/`transform_opencode_md`/`main` из brain (тесты, хуки, mcp) — зафиксировать контракт совместимости.
- [x] **Этап 2: Декомпозиция (без смены поведения)**
  - [x] Шаг 2.1: Создать `agents/tools/tour.py`: TOUR_SCREENS + `render_screens()`.
  - [x] Шаг 2.2: brain.py: import из tour.py (с реэкспортом), ветка `tour` → вызов `render_screens`.
  - [x] Шаг 2.3: brain.py: тело каждой ветки `main()` → `cmd_<name>(args)`; `main()` — только парсинг + диспетчер. diff должен показывать перенос, не переписывание.
- [x] **Этап 3: Смок-тесты CLI**
  - [x] Шаг 3.1: `tests/test_cli.py` — `TestCliReadOnly` (живое репо, см. белый список) и `TestCliMutating` (tmp-скелет: план/баг/adr/задача/walkthrough/search/claim-release), паттерн `TestTourSmoke` из test_stats.py.
  - [x] Шаг 3.2: Полный suite — 0 failures (ожидаемо 240 → ~262).
- [x] **Этап 4: Гигиена и сдача**
  - [x] Шаг 4.1: Переписать `agents/tasks/backlog.md` под реальный бэклог.
  - [x] Шаг 4.2: `python agents/tools/install_hooks.py` — pre-commit в этом репо; проверка: файл существует, исполняемый.
  - [x] Шаг 4.3: STATUS.md, CODEBASE_MAP.md, active_task.md актуализация; `sync --check` чист; коммит `refactor(plan-009): ...` + запись в history.

---

## 4. 🛡️ Риски, сайд-эффекты и план отката

- **Большой diff в brain.py** — Mitigation: механический перенос тел веток в функции, без переименования переменных и смены строк вывода; валидатор — смок-тесты + 240 существующих тестов.
- **Контракт совместимости** — Mitigation: Шаг 1.1 (grep импортов), реэкспорт TOUR_SCREENS; transform_* не трогаем.
- **Смоки могут загрязнить репо** — Mitigation: жёсткий белый/чёрный список команд (см. §2); tmp-скелет с `cwd=tmp` — brain.py детектит root по cwd.
- **pre-commit замедлит коммиты** (~2–5 сек на check) — осознанно: это собственная рекомендация шаблона; отключается удалением `.git/hooks/pre-commit`.
- **Windows/Git Bash subprocess** — паттерн уже обкатан в test_stats.py (tour smoke) и test_claim.py; timeout=60 на процесс.
- **Откат:** `git revert` одного коммита; pre-commit снимается удалением файла хука.

---

## 5. 🧪 План тестирования и критерии приемки

1. Автоматические тесты: `python -m unittest discover -s tests -v` — 0 failures, 1 skip (SDK); новый `tests/test_cli.py` покрывает все разрешённые подкоманды.
2. Ручная проверка: `python brain.py status|doctor|stats --json|tour --list` — вывод идентичен до/после декомпозиции (глазами); `python agents/tools/install_hooks.py` → хук установлен.
3. Критерий «Готово» (Definition of Done):
   - [x] Ни одна подкоманда не изменила поведение (смоки зелёные и до, и после декомпозиции).
   - [x] `brain.py` без inline-веток в `main()`, тур — в `tour.py`.
   - [x] backlog.md отражает реальные задачи; pre-commit установлен в самом шаблоне.
   - [x] Полный suite 0 failures; `sync --check` чист; доки актуальны; план → ✅ COMPLETED, запись в history.
