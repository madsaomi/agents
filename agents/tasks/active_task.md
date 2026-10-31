# 📋 Активная задача: TASK-006 — Кросстулумность: Codex и OpenCode

**Статус:** ✅ COMPLETED (Завершена)  
**Дата создания:** 2026-10-29  
**Дата завершения:** 2026-10-29  
**Исполнитель:** MiMo (OpenCode)  
**Приоритет:** HIGH  
**Связанный план:** [`PLAN-006`](../plans/plan_006_codex_opencode.md)  
**Архив:** [`task_006_completed.md`](archive/task_006_completed.md)  

---

## Итог

`brain.py sync` рендерит исполняемые правила для всех 4 инструментов: Codex (`.codex/hooks.json`,
`.agents/skills/`), OpenCode (`opencode.jsonc`, `.opencode/{commands,agents,skills}`,
плагин `second_brain` — Plan-First-гейт через `permission.evaluate`, fail-open). Хуки
`pre_tool_gate`/`post_edit_lint` расширены под `apply_patch` Codex. 214 тестов, integrity 0/0,
`sync --check` чист.

## Открытые пункты

- [ ] Живой смоук Codex `/hooks` (trust-review) — CLI не установлен на машине разработчика.
- [x] MCP-инструменты `list_links` / `list_claims` / `get_stats` — закрыто в [`PLAN-007`](../plans/plan_007_mcp_links_claims_stats.md): три read-only инструмента добавлены в `brain-mcp` (9 инструментов), 226 тестов.

## Следующая задача

- Определяется заказчиком/агентом при входе в проект (кандидаты: MCP-инструменты связей, PyPI v0.5.0,
  `brain digest`/`brain graph`, doctor).
