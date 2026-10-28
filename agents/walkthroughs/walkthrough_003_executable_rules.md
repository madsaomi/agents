# 🚀 Отчет о сдаче и демонстрации (Walkthrough): Исполняемые правила — sync, хуки, субагенты, MCP, пресеты, поиск FTS5, мультиагентность

> **Дата проведения:** 2026-10-28  
> **Исполнитель / Агент:** MiMo  
> **Связанный план:** [PLAN-003](../plans/plan_003_executable_rules.md)  
> **Связанная задача:** [TASK-003](../tasks/active_task.md)  
> **Итог валидации:** 🟢 ACCEPTED (Принято)  

---

## 1. 🎯 Что было реализовано
- **Цель:** Превратить markdown-правила шаблона «Второй Мозг» в исполняемые инструменты: единый источник правил + генерация конфигов, хуки, обеспечивающие соблюдение правил, субагенты/скиллы/команды, MCP-сервер, пресеты стеков, поиск по памяти и координация параллельных агентов.
- **Основной результат:** Правила проекта физически неисполнимы к обходу (хуки отклоняют), а вся память доступна инструментам (CLI/MCP/поиск) без порчи markdown-формата.

### Этапы (8 коммитов на `main`):

| Этап | Коммит | Содержание |
|---|---|---|
| 0. База | `86ffc69` | Относительные ссылки вместо `file:///` (54 шт.), первые тесты, плейсхолдеры, удалён тестовый walkthrough |
| 1. Правила | `41dfa78` | `agents/rules/CORE_RULES.md` (11 правил, вкл. prompt-injection), 5 `.tpl`-шаблонов, `brain.py sync [--check]`, CI-драйф-чек |
| 2. Хуки | `d938311` | `.claude/settings.json` + 4 хука Claude Code, Plan-first gate (deny через `permissionDecision`, fail-open), секрет-гард, инъекция контекста, линт, лог сессии |
| 3. Субагенты | `4b8f6a6` | 7 субагентов, 5 скиллов (+ зеркало Antigravity через `SYNC_MIRRORS`), 6 slash-команд, BUG-001 |
| 4. MCP | `2f4cffc` | `agents/mcp/brain_mcp.py` (6 инструментов), `.mcp.json` (7 пресетов, секреты `${ENV}`), extra `[mcp]` |
| 5. Пресеты | `abfb035` | 4 пресета стека (django-drf, aiogram-bot, fastapi, nextjs), `brain preset/init --preset/upgrade` (sha256-lock), пакет v0.4.0 с entry point `brain` |
| 6. Поиск | `5462202` | `brain.py search` на SQLite FTS5 (индекс `.brain_index.db`), детектор устаревания `CODEBASE_MAP.md` |
| 7. Мультиагентность | `b404095` | `brain.py claim/release/claims` (атомарные локи, heartbeat-TTL, git worktree), `dump --budget` |

### Ключевые созданные файлы:
- `[NEW]` `agents/rules/CORE_RULES.md` — единый источник правил проекта.
- `[NEW]` `agents/tools/search.py` — полнотекстовый поиск памяти (FTS5, stdlib).
- `[NEW]` `agents/tools/locks.py` — блокировки задач claim/release + git worktree.
- `[NEW]` `agents/mcp/brain_mcp.py` + `.mcp.json` — MCP-инструменты памяти и пресеты подключения.
- `[NEW]` `agents/presets/{django-drf,aiogram-bot,fastapi,nextjs}/` — пресеты стеков (манифесты, стандарты, CI, агенты, скиллы).
- `[NEW]` `.claude/{settings.json,agents/,skills/,commands/}` — хуки, субагенты, скиллы и команды Claude Code.
- `[NEW]` `tests/{test_sync,test_hooks,test_brain_mcp,test_presets,test_search,test_claim,test_dump_budget}.py` — 117 тестов.
- `[MODIFY]` `agents/tools/brain.py` — диспетчер CLI: `sync`, `search`, `presets/preset/upgrade`, `claim/release/claims`, `dump --budget`.
- `[MODIFY]` `agents/tools/check_integrity.py` — секции 9 (MCP/хуки) и 10 (актуальность CODEBASE_MAP).
- `[MODIFY]` `pyproject.toml`, `.github/workflows/integrity.yml`, `README.md`, `agents/architecture/CODEBASE_MAP.md`.

