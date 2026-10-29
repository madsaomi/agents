# 📐 План реализации: PLAN-006 — Кросстулумность: Codex и OpenCode

> **Статус:** ✅ DONE (2026-10-29, все 4 этапа сданы: 214 тестов, integrity 0/0, sync --check чист)
> **Дата создания:** 2026-10-29  
> **Автор / Агент:** MiMo (OpenCode)  
> **Связанная задача:** [TASK-006](../tasks/active_task.md)  
> **Целевая ветка / Ревизия:** main  

---

## 1. 🎯 Цель и контекст

- **Проблема / Задача:** Шаблон позиционируется как 4-инструментный (Claude Code / Codex / OpenCode / Antigravity), но `brain.py sync` рендерит конфиги только для Claude/Cursor/Windsurf/Copilot (5 файлов) + одно зеркало Antigravity. Codex читает только `AGENTS.md` (правила) — без хуков и репозиторных скиллов; OpenCode — вообще без конфига: ни MCP, ни команд, ни сабагентов, ни Plan-First-гейта. Исполняемые правила из PLAN-003 работают только в Claude Code.
- **Ожидаемый результат:** `sync` рендерит для всех 4 инструментов: Codex получает `.codex/hooks.json` (те же 4 хука) и `.agents/skills/` (все 5 скиллов); OpenCode получает `opencode.jsonc` (MCP), `.opencode/commands/` (6 команд), `.opencode/agents/` (7 сабагентов), `.opencode/skills/` (5 скиллов) и локальный плагин с Plan-First-гейтом.

### Факты официальной документации (сверено 2026-10-29)

| Инструмент | Факт |
|---|---|
| **Codex: промпты** | `~/.codex/prompts` (custom prompts) — **устарели** (deprecated v0.117+), рендерить `.codex/prompts/` НЕЛЬЗЯ. Правила → `AGENTS.md` (уже есть), скиллы → `$REPO_ROOT/.agents/skills/<name>/SKILL.md` |
| **Codex: хуки** | `<repo>/.codex/hooks.json`; **те же имена событий** (SessionStart, PreToolUse, PostToolUse, Stop) и **та же форма отказа** `hookSpecificOutput.permissionDecision: deny` и `additionalContext`, что у Claude Code → наши python-хуки переиспользуются почти без правок. Путь к скриптам: `$(git rev-parse --show-toplevel)/...`. Нужен trust-review через `/hooks` (документировать) |
| **Codex: stdin** | Присылает те же поля `tool_name` / `tool_input`, что и Claude |
| **OpenCode: конфиг** | `opencode.json(c)` в корне проекта, `$schema: https://opencode.ai/config.json`; MCP → `mcp.servers` в формате `{type: local, command: [...]}`; секреты — `{env:VAR}` |
| **OpenCode: команды** | `.opencode/commands/*.md`, frontmatter `description`/`agent`/`model`, тело — шаблон промпта; `$ARGUMENTS` и `$1..$n` — **общие с Claude Code** → тело переносится как есть |
| **OpenCode: агенты** | `.opencode/agents/*.md`, frontmatter `description`, `mode`, `permissions`; поля Claude `name`(=файл), `tools`, `model: opus` — **нельзя** (V2 deprecated/невалидно) → трансформа: убрать `name`/`tools`/`model`, добавить `mode: subagent`, read-only агентам — `permissions: deny edit+shell` |
| **OpenCode: скиллы** | авто-обнаружение в `.opencode/skills/<name>/SKILL.md` (формат SKILL.md общий со стандартом agentskills.io) |
| **OpenCode: плагин** | `.opencode/plugins/<id>/index.ts`, `import { Plugin } from "@opencode/plugin"`, грузится автоматически; гейт → `ctx.permission.hook("evaluate")` (можно выставить `effect: "deny"` + `message`) |

---

## 2. 🔍 Анализ и затронутые компоненты

