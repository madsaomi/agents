# 📐 План реализации: PLAN-012 — `brain graph`: mermaid-граф связей памяти

> **Статус:** ✅ COMPLETED  
> **Дата создания:** 2026-11-01  
> **Дата завершения:** 2026-11-01  
> **Автор / Агент:** ZCode (GLM)  
> **Связанная задача:** [TASK-011](../tasks/active_task.md) (из backlog)  
> **Целевая ветка / Ревизия:** main

---

## 1. 🎯 Цель и контекст

- **Проблема / Задача:** вики-связи `[[...]]` уже резолвятся (`links.py`, PLAN-005) и показываются списком (`brain links`), но структуру памяти «одним взглядом» не видно: какие записи хабы, что висит изолированно, где битые связи. Для вставки в README/PR/веб-чат нужен готовый mermaid-граф.
- **Ожидаемый технический результат:** `python brain.py graph [--json] [--max N]` — mermaid-блок: узлы-записи (с эмодзи разделов), сплошные рёбра `-->` для разрешённых `[[связей]]`, пунктирные `-.->` на фантомные узлы для битых. Лимит узлов по степени связности (`--max`, default 40). Всё stdlib, переиспользование `links.find_links`/`build_index` без дублирования резолюции.

---

## 2. 🔍 Анализ и затронутые компоненты

### Затронутые файлы:
- `[NEW]` `agents/tools/graph.py` — `collect_graph(root=None) -> dict` (узлы/рёбра/битые), `render_mermaid(graph, max_nodes=40) -> str`, `main()`.
- `[MODIFY]` `agents/tools/brain.py` — subparser `graph [--json] [--max N]`, `cmd_graph`, HANDLERS.
- `[NEW]` `tests/test_graph.py` — фикстура-скелет со связями.
- `[MODIFY]` `README.md` (+1 строка команд), `agents/STATUS.md`, `agents/architecture/CODEBASE_MAP.md`, `agents/tasks/backlog.md` (TASK-011 → Выполнено), `agents/tasks/active_task.md`.
- `[MODIFY]` `agents/tools/tour.py` — экран 4/7 (+1 строка: graph).

### Зависимости и влияние:
- Новые библиотеки: **НЕТ**. Импорт `links` (публичные `find_links`, `build_index`), лениво внутри collect.
- Влияние на существующие API: только добавление. `links.py` не меняется.
- Breaking changes: **НЕТ**.

### Контракт `graph.py`:

**`collect_graph(root=None)`** (rel-пути — относительно `agents/`, как в links.py):
- `nodes`: dict `rel → {label: stem, section: <первая часть rel>}` — из значений `links.build_index`.
- `edges`: dedupe `src → dst` по паре с счётчиком (`links.find_links`, только `dst is not None`, без `src == dst`).
- `unresolved`: связи с `dst is None` и не-плейсхолдер (`{src, target}`).
- `summary`: {nodes, edges, unresolved}.

**`render_mermaid(graph, max_nodes=40)`**:
- Топ-N узлов по степени (входящие+исходящие+битые-источники); изолированные — первыми на отсечение.
- Идентификаторы `m0…mN`, подписи в кавычках: `m0["📐 plan_003_executable_rules"]` (эмодзи раздела: plans 📐, bugs 🐛, decisions 🏛️, tasks 📋, history 📝, walkthroughs 🚀, rules 📜, прочее 📄).
- Рёбра: `m0 --> m1`; битые: `m0 -.-> p0[["⚠️ target"]]` (фантомы, до 10).
- Шапка `graph TD`; вывод — fenced-блок ` ```mermaid `.
- `--json` → `json.dumps(graph, ensure_ascii=False, indent=2)`.

---

## 3. 📝 Пошаговый план реализации (Atomic Steps)

- [x] **Этап 1: Модуль**
  - [x] Шаг 1.1: `agents/tools/graph.py`: collect/render/main (reconfigure stdout, паттерн doctor.py).
- [x] **Этап 2: Интеграция**
  - [x] Шаг 2.1: brain.py — парсер + `cmd_graph`; тур 4/7 — строка.
- [x] **Этап 3: Тестирование**
  - [x] Шаг 3.1: `tests/test_graph.py`: (а) скелет с 3 записями и связями → узлы/рёбра/dedupe/счётчики; (б) битая `[[MISSING-999]]` → unresolved, фантом в mermaid; (в) self-link не даёт ребра; (г) mermaid: `graph TD`, кавычки-подписи, `-->`, `-.->`, эмодзи раздела; (д) `--max` отсекает до N узлов по степени; (е) json-сериализуемость; (ж) CLI-смоук: `brain.py graph` на живом репо rc 0 + `graph TD` в выводе, `--json` парсится.
  - [x] Шаг 3.2: Полный suite — 0 failures (ожидаемо 281 → ~291).
- [x] **Этап 4: Сдача**
  - [x] Шаг 4.1: README, STATUS, CODEBASE_MAP, backlog (TASK-011 закрыт), active_task, тур.
  - [x] Шаг 4.2: `sync --check` чист; коммит `feat(plan-012): ...`; запись в history.

---

## 4. 🛡️ Риски, сайд-эффекты и план отката

- **Mermaid-синтаксис ломается на спецсимволах** (точки, кириллица, эмодзи в подписях) — Mitigation: подписи всегда в двойных кавычках; id — только `m<N>`/`p<N>`; тест (г) фиксирует формат.
- **Большой граф в реальном проекте** (десятки записей) — Mitigation: `--max` по степени связности; summary в выводе показывает полный размер.
- **Кириллические stem в подписях** — валидно внутри кавычек; проверяется тестом на живом репо.
- **Дублирование резолюции** — запрещено: только `links.find_links`/`build_index`; приватное `_resolve`/`_norm` не импортируется.
- **Откат:** `git revert` одного коммита; новое имя команды ни с чем не конфликтует.

---

## 5. 🧪 План тестирования и критерии приемки

1. Автоматические тесты: `python -m unittest discover -s tests -v` — 0 failures, 1 skip (SDK).
2. Ручная проверка: `python brain.py graph` на живом репо — mermaid вставляется в markdown-просмотрщик (GitHub) и рендерится; `--json` парсится; `--max 10` ограничивает.
3. Критерий «Готово» (Definition of Done):
   - [x] `brain graph` даёт валидный mermaid с рёбрами и фантомами битых связей; лимит работает.
   - [x] Тесты 0 failures; sync --check чист; доки актуальны; TASK-011 закрыт в бэклоге; план → ✅ COMPLETED; запись в history.
