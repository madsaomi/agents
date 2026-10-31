# 📐 План реализации: PLAN-008 — `brain doctor`: диагностика окружения

> **Статус:** ✅ COMPLETED  
> **Дата создания:** 2026-10-31  
> **Дата завершения:** 2026-10-31  
> **Автор / Агент:** ZCode (GLM)  
> **Связанная задача:** [TASK-008](../tasks/active_task.md)  
> **Целевая ветка / Ревизия:** main

---

## 1. 🎯 Цель и контекст

- **Проблема / Задача:** при раскатке шаблона в целевые проекты (фаза M2) нет быстрой команды «работает ли окружение»: FTS5 может отсутствовать в системном sqlite, `mcp`-extra не установлен, индекс поиска устарел или не создан, git недоступен, буфер обмена не работает. Существующий `brain check` валидирует **память и структуру** (секции 1–11), `stats` — **данные памяти**; состояние **окружения и инфраструктуры** не проверяет никто.
- **Ожидаемый технический результат:** команда `python brain.py doctor [--json]` — один взгляд на здоровье окружения с цветными маркерами 🟢/🟡/🔴, подсказками-хинтами по каждой проблеме и exit code (0 — нет ошибок, 1 — есть 🔴; 🟡 не валят exit code). Всё stdlib-only.

---

## 2. 🔍 Анализ и затронутые компоненты

### Затронутые файлы:
- `[NEW]` `agents/tools/doctor.py` — вся логика: `collect_doctor(root=None) -> dict`, `format_doctor(report) -> str`, 7 проверок окружения. Паттерн — как `stats.py` (collect/format, `root` для тестируемости, reconfigure stdout).
- `[MODIFY]` `agents/tools/brain.py` — import `doctor`, subparser `doctor` (`--json`), ветка в `main()` (как `stats`), +1 строка в экран тура 6/7 (TOUR_SCREENS).
- `[NEW]` `tests/test_doctor.py` — unittest на `collect_doctor`/`format_doctor` с tmp-скелетом проекта (паттерн `tests/test_stats.py`).
- `[MODIFY]` `README.md` — команда в разделе возможностей/команд.
- `[MODIFY]` `agents/STATUS.md` — строка подсистемы «Диагностика окружения» + счётчик тестов.
- `[MODIFY]` `agents/architecture/CODEBASE_MAP.md` — дерево + строка таблицы `doctor.py`.
- `[MODIFY]` `agents/tasks/active_task.md` — карточка TASK-008 с чек-листом.
- `[MODIFY]` `.github/workflows/integrity.yml` — шаг `python brain.py doctor --json` после integrity (дым на чистом checkout: exit 0 при warn-ах).

### Зависимости и влияние:
- Новые библиотеки: **НЕТ** — stdlib (`sys`, `sqlite3`, `shutil`, `subprocess`, `importlib.util`, `json`, `os`, `time`, `pathlib`).
- Влияние на существующие API: только добавление (`brain.py` — новый subparser; существующие команды не трогаем).
- Breaking changes: **НЕТ**. `.mcp.json`, sync-шаблоны, CORE_RULES.md не меняются → `sync --check` останется чистым.

### Контракт `doctor.py` (проверки, каждая → `{name, status: ok|warn|fail, details, hint}`):

| # | Проверка | ok | warn | hint (пример) |
|---|---|---|---|---|
| 1 | **python** | `sys.version_info >= (3, 9)` | — (fail при < 3.9) | «Обнови Python до 3.9+» |
| 2 | **fts5** | `CREATE VIRTUAL TABLE temp.x USING fts5(...)` в `:memory:` | — (fail) | «search недоступен: собери sqlite с FTS5» |
| 3 | **git** | `shutil.which("git")` и root — git-репо (`git rev-parse`) | нет бинар/не репо | «claim/worktree и integrity требуют git» |
| 4 | **index** | `.brain_index.db` есть и свежее всех `.md` памяти | нет индекса / устарел | «Запусти: brain search --reindex» |
| 5 | **clipboard** | найден бэкенд (clip.exe/pbcopy/wl-copy или pyperclip) | нет бэкенда | «dump сохранит в файл без буфера обмена» |
| 6 | **mcp** | `importlib.util.find_spec("mcp")` найден | не найден | «pip install ".[mcp]"» |
| 7 | **write_access** | запись+удаление `agents/.doctor_write_test` | — (fail при OSError) | «Проверь права на каталог agents/» |

