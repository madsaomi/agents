# 📐 План реализации: PLAN-007 — MCP-инструменты связей, локов и статистики

> **Статус:** ✅ COMPLETED  
> **Дата создания:** 2026-10-30  
> **Дата завершения:** 2026-10-30  
> **Автор / Агент:** MiMo (OpenCode)  
> **Связанная задача:** TASK-006 (открытый пункт «MCP-инструменты `list_links` / `list_claims` / `get_stats`») → новая TASK-007  
> **Целевая ветка / Ревизия:** main

---

## 1. 🎯 Цель и контекст

- **Проблема / Задача:** MCP-сервер `brain-mcp` (6 инструментов) не даёт MCP-клиентам доступа к вики-связям `[[...]]`, мультиагентным локам claim и дашборду здоровья памяти. Эти возможности уже есть в CLI (`brain.py links|claims|stats`), но агент через MCP вынужден либо терять их, либо дублировать логику парсинга markdown.
- **Ожидаемый результат:** три новых read-only MCP-инструмента `list_links`, `list_claims`, `get_stats`, переиспользующие готовую логику `agents/tools/links.py`, `locks.py`, `stats.py` (без дублирования и без ломания формата markdown-файлов). Ядро остаётся stdlib-only; пакет `mcp` — по-прежнему optional extra.

---

## 2. 🔍 Анализ и затронутые компоненты

### Затронутые файлы:
- `[MODIFY]` `agents/mcp/brain_mcp.py` — три новые чистые функции-инструмента + регистрация в `TOOL_FUNCTIONS` + обновление докстринга модуля (список инструментов в шапке).
- `[MODIFY]` `tests/test_brain_mcp.py` — обновить `TestToolSurface.EXPECTED` (сейчас жёсткая проверка на ровно 6 имён — **тест сломается**, если не обновить); добавить тест-классы для трёх инструментов.
- `[MODIFY]` `README.md` — раздел «MCP-сервер brain-mcp»: +3 строки в таблицу инструментов.
- `[MODIFY]` `agents/STATUS.md` — строка «MCP-сервер brain-mcp»: 6 → 9 инструментов; счётчик тестов.
- `[MODIFY]` `agents/architecture/CODEBASE_MAP.md` — строки с «6 инструментов» и перечнем функций `brain_mcp.py`.
- `[MODIFY]` `agents/tasks/active_task.md` — закрыть пункт «MCP-инструменты list_links/list_claims/get_stats» (или перевести в архив при новой TASK-007).

Файлы НЕ создаются и НЕ удаляются — изменения точечные, только в MCP-обёртке и тестах.

### Зависимости и влияние:
- Новые библиотеки / пакети: НЕТ (всё stdlib + уже существующие модули `agents/tools/`; импорт `links`/`locks`/`stats` — ленивый внутри функций, как это уже сделано для `end_session`/`search`, чтобы не тянуть side-effects на уровень модуля).
- Влияние на существующие API: только добавление; сигнатуры существующих 6 инструментов не меняются, `.mcp.json` не трогаем (имя сервера `brain-memory` то же).
- Breaking changes: НЕТ. Единственный каскад — `TestToolSurface.EXPECTED` (осознанно strict-тест, обновляется в этом же PR).

### Контракты новых инструментов (read-only, все принимают `root` для тестируемости):

**`list_links(query: str = "", root: Path = None) -> str`**
- Переиспользует `links.links_for()` и `links.unresolved_links()`.
- Пустой query → сводка: «🔗 Связи памяти: N разрешённых, M плейсхолдеров, K битых» + список битых (до ~10, `src:line raw`).
- query задан (ID/имя/stem/путь) → секции «➡️ Исходящие», «⬅️ Обратные ссылки», «⚠️ Неразрешённые» в формате `{src}:{line} {raw} → {dst}`.
- Запись не найдена → `❓ Запись не найдена: 'X'` + «Но есть битые связи с такой целью» (нормализованное сравнение — через публичный результат `links_for`, не трогая приватный `_norm`).
- Плейсхолдеры (`[[...]]`, короткие цели) не выводятся — как в CLI.

