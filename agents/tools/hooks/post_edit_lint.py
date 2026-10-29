#!/usr/bin/env python3
"""
PostToolUse-хук Claude Code и Codex: автозапуск линтера/форматтера после правки файла.

Регистрация: .claude/settings.json → PostToolUse (мэтчер Edit|Write);
             .codex/hooks.json → PostToolUse (мэтчер Edit|Write|apply_patch).
Правило: тихий выход 0, если ruff/black не установлены или файл не Python.
Проблемы возвращаются как additionalContext (не блокируют работу).
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Пути внутри unified-патча Codex (apply_patch)
APPLY_PATCH_PATH_RE = re.compile(
    r"^\*\*\* (?:Update|Add|Delete|Move(?: to)?) File:\s*(\S+)\s*$", re.MULTILINE
)


def project_root() -> Path:
    import os
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3]


def run(cmd, timeout=15):
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    tool_input = inp.get("tool_input") or {}
    if inp.get("tool_name") == "apply_patch":
        paths = APPLY_PATCH_PATH_RE.findall(str(tool_input.get("command", "")))
    else:
        fp = str(tool_input.get("file_path", ""))
        paths = [fp] if fp else []

    findings = []
    for file_path in paths:
        if not file_path.lower().endswith(".py"):
            continue
        path = Path(file_path)
        if not path.is_file():
            continue

        if shutil.which("ruff"):
            res = run(["ruff", "check", "--no-cache", str(path)])
            if res is not None and res.returncode != 0:
                out = (res.stdout or res.stderr).strip()
                findings.append(f"ruff ({path.name}):\n{out[:1500]}")

        if shutil.which("black"):
            res = run(["black", "--check", "--quiet", str(path)])
            if res is not None and res.returncode != 0:
                findings.append(f"black: файл {path.name} не отформатирован — запусти `black {path.name}`")

    if not findings and not shutil.which("ruff") and not shutil.which("black"):
        return 0  # линтеров нет — тихо выходим

    if findings:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    "⚠️ Автопроверка после правки (PostToolUse-хук). Исправь до завершения шага:\n"
                    + "\n".join(findings)
                ),
            }
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
