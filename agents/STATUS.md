# 📊 Текущий статус проекта (STATUS.md)

**Проект:** Second Brain Template  
**Описание:** Универсальный шаблон долговременной памяти, регламентов и исполняемых правил для AI-агентов  
**Технологический стек:** Python 3.9+ (stdlib-only, опциональный extra `[mcp]`), SQLite FTS5, Markdown, Git, Claude Code / Cursor / Windsurf / Antigravity / Codex / OpenCode  
**Последнее обновление:** 2026-11-01 (Западная Азия (зима))  
**Ответственный агент:** AI Assistant
**Текущая фаза:** 🟢 PLAN-003…013 закрыты (последний — финальный код перед релизом), готово к PyPI v0.5.0  

---

## 🚦 Состояние подсистем

| Подсистема / Компонент | Статус | Комментарий |
|---|---|---|
| **Экосистема «Второго Мозга» (`agents/`)** | 🟢 Готово | Память, планы, задачи, баги, ADR, история |
| **Единый источник правил (`CORE_RULES.md` + sync)** | 🟢 Готово | 11 правил; `brain.py sync [--check]`, дрейф ловит CI |
| **Исполняемые хуки Claude Code** | 🟢 Готово | Plan-first gate, секрет-гард, инъекция контекста, линт, лог сессии |
| **Субагенты / скиллы / команды** | 🟢 Готово | 7 агентов, 5 скиллов (+ зеркала Antigravity/Codex/OpenCode), 6 команд |
| **MCP-сервер `brain-mcp`** | 🟢 Готово | 9 инструментов (PLAN-007: +`list_links`/`list_claims`/`get_stats`), `.mcp.json` с 7 пресетами, extra `[mcp]` |
| **Кросстулумность Codex и OpenCode (PLAN-006)** | 🟢 Готово | `sync` рендерит `.codex/hooks.json` (те же 4 хука, trust-review `/hooks`), `opencode.jsonc` (7 MCP), `.opencode/{commands,agents,skills}` (6+7+5), плагин `second_brain` — Plan-First-гейт через `permission.evaluate` (fail-open) |
| **Пресеты стека + упаковка** | 🟢 Готово | django-drf / aiogram-bot / fastapi / nextjs; entry point `brain` |
| **Поиск по памяти (FTS5)** | 🟢 Готово | `brain.py search`, индекс `.brain_index.db`, детектор устаревания карты |
| **Мультиагентность (claim/release + dump --budget)** | 🟢 Готово | Атомарные локи с heartbeat-TTL, worktree, сжатие контекста под лимит |
| **Безопасность и дашборд (PLAN-004)** | 🟢 Готово | Секрет-сканер в check/pre-commit/CI, `brain stats [--json]`, GH-аннотации `::error file=`, `brain tour` |
| **Связи и теги (PLAN-005)** | 🟢 Готово | Вики-связи `[[...]]` + обратные ссылки (`brain links`), frontmatter-теги с авто-миграцией индекса, фильтры `search --tag/--since`, секции в `stats` |
| **Диагностика окружения (PLAN-008)** | 🟢 Готово | `brain doctor [--json]`: Python/FTS5/git/свежесть индекса/буфер/extra `[mcp]`/запись; warn не валят exit code, хинты по каждой проблеме |
| **Надёжность ядра CLI (PLAN-009)** | 🟢 Готово | Смок-тесты подкоманд `brain.py` (subprocess), `main()` → `cmd_*` + `HANDLERS`, тур → `tour.py`; BUG-002 (`index_memory` игнорировал root) исправлен; pre-commit хук установлен в самом шаблоне |
| **Жизненный цикл памяти (PLAN-010)** | 🟢 Готово | `brain handoff [--copy]` — эстафета (7 секций, fail-soft); `brain archive [--force]` — архив задачи + сброс active_task; memory lint (секция 12 check) — дисциплина записей warn-ами |
| **Root-aware фабрики (PLAN-011)** | 🟢 Готово | Все 7 фабрик артефактов (`plan/bug/adr/task/walkthrough/init/end`) принимают `root`: цели — от root проекта, шаблоны — ресурсы модуля; CLI-регресс из tmp-скелета (класс BUG-002 закрыт) |
| **Mermaid-граф связей (PLAN-012)** | 🟢 Готово | `brain graph [--json] [--max N]`: узлы-записи с эмодзи разделов, рёбра `-->` по `[[связям]]`, битые — пунктиром на фантомы; лимит по степени связности |
| **Финальный код (PLAN-013)** | 🟢 Готово | `check [--fix]` и `dump` уважают root (класс BUG-002 закрыт полностью); `brain digest [--tokens N] [--copy]` — компактная сводка поверх handoff/stats |
| **Тесты и CI** | 🟢 Готово | 305 unittest (1 skip — SDK), матрица Python 3.9/3.11/3.13 |
| **Документация** | 🟢 Готово | README, CODEBASE_MAP, walkthrough_003, AGENTS.md |

> *Обозначения статусов: 🟢 Готово / Работает | 🟡 В разработке / Требует внимания | 🔴 Заблокировано / Ошибка | ⚪ Не начато*

---

## 🎯 Что делается прямо сейчас (Текущий фокус):
- **PyPI v0.5.0 (TASK-010)** — подготовка релиза: см. 👉 **[`agents/plans/plan_014_pypi_v050_podgotovka_reliza.md`](plans/plan_014_pypi_v050_podgotovka_reliza.md)**; остаётся шаг публикации с токеном заказчика

---

## 🚧 Блокеры и известные риски:
- Критических блокеров нет.
- Известный внешний баг: [anthropics/claude-code#44385](https://github.com/anthropics/claude-code/issues/44385) — frontmatter `model` субагента может игнорироваться (BUG-001; обход: передавать model явно при вызове).

---

## 📅 Ближайшие вехи (Milestones):
1. **M1 (Исполняемые правила):** ✅ Завершено — PLAN-003 (sync, хуки, субагенты, MCP, пресеты, поиск, мультиагентность).
2. **M2 (Распространение):** 🟡 Шаблон опубликован как пакет `second-brain-template`; раскатка в целевые проекты через `brain init --preset <стек>`.
3. **M3 (Обратная связь):** Сбор кейсов использования и доработка пресетов/хуков по реальным проектам.
4. **M4 (Релиз):** Публикация в реестры (PyPI/маркетплейсы агентов), версии > 0.4.0.