**`list_claims(root: Path = None) -> str`**
- Переиспользует `locks.list_claims()`.
- Локи есть → «🔒 Активные блокировки (N):» + строки `mark task agent PID created` (+ worktree/заметка), маркеры 🟢 active / 💀 stale / ❓ unknown — в точности как `locks.py main`.
- Локов нет → «Свободно: активных блокировок нет.»

**`get_stats(as_json: bool = False, stale_days: int = 90, root: Path = None) -> str`**
- Переиспользует `stats.collect_stats()` + `stats.format_stats()`.
- `as_json=False` → текстовый дашборд `format_stats()`; `as_json=True` → `json.dumps(stats, ensure_ascii=False, indent=2)` (машинное чтение, как `brain.py stats --json`).

Стиль ответов — как у существующих инструментов: plain-text/markdown-строка с эмодзи-маркерами; ошибки — `❌`, не fatal-ситуации — `ℹ️`/`❓`. Секреты не затрагиваются. Против prompt-injection найденное в `list_links` выводится как данные без инструкций (для консистентности с `search_memory` можно добавить одну строку-предостережение).

---

## 3. 📝 Пошаговый план реализации (Atomic Steps)

- [x] **Этап 1: Подготовка и контракты**
  - [x] Шаг 1.1: Обновить докстринг модуля `agents/mcp/brain_mcp.py` (шапка со списком инструментов: 6 → 9, добавить `list_links`, `list_claims`, `get_stats`).
- [x] **Этап 2: Реализация инструментов**
  - [x] Шаг 2.1: Реализовать `list_links(query="", root=None)` в `agents/mcp/brain_mcp.py`: ленивый `import links`, делегирование `links_for`/`unresolved_links`, форматирование строк (без дублирования резолюции).
  - [x] Шаг 2.2: Реализовать `list_claims(root=None)`: ленивый `import locks`, делегирование `locks.list_claims()`, форматирование с маркерами статуса.
  - [x] Шаг 2.3: Реализовать `get_stats(as_json=False, stale_days=90, root=None)`: ленивый `import stats`, делегирование `collect_stats`/`format_stats`, JSON-ветка через `json.dumps(ensure_ascii=False, indent=2)`.
  - [x] Шаг 2.4: Дописать три функции в `TOOL_FUNCTIONS` (порядок: чтение → запись, т.е. после существующих).
- [x] **Этап 3: Тестирование**
  - [x] Шаг 3.1: В `tests/test_brain_mcp.py` обновить `TestToolSurface.EXPECTED` до 9 имён (иначе `test_all_six_tools_present` падает).
  - [x] Шаг 3.2: Добавить `TestListLinks`: (а) в скелете `make_project()` создать пару файлов со связями `[[BUG-001]]` и битой `[[MISSING-999]]`; (б) пустой query → сводка с числом битых; (в) query `BUG-001` → исходящие/обратные; (г) неизвестный query → `❓`; (д) `root` в сигнатуре (см. `test_search_memory_accepts_root_override`).
  - [x] Шаг 3.3: Добавить `TestListClaims`: (а) без локов → «Свободно»; (б) создать лок через `locks.claim_task(..., root=...)` → вывод содержит task/agent и маркер; (в) `root` в сигнатуре.
  - [x] Шаг 3.4: Добавить `TestGetStats`: (а) текстовый режим содержит «ДАШБОРД» и секции; (б) `as_json=True` → валидный JSON с ключами `sections`/`claims`/`wiki`; (в) пустой скелет проекта не падает (fail-soft).
  - [x] Шаг 3.5: Прогнать весь suite: `python -m unittest discover -s tests -v` — 0 failures, допустим 1 skip (SDK).
