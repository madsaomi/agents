#!/usr/bin/env python3
"""
SessionStart-хук Claude Code: подкладывает агенту текущий статус и активную задачу.

Регистрация: .claude/settings.json → SessionStart.
Выход: JSON с hookSpecificOutput.additionalContext (см. code.claude.com/docs/en/hooks).
Дополнительно пишет маркер старта сессии (.claude/.session_state.json) —
его использует session_log.py для автосоздания записи истории.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def project_root() -> Path:
    import os
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3]


def read_lines(path: Path, limit: int) -> str:
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[:limit])


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
    except Exception:
        inp = {}

    root = project_root()
    status = read_lines(root / "agents" / "STATUS.md", 40)
    active = read_lines(root / "agents" / "tasks" / "active_task.md", 60)

    context = (
        "## 🧠 Second Brain: контекст сессии (автовставка SessionStart-хука)\n\n"
        "Правила проекта: `agents/rules/CORE_RULES.md` (Plan-First обязателен).\n\n"
        f"### 📊 STATUS.md\n{status}\n\n"
        f"### 📋 Активная задача\n{active}\n\n"
        "> Продолжай с первого невыполненного шага `[ ]`. Не перечитывай файлы, если они выше."
    )

    # Маркер старта сессии — для session_log.py (автосоздание истории)
    try:
        state = {
            "session_id": inp.get("session_id", ""),
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "source": inp.get("source", ""),
        }
        state_dir = root / ".claude"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / ".session_state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass  # маркер — best effort, не ломаем сессию

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