---

## 2. 🧪 Результаты автоматического тестирования

### Юнит-тесты (stdlib unittest):
```bash
python -m unittest discover -s tests
```
**Результат:** `Ran 117 tests ... OK (skipped=1)` — skip только серверного каркаса MCP без установленного SDK (опциональный extra `[mcp]`).

### Целостность и дрейф конфигов:
```bash
python agents/tools/check_integrity.py   # 10 секций, ошибок: 0, WARN: 0
python brain.py sync --check             # все 5 конфигов + 1 зеркало == канону
```
**Результат:** 100% порядок; дрейф канона ловится CI (матрица Python 3.9/3.11/3.13).

### Демонстрация ключевых возможений:
```bash
python brain.py search "jwt" --limit 5        # FTS5: префикс, фразы, кириллица, snippet+bm25
python brain.py claim TASK-003 --worktree     # атомарный лок + git worktree + ветка task/...
python brain.py claims                        # список блокировок (🟢/💀/❓)
python brain.py dump --budget 800             # 11 207 → ~730 токенов (автосуммаризация)
python brain.py preset django-drf             # пресет стека (свои правки не затираются)
python brain.py upgrade                       # обновление шаблонов без потери данных
```

---

## 3. ✅ Проверка критериев готовности (Definition of Done)

- [x] Все 8 этапов `PLAN-003` выполнены (см. [план](../plans/plan_003_executable_rules.md)).
- [x] `check_integrity.py` — 0 ошибок, 0 WARN, битых `file:///` нет.
- [x] 117 тестов проходят локально и в CI (матрица 3.9/3.11/3.13).
- [x] Правило «без плана нет кода» исполняется хуком (отказ через `permissionDecision: "deny"`, контекст — `additionalContext`, fail-open при сбое).
- [x] Все конфиги AI-инструментов генерируются через `sync` из `CORE_RULES.md`, дрейф ловится CI.
- [x] Секреты только через `${ENV}` (валидируется в `check_integrity`), в репозиторий не попадают.
- [x] Поиск/локи/бюджет тестируемы (параметры `root`/`db_path`), тесты изолированы во временных каталогах.
- [x] Документация обновлена: README, `CODEBASE_MAP.md`, `STATUS.md`, этот walkthrough.

---

## 4. 📌 Как пользоваться (мини-гайд)

| Задача | Команда |
|---|---|
| Изменить правила проекта | Правь **только** `agents/rules/CORE_RULES.md`, затем `python brain.py sync` |
| Найти что-то в памяти | `python brain.py search "запрос"` (`--reindex` — перестроить индекс) |
| Забрать задачу параллельному агенту | `python brain.py claim TASK-XXX [--worktree]` → `release TASK-XXX` |
| Контекст в веб-чат под лимит | `python brain.py dump --budget 4000` |
| Новый проект на своём стеке | `python brain.py init --preset django-drf` (или `fastapi`, `nextjs`, `aiogram-bot`) |
| Обновить шаблон | `python brain.py upgrade` (правки пользователя и история не затираются) |
| MCP-инструменты | `pip install ".[mcp]"` → `python agents/mcp/brain_mcp.py` |

---

## 5. ⚠️ Известные ограничения и риски
- Оценка токенов в `dump --budget` грубая (~3 символа/токен) — это эвристика, не точный подсчёт.
- TTL heartbeat локов (45 мин) требует периодического повторного `claim` при долгих сессиях (настраивается `BRAIN_LOCK_TTL_MINUTES`).
- Frontmatter `model` субагента может игнорироваться Claude Code — [BUG #44385](https://github.com/anthropics/claude-code/issues/44385) (BUG-001, обход задокументирован).
- Серверная часть `brain_mcp.py` тестируется только при установленном SDK (extra `[mcp]`, Python 3.11+).