### Затронутые файлы:
- `[NEW]` `agents/templates/sync/hooks.json.tpl` — хуки Codex: SessionStart (inject_context), PreToolUse `Edit|Write`/`Read`/`Bash` (pre_tool_gate), PostToolUse `Edit|Write` (post_edit_lint), Stop (session_log); команды через `$(git rev-parse --show-toplevel)`.
- `[NEW]` `agents/templates/sync/opencode.jsonc.tpl` — `$schema` + `mcp.servers` (7 серверов из `.mcp.json`, формат OpenCode, секреты `${VAR}` → `{env:VAR}`).
- `[NEW]` `.opencode/plugins/second_brain/index.ts` — Plan-First/секрет-гейт: `permission.hook("evaluate")` → spawn тех же `agents/tools/hooks/pre_tool_gate.py` (единый источник правды), deny при `permissionDecision: deny`, **fail-open** при любой ошибке (как у Claude-хуков).
- `[MODIFY]` `agents/tools/brain.py` — sync: новые SYNC_SPECS (2 шаблона), SYNC_MIRRORS (все 5 скиллов → `.agents/skills/` и `.opencode/skills/`), новый тип SYNC_TRANSFORMS (команды и агенты Claude → OpenCode) в `render_sync_configs()`.
- `[NEW]` `.codex/hooks.json`, `opencode.jsonc`, `.opencode/commands/*.md` (6), `.opencode/agents/*.md` (7), `.opencode/skills/*` (5), `.agents/skills/*` (+4) — генерируемые артефакты (коммитятся, как и 5 Claude-конфигов).
- `[MODIFY]` `tests/test_sync.py` — тесты рендера Codex/OpenCode; `[NEW]` `tests/test_opencode_render.py` — трансформы команд/агентов + плагин (структура/валидность).
- `[MODIFY]` `README.md`, `agents/architecture/CODEBASE_MAP.md`, `agents/STATUS.md` — раздел «Кросстулумность».
- `[DELETE]` — нет.

### Зависимости и влияние:
- Новые библиотеки: НЕТ для Python-части. Плагин — один `index.ts` (TypeScript, исполняется встроенным в OpenCode bun, **без npm install** — локальный плагин без package.json грузится с корнем файла `index.ts`).
- `.mcp.json` (Claude-формат) остаётся нетронутым — `opencode.jsonc` его дублирует в своём формате (оба коммитятся).
- Риск Breaking changes: НЕТ — только новые цели рендера; `sync --check` станет строже (новые файлы должны существовать и совпадать).
- **Важно:** `.opencode/**` и `opencode.jsonc` — это артефакты рендера, правка руками = дрейф, который поймает `sync --check` (как у CLAUDE.md).

---

## 3. 📝 Пошаговый план реализации (Atomic Steps)

- [ ] **Этап 1: Codex — хуки и скиллы**
  - [ ] 1.1: `hooks.json.tpl` — 6 хуков с теми же скриптами; проверить по доке Codex: `matcher` (`Edit|Write`, `Read`, `Bash`), `command` с git-root, таймауты; stdout-контракты хуков уже совместимы (проверено: `inject_context` → JSON `additionalContext`, `pre_tool_gate` → JSON `permissionDecision`, `session_log` → без вывода).
  - [ ] 1.2: SYNC_MIRRORS — все 5 скиллов `.claude/skills/*/SKILL.md` → `.agents/skills/<имя каталога>/SKILL.md` (существующее `second_brain` не переименовывать).
  - [ ] 1.3: Смоук: `sync` генерирует `.codex/hooks.json`; JSON валиден; пути к скриптам существуют.
- [ ] **Этап 2: OpenCode — конфиг, команды, агенты, скиллы**
  - [ ] 2.1: `opencode.jsonc.tpl` — `$schema` + `mcp.servers` (brain/filesystem/github/postgres/context7/playwright/sentry → `{"type":"local","command":[...],"env":{...}}`, секреты через `{env:VAR}`).
  - [ ] 2.2: SYNC_TRANSFORMS: команды `.claude/commands/*.md` → `.opencode/commands/*.md` (сохранить `description`, тело как есть — `$ARGUMENTS` общий; выбросить Claude-специфику: `argument-hint`, `allowed-tools`).
  - [ ] 2.3: SYNC_TRANSFORMS: агенты `.claude/agents/*.md` → `.opencode/agents/*.md` (`description` + `mode: subagent` + тело; read-only набор инструментов → `permissions: [-edit, -shell]`; выбросить `name`/`tools`/`model`).
  - [ ] 2.4: SYNC_MIRRORS — 5 скиллов → `.opencode/skills/<имя>/SKILL.md`.
  - [ ] 2.5: Смоук: `sync` + `sync --check` чист; `opencode` читает конфиг (см. 4.2).
