# 📐 План реализации: PLAN-015 — Кристально чистый шаблон (очистка памяти разработки)

> **Статус:** ✅ COMPLETED
> **Дата завершения:** 2026-11-01  
> **Дата создания:** 2026-11-01  
> **Автор / Агент:** ZCode (GLM)  
> **Целевая ветка / Ревизия:** новая main (orphan) + ветка-бэкап `dev-history`

---

## 1. 🎯 Цель и контекст

- **Проблема:** репозиторий шаблона несёт всю память разработки самого шаблона (30 сессий history, 12 планов, задачи/архив, баги BUG-001/002, ADR, walkthroughs, профили агентов). При клонировании шаблона в целевой проект эта память едет вместе с ним.
- **Результат:** `main` = один коммит «чистый шаблон» (память разработки вычищена до эталонных примеров и заглушек); полная история разработки сохранена в ветке **`dev-history`** (пушится на origin) — anti-pattern №2 (уничтожение памяти) соблюдён: ничего не теряется, память переезжает.

## 2. Что вычищается / что остаётся

**Вычищается (проектная память разработки):**
- `agents/history/session_*.md` — все, кроме `session_000_init_example.md`
- `agents/plans/plan_*.md` — все
- `agents/tasks/` — active_task → заглушка; `archive/task_*.md` — все
- `agents/bugs_and_fixes/BUG_001*, BUG_002*` (пример BUG_000 остаётся)
- `agents/decisions/ADR_001*` (пример ADR_000 остаётся)
- `agents/walkthroughs/walkthrough_*.md` — все
- `agents/registry/agent_*.md` — все профили (шаблон профиля остаётся)
- `agents/tasks/backlog.md` → заглушка; `agents/tools/context_dump.md` (мусор) — удалить
- `.brain_index.db` — пересоздать после очистки

**Остаётся (продукт шаблона):**
- `agents/rules/`, `templates/`, `presets/`, `tools/`, `mcp/`, `architecture/CODEBASE_MAP.md`, `AGENT_GUIDE.md`, `GLOSSARY.md`, `product/PRD.md`, `ROADMAP.md`
- `STATUS.md` — сохраняется таблица возможностей шаблона; сбрасываются «Текущий фокус»/задачи (дев-специфика)
- Конфиги инструментов: `.claude/`, `.codex/`, `.opencode/`, `.cursor/`, `.windsurf*`, `CLAUDE.md`, `.mcp.json`, CI, `pyproject.toml` (0.5.0)

## 3. Шаги

- [x] Шаг 1: план + запись сессии — коммитом в ТЕКУЩУЮ (старую) историю
- [x] Шаг 2: ветка `dev-history` от HEAD; push `dev-history` на origin (память закреплена на GitHub)
- [x] Шаг 3: вычистка файлов (git rm), сброс STATUS/backlog/active_task
- [x] Шаг 4: верификация чистого дерева: unittest 305, integrity, sync --check, doctor
- [x] Шаг 5: `git checkout --orphan clean-main` → один коммит «Second Brain Template v0.5.0 — clean template» → rename в main
- [x] Шаг 6: force-push `main` на origin; тег `v0.5.0` на GitHub

## 4. Риски

- Необратимость на origin — mitigated: явное подтверждение заказчика; бэкап-ветка dev-history пушится ДО перезаписи main.
- Integrity-секции на чистом дереве (кол-во сессий, плейсхолдеры, карта) — верифицируются на шаге 4; заглушки не содержат `{{плейсхолдеров}}`.
- Откат: `git reset --hard dev-history` (до force-push) / восстановление из origin/dev-history (после).

## 5. DoD

- [x] `git log main` = 1 коммит; клон репозитория не несёт памяти разработки.
- [ ] Все проверки зелёные на чистом дереве; dev-history на GitHub содержит полную историю.
