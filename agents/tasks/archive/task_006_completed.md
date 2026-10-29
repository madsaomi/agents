# 📋 Завершённая задача: TASK-006 — Кросстулумность: Codex и OpenCode

> **Статус:** ✅ COMPLETED
> **Даты:** 2026-10-29 — 2026-10-29
> **План:** [plan_006_codex_opencode.md](../../plans/plan_006_codex_opencode.md)
> **Закрыта через:** `python brain.py end --task TASK-006`

---

## Итог

Шаблон перестал быть Claude-first: `brain.py sync` рендерит исполняемые правила для всех
4 инструментов. Выполнены этапы 1–4 плана:
1. **Codex** (Этап 1): `.codex/hooks.json` — те же 4 python-хука (`permissionDecision`-контракт идентичен Claude);
   хуки `pre_tool_gate`/`post_edit_lint` доработаны под `apply_patch` (пути из патча `*** Update File:`);
   5 скиллов зеркалятся в `.agents/skills/`.
2. **OpenCode** (Этап 2): `opencode.jsonc` (7 MCP в формате V2, секреты `{env:VAR}`, deny-правила секретов);
   трансформа `transform_opencode_md()` — 6 команд и 7 агентов (read-only → deny edit/shell);
   скиллы в `.opencode/skills/`.
3. **Плагин** (Этап 3): `.opencode/plugins/second_brain/index.ts` — `permission.evaluate` → тот же
   `pre_tool_gate.py`, fail-open; живой deny подтверждён в сессии `opencode run`.
4. **Тесты** (Этап 4): +19 автотестов (214 всего), README «Кросстулумность», CODEBASE_MAP, STATUS.

## Закрытые пункты

- [x] `hooks.json.tpl` + зеркала скиллов Codex; смоук JSON + deny на секреты в патче.
- [x] `opencode.jsonc.tpl` (7 MCP) + `sync --check` чист (7 конфигов, 10 зеркал, 13 трансформ).
- [x] Трансформы команд/агентов: `$ARGUMENTS` сохраняется, Claude-ключи выброшены, `mode: subagent` добавлен.
- [x] Плагин OpenCode грузится (`opencode plugin list`) и гейтит чтение секретов (живой тест `.env.test`).
- [x] 214 тестов зелёные, integrity 0/0, документация обновлена.

## Открытые пункты

- [ ] Codex CLI на машине разработчика не установлен — живой смоук trust-review `/hooks` не проводился.
- [ ] MCP-инструменты `list_links`/`list_claims`/`get_stats` — brain-mcp отстаёт от CLI (PLAN-007).
- [ ] Секрет-гард для чтения через shell-обход (Codex: хук не полная граница защиты — задокументировано).