- **Свежесть индекса:** mtime `.brain_index.db` vs max mtime `.md` в каталогах памяти (список сверить с `search.py` — дублировать константу нельзя: импортировать её оттуда, если экспортируется, иначе os.walk по `agents/` с исключением `.locks`; решение — на Шаге 1.1 после чтения search.py).
- **Exit code:** `fail` → 1, иначе 0; `warn` не влияет (чтобы CI на чистом checkout был зелёным).
- `--json` → `json.dumps(report, ensure_ascii=False, indent=2)` (как `stats --json`).

---

## 3. 📝 Пошаговый план реализации (Atomic Steps)

- [x] **Этап 1: Подготовка и контракты**
  - [x] Шаг 1.1: Прочитать `search.py` — определить, экспортируется ли список каталогов памяти для проверки свежести индекса (импорт > дублирование).
  - [x] Шаг 1.2: Прочитать `dump_context.copy_to_clipboard` — какие бэкенды буфера она поддерживает (doctor не должен называть бэкенд, которого dump не использует).
- [x] **Этап 2: Реализация**
  - [x] Шаг 2.1: Создать `agents/tools/doctor.py`: `collect_doctor()`, `format_doctor()`, reconfigure stdout на уровне модуля (идиома `stats.py`/`search.py`, как и планировалось по стилю), цвета как в `check_integrity.py`.
  - [x] Шаг 2.2: Подключить в `brain.py`: import, subparser `doctor` c `--json`, ветка `main()` с exit code, строка в TOUR_SCREENS 6/7.
- [x] **Этап 3: Тестирование**
  - [x] Шаг 3.1: `tests/test_doctor.py`: (а) отчёт на реальном репо — все 7 ключей, счётчики summary сходятся; (б) fts5 ok; (в) write_access ok; (г) tmp-скелет без `.brain_index.db` → warn с хинтом reindex; (д) устаревший индекс (utime назад) → warn; (е) tmp-скелет без git → warn; (ж) отчёт json-сериализуем; (з) format содержит маркеры и хинты; (и) mock ошибки sqlite → fail (unittest.mock.patch).
  - [x] Шаг 3.2: Ручной смоук: `python brain.py doctor` и `python brain.py doctor --json` на этом репо; exit code 0.
  - [x] Шаг 3.3: Полный suite: `python -m unittest discover -s tests` — 0 failures (ожидаемо 226 → ~235).
- [x] **Этап 4: Документирование и сдача**
  - [x] Шаг 4.1: README, STATUS.md, CODEBASE_MAP.md, active_task.md — актуализация.
  - [x] Шаг 4.2: `.github/workflows/integrity.yml` — шаг doctor.
  - [x] Шаг 4.3: `python brain.py sync --check` — чисто; коммит `feat(plan-008): ...`.

---

## 4. 🛡️ Риски, сайд-эффекты и план отката

- **Дублирование констант с search.py** (каталоги памяти) — Mitigation: импорт, а не копия (Шаг 1.1); если константы приватны — минимально экспортировать их из search.py.
- **Ложный fail в CI** — Mitigation: только 3 проверки дают fail (python/fts5/write_access), все детерминированы; clipboard/index/mcp/git — warn-only.
- **os.utime/monkeypatch в тестах на Windows** — `Path.utime` работает штатно; ошибки записи симулируем через `unittest.mock.patch` (stdlib), а не chmod (кроссплатформенно ненадёжен).
- **Влияние на существующие команды:** нет — новый модуль и новая ветка диспетчера; импорт `doctor` в `brain.py` без вредных side-effects (reconfigure stdout идемпотентен и уже выполняется самим `brain.py`/`stats.py` при импорте — тот же идиом).
- **Откат:** `git revert` одного коммита; новые файлы удаляются, существующие возвращаются к прежнему виду. Данные памяти не затрагиваются.

---

## 5. 🧪 План тестирования и критерии приемки

1. Автоматические тесты: `python -m unittest discover -s tests -v` — 0 failures, 1 skip (SDK).
2. Ручная проверка: `python brain.py doctor` → 7 проверок с честными статусами этого репо, хинты на warn-ах; `--json` парсится `json.loads`; `echo $?` → 0.
3. Критерий «Готово» (Definition of Done):
   - [x] `python brain.py doctor` работает на реальном репо, exit 0; на tmp-скелете без индекса — warn, не fail.
   - [x] Тесты 0 failures; счётчики в STATUS.md/CODEBASE_MAP.md обновлены.
   - [x] `brain.py sync --check` чист; README/STATUS/MAP/active_task актуализированы.
   - [x] Чек-лист плана `[x]`, статус → ✅ COMPLETED, запись в `agents/history/`.