- [x] **Этап 4: Документирование и сдача**
  - [x] Шаг 4.1: `README.md` — +3 строки в таблицу MCP-инструментов (`list_links` — вики-связи и backlinks; `list_claims` — активные локи агентов; `get_stats` — дашборд здоровья памяти, `as_json`).
  - [x] Шаг 4.2: `agents/architecture/CODEBASE_MAP.md` — «6 инструментов» → «9 инструментов» (дерево + таблица файлов с перечнем функций).
  - [x] Шаг 4.3: `agents/STATUS.md` — строка MCP-сервера (9 инструментов), обновить счётчик тестов и «Последнее обновление».
  - [x] Шаг 4.4: `agents/tasks/active_task.md` — отметить закрытым пункт про MCP-инструменты (ссылка на PLAN-007).
  - [x] Шаг 4.5: Смоук вживую: `python -c "import sys; sys.path.insert(0,'agents/mcp'); import brain_mcp; print(brain_mcp.list_links()); print(brain_mcp.list_claims()); print(brain_mcp.get_stats(as_json=True)[:200])"` — без пакета `mcp` (инструменты-функции работают без SDK).
  - [x] Шаг 4.6: `python agents/tools/brain.py sync --check` — без дрейфа; зафиксировать сессию в `agents/history/` (запись сессии — на стороне родительской сессии при handoff).

---

## 4. 🛡️ Риски, сайд-эффекты и план отката

- **`TestToolSurface.EXPECTED` сломается** — strict-тест на ровно 6 имён. Mitigation: обновление теста тем же изменением (Шаг 3.1, до запуска CI).
- **Сайд-эффекты импорта** `links.py`/`locks.py`/`stats.py` на уровне модуля (reconfigure stdout, env) — Mitigation: ленивый импорт внутри функций (паттерн уже применён в `search_memory`/`end_session`).
- **Дублирование формата** вместо переиспользования — запрещено: только делегирование в `links_for`/`list_claims`/`collect_stats`; приватные `_norm`, `_resolve` не импортировать.
- **Скорость `get_stats`** — полное сканирование markdown; на шаблоне < секунды, приемлемо. При желании позже — кэш, но вне рамок PLAN-007.
- **Секреты/безопасность:** инструменты read-only, ничего не пишут; `root` — только параметр функции. Повторить паттерн `search_memory` (уже работает в проде): если SDK подхватит `root` как экспорт-параметр — оставить как есть, проверив поведение на смоуке (Шаг 4.5).
- **Откат:** `git revert` одного коммита (изменения только добавляют функции и правят тесты/доки); `.mcp.json` и CLI не менялись — откат тривиален, данные памяти не затрагиваются.

---

## 5. 🧪 План тестирования и критерии приемки

1. Автоматические тесты: `python -m unittest discover -s tests -v` — существующие 214 + новые (ожидаемо ~12–15) проходят; 1 skip только для SDK (`TestServerWiring`).
2. Ручная проверка (Шаг 4.5, смоук без пакета `mcp`): три инструмента возвращают непустые строки на реальном проекте; `get_stats(as_json=True)` парсится `json.loads`.
3. Критерий «Готово» (Definition of Done):
   - [x] `TOOL_FUNCTIONS` содержит ровно 9 инструментов; каждый с docstring (проверяется существующим `test_tools_have_docstrings`).
   - [x] Новая логика НЕ дублирует парсинг — только вызовы `links`/`locks`/`stats` (ревью).
   - [x] Тесты: 0 failures, 1 skip; `TestToolSurface.EXPECTED` обновлён.
   - [x] `README.md`, `CODEBASE_MAP.md`, `STATUS.md`, `active_task.md` актуализированы.
   - [x] `brain.py sync --check` чист.
   - [x] Чек-лист плана выполнен `[x]`, статус плана → ✅ COMPLETED, запись в `agents/history/` (запись сессии — на стороне родительской сессии при handoff).
