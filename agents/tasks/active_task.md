# 📋 Активная задача: TASK-011 — `brain graph`: mermaid-граф связей памяти

**Статус:** ✅ COMPLETED (Завершена)  
**Дата создания:** 2026-11-01  
**Дата завершения:** 2026-11-01  
**Исполнитель:** ZCode (GLM)  
**Приоритет:** MEDIUM  
**Связанный план:** [`PLAN-012`](../plans/plan_012_brain_graph_mermaid-graf_svyazey.md)  

---

## Чек-лист

- [x] **Этап 1:** `agents/tools/graph.py` — `collect_graph(root)` (узлы из `links.build_index`, рёбра dedupe из `links.find_links`, битые отдельно, self-ссылки отброшены), `render_mermaid(graph, max_nodes)` (топ-N по степени, id `m<N>`/`p<N>`, подписи в кавычках с эмодзи разделов, фантомы `-.->`), `format_summary()`
- [x] **Этап 2:** brain.py — subparser `graph [--json] [--max N]` + `cmd_graph`; тур 4/7 — строка
- [x] **Этап 3:** `tests/test_graph.py` — 14 тестов (узлы/рёбра/dedupe, self-link, unresolved, секции, mermaid-формат, лимит, пустая память, JSON, CLI-смоуки ×3). По ходу: (а) секция парсится из `agents/<раздел>/...` (каталог проекта сам называется agents); (б) сводка вынесена в `format_summary` для диспетчера. Suite: **295 tests, 0 failures, 1 skip**
- [x] **Этап 4:** README (+1 команда), STATUS (295, фаза 003…012), CODEBASE_MAP (дерево+таблица), backlog (TASK-011 → Выполнено), `sync --check` чист, integrity 100%, коммит `feat(plan-012)`, запись в history

## Примечания

- На живом репо: 38 узлов, 2 ребра (планы → BUG-001), 2 битые связи на `MISSING-999` (из смоков тестов) — рисуются пунктиром.
- Mermaid-блок вставляется в GitHub/README без доработок.

## Следующая задача

- Из backlog: TASK-010 (PyPI v0.5.0, разблокирована) / TASK-012 (brain digest) / TASK-015 (root-остатки) — по выбору заказчика.
