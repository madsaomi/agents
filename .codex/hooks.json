{
  "description": "Second Brain: исполнительные правила Codex (Plan-First, защита секретов, линт после правки, журнал сессии). Генерируется: python brain.py sync (канон: agents/rules/CORE_RULES.md). Хуки требуют trust-review через /hooks. Не править руками.",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$(git rev-parse --show-toplevel)/agents/tools/hooks/inject_context.py\"",
            "timeout": 15,
            "statusMessage": "Загрузка контекста Second Brain"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|apply_patch|Read|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$(git rev-parse --show-toplevel)/agents/tools/hooks/pre_tool_gate.py\"",
            "timeout": 15,
            "statusMessage": "Plan-First: проверка активного плана и секретов"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|apply_patch",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$(git rev-parse --show-toplevel)/agents/tools/hooks/post_edit_lint.py\"",
            "timeout": 30,
            "statusMessage": "Линт после правки файла"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$(git rev-parse --show-toplevel)/agents/tools/hooks/session_log.py\"",
            "timeout": 15,
            "statusMessage": "Запись сессии в agents/history"
          }
        ]
      }
    ]
  }
}
