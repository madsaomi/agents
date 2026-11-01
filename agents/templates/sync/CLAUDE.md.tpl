<!-- ⚠️ СГЕНЕРИРОВАНО `python brain.py sync`. Источник: agents/rules/CORE_RULES.md. НЕ РЕДАКТИРУЙ ВРУЧНУЮ. -->
# Claude Code — правила проекта (Second Brain)

{{CORE_RULES}}

## Дополнительно для Claude Code
- Используй субагентов из `.claude/agents/` (planner, reviewer, security-auditor и др.) для узких задач.
- Скиллы подключаются на demand из `.claude/skills/`, слэш-команды: `/plan`, `/bug`, `/adr`, `/review`, `/handoff`, `/status`.
- Хуки в `.claude/settings.json` применяют эти правила принудительно (Plan-First, защита секретов).
