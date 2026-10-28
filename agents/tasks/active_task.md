# 📋 Активная задача: TASK-003 — Исполняемые правила (sync, хуки, субагенты, MCP)

**Статус:** 🔵 IN_PROGRESS (Этапы 0–5 ✅ → Этап 6 ⏭: поиск FTS5 + детектор устаревания)  
**Дата создания:** 2026-10-27  
**Исполнитель:** MiMo (OpenCode)  
**Приоритет:** HIGH  
**Связанный план:** [`PLAN-003`](../plans/plan_003_executable_rules.md)  

---

## 🎯 Цель задачи
Превратить markdown-правила в исполняемый инструмент: единый источник правил + `brain.py sync`, хуки Claude Code, субагенты/skills/команды, MCP-сервер `brain-mcp`, пресеты стека, поиск по памяти. Согласовано с заказчиком 2026-10-27.

---

## 📌 Пошаговый чек-лист выполнения:

- [x] **Этап 0: Починка базы + тесты**
  - [x] 0.1: Заменить `file:///` → относительные ссылки (54 ссылки, 23 файла)
  - [x] 0.2: Валидатор считает `file:///` устаревшим форматом (WARN)
  - [x] 0.3: Удалён тестовый мусор `WT_001_testovyy_walkthrough.md`
  - [x] 0.4: `tests/test_second_brain.py` — 6 тестов (ссылки, integrity, brain CLI, плейсхолдеры)
  - [x] 0.5: CI `integrity.yml` — добавлен `python -m unittest discover -s tests`
  - [x] 0.6: Плейсхолдеры заполнены через `init_project.py` — 0 ошибок / 0 WARN
- [x] **Этап 1: Единый источник правил + `brain.py sync`**
  - [x] 1.1: Канон `agents/rules/CORE_RULES.md` + шаблоны-обёртки `agents/templates/sync/`
  - [x] 1.2: `brain.py sync` (рендер 5 конфигов, сохранение EOL)
  - [x] 1.3: `brain.py sync --check` + шаг в CI + `tests/test_sync.py`
  - [x] 1.4: Сверка форматов `.claude/` с документацией (официальный hooks reference)
- [x] **Этап 2: Хуки Claude Code**
  - [x] `.claude/settings.json` +4 скрипта в `agents/tools/hooks/` (gate, inject, lint, history)
  - [x] `tests/test_hooks.py` — 17 сценариев; секция 9 в `check_integrity.py`
- [x] **Этап 3: Субагенты, skills, слэш-команды**
  - [x] `.claude/agents/` — 7 ролей; `.claude/skills/` — 5 скиллов (зеркало Antigravity через sync); `.claude/commands/` — 6 команд
  - [x] `tests/test_claude_config.py` + BUG-001 (model frontmatter)
- [x] **Этап 4: brain-mcp**
  - [x] `agents/mcp/brain_mcp.py` — 6 инструментов (SDK optional, skipIf в тестах)
  - [x] `.mcp.json` — 7 пресетов, секреты `${ENV}`; `pyproject.toml` extra `[mcp]`; README; `tests/test_brain_mcp.py`
- [x] **Этап 5: Пресеты django-drf / aiogram-bot + пакет**
  - [x] `agents/presets/` — 4 пресета (django-drf, aiogram-bot, fastapi, nextjs) с агентами и скиллами
  - [x] `brain.py presets/preset/init --preset/upgrade` + `tests/test_presets.py` (17 тестов)
  - [x] Упаковка: entry point `brain`, package-data, CI-матрица 3.9/3.11/3.13
- [ ] **Этап 6: Поиск FTS5 + детектор устаревания**
- [ ] **Этап 7: Мультиагентность и контекст**
- [ ] **Этап 8: Документирование и сдача**

---

## 🧪 Критерии готовности (Definition of Done):
1. `check_integrity.py` — 0 ошибок, 0 WARN, битых `file:///` нет.
2. Тесты проходят в CI.
3. Правило «без плана нет кода» физически неисполнимо (PreToolUse exit 2).
4. Все конфиги тулс генерируются через `sync`, дрейф ловится CI.