- [ ] **Этап 3: Плагин OpenCode — Plan-First-гейт**
  - [ ] 3.1: `index.ts` — `Plugin.define({id: "second_brain"})`; `ctx.permission.hook("evaluate")`: для `action` edit/read/shell собрать Claude-совместимый payload (`tool_name`: Edit/Read/Bash, `tool_input.file_path`/`command`), запустить `python agents/tools/hooks/pre_tool_gate.py` (cwd = `ctx.location.directory`), при `permissionDecision: deny` → `event.effect = "deny"`, `event.message = reason`.
  - [ ] 3.2: Fail-open: ненулевой exit без JSON / таймаут (3 с) / отсутствие python → без изменений + `console.warn`.
  - [ ] 3.3: Смоук через установленный `opencode` CLI: плагин загружается, deny срабатывает на правке без активной задачи, allow — с активной.
- [ ] **Этап 4: Тесты, документирование, сдача**
  - [ ] 4.1: `tests/test_sync.py`+: hooks.json/opencode.jsonc валидны (json), все SYNC-цели существуют и совпадают при `--check`; трансформы команд/агентов (description сохранён, запрещённые ключи выброшены, `$ARGUMENTS` цел); зеркала скиллов байт-в-байт; `index.ts` — непустой, содержит `permission.hook`, `second_brain`, вызов `pre_tool_gate.py`.
  - [ ] 4.2: README (раздел «Кросстулумность: Codex и OpenCode» + trust-review `/hooks`), `CODEBASE_MAP`, `STATUS`; прогон 195+ тестов; запись сессии, `brain end`, коммит.

---

## 4. 🛡️ Риски, сайд-эффекты и план отката

- **Хуки Codex не запустятся без trust-review** (`/hooks`) → документируем в README первый шаг после `sync`; хуки не критичны (без них Codex просто работает без гейта — fail-open по построению).
- **`$(git rev-parse --show-toplevel)` требует sh-совместимого shell** → рекомендация самой документации Codex; на Windows возможен сбой запуска → хук молча не работает (Codex: ошибка хука не блокирует операцию), риск приемлем; `commandWindows` добавить, если на этапе 1.3 подтвердится проблема.
- **Плагин: API V2 молодой** → локальный плагин с `id` и `setup`, только проверенные докой хуки; единственный TS-файл; если смоук (3.3) покажет неработоспособность — Этап 3 исключается из коммита (1–2 и 4 остаются), плагин переносится в PLAN-007.
- **Трансформа теряет `model`/`tools` у сабагентов** → осознанно (V2 deprecated-поля); поведение: агенты наследуют модель сессии, read-only ограничивается permissions.
- **`sync --check` строже** → CI/предкоммит-хук упадут, если сгенерированные файлы удалить/править руками — это и есть цель (как с 5 Claude-конфигами).
- **Откат:** `git revert` по этапам; все новые артефакты производные — удаляются и пересоздаются `sync`.

---

## 5. 🧪 План тестирования и критерии приемки

1. Автотесты: `python -m unittest discover -s tests` — 195 + новые, 0 падений.
2. Ручная проверка:
   - `python brain.py sync` → `.codex/hooks.json`, `opencode.jsonc`, `.opencode/{commands,agents,skills}`, `.agents/skills/*` созданы; `sync --check` — чист; правка руками → drift обнаружен.
   - `python -c "import json; json.load(open('.codex/hooks.json'))"` и то же для `opencode.jsonc` — валидны.
   - Codex (если доступен): `codex` видит скиллы (`/skills`), хуки просят trust (`/hooks`), гейт deny на правке без плана.
   - OpenCode: `opencode` видит `/plan` и др. команды, сабагентов, MCP `brain`; плагин гейтит правку без активной задачи.
3. Definition of Done:
   - [ ] Код компилируется (`compileall`), только stdlib (Python-часть); TS-плагин — один файл без зависимостей.
   - [ ] Тесты зелёные, `check_integrity` — 0/0, `sync --check` чист.
   - [ ] Все цели рендера (5 старых + 2 новых шаблона + 6 команд + 7 агентов + 10 зеркала скиллов) существуют и синхронны.
   - [ ] Документация (README/CODEBASE_MAP/STATUS) обновлена.
