#!/usr/bin/env python3
"""
PreToolUse-хук Claude Code: принудительный Plan-First + защита секретов и деструктивных команд.

Регистрация: .claude/settings.json → PreToolUse (мэтчеры Edit|Write, Read, Bash|PowerShell).
Вход: JSON события на stdin (см. code.claude.com/docs/en/hooks).
Отказ: JSON hookSpecificOutput.permissionDecision=deny на stdout, exit 0.
Логика fail-open: любая внутренняя ошибка -> exit 0 (не блокируем сессию).
"""

import json
import re
import sys
from pathlib import Path

# Определяем корень проекта: cwd события -> CLAUDE_PROJECT_DIR -> родитель tools/hooks
def _project_root(inp: dict) -> Path:
    for key in ("cwd",):
        if inp.get(key):
            return Path(inp[key])
    import os
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3]


# Файлы, которые никогда не редактируются/не читаются напрямую
SECRET_FILE_RE = re.compile(
    r"(^|[/\\])\.env$|"          # .env (но НЕ .env.example — $ конец строки, точка перед env экранирована)
    r"(^|[/\\])\.env\.[^/\\]+$|"  # .env.local, .env.production
    r"\.(pem|p12|pfx|key)$|"
    r"(^|[/\\])id_(rsa|ed25519|ecdsa)(\.pub)?$"
)
SECRET_EXEMPT_RE = re.compile(r"\.env\.example$|\.env\.sample$")

# Деструктивные / опасные shell-команды
DANGEROUS_BASH = [
    (re.compile(r"\brm\s+-(?:[a-z]*r[a-z]*f|[a-z]*f[a-z]*r)\b"), "rm -rf (деструктивное удаление)"),
    (re.compile(r"\bgit\s+push\b[^|;&]*\s--force\b|\bgit\s+push\s+-f\b"), "git push --force"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard"),
    (re.compile(r"\bgit\s+clean\s+-[a-z]*f"), "git clean -f"),
    (re.compile(r"\bgit\s+checkout\s+--\s+\."), "git checkout -- . (затирает незакоммиченные правки)"),
    (re.compile(r"(curl|wget)\b[^|;&]*\|\s*(ba|z)?sh\b"), "curl|sh (загрузка и запуск скрипта)"),
    (re.compile(r"\bchmod\s+777\b"), "chmod 777"),
    (re.compile(r"\bRemove-Item\b[^|;&]*-Recurse\b"), "Remove-Item -Recurse (PowerShell)"),
    (re.compile(r"(cat|type|more|Get-Content)\s+['\"]?\.env['\"]?\b"), "чтение .env напрямую"),
]


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[Second Brain] {reason}",
        }
    }, ensure_ascii=False))


def has_active_plan(root: Path) -> bool:
    """Активен ли план: plan_*.md со статусом DRAFT/APPROVED/IN_PROGRESS ИЛИ незакрытые шаги в active_task.md."""
    plans_dir = root / "agents" / "plans"
    if plans_dir.is_dir():
        for plan in plans_dir.glob("plan_*.md"):
            try:
                head = plan.read_text(encoding="utf-8", errors="replace")[:600]
            except OSError:
                continue
            if re.search(r"(🟡 DRAFT|🟢 APPROVED|🔵 IN_PROGRESS)", head):
                return True
    active = root / "agents" / "tasks" / "active_task.md"
    if active.is_file():
        try:
            content = active.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        if re.search(r"^- \[ \]", content, re.MULTILINE):
            return True
    return False


def main() -> int:
    try:
        inp = json.load(sys.stdin)
    except Exception:
        return 0  # fail-open: нет входа -> не блокируем

    tool = inp.get("tool_name", "")
    tool_input = inp.get("tool_input", {}) or {}
    try:
        root = _project_root(inp)

        # --- Bash / PowerShell: деструктивные команды и прямое чтение секретов ---
        if tool in ("Bash", "PowerShell"):
            command = str(tool_input.get("command", ""))
            for pattern, label in DANGEROUS_BASH:
                if pattern.search(command):
                    deny(f"Заблокировано: {label}. Правило agents/rules/ANTI_PATTERNS.md. Если необходимо — выполни вручную с подтверждением пользователя.")
                    return 0
            return 0

        # --- Read: нельзя читать секреты ---
        if tool == "Read":
            fp = str(tool_input.get("file_path", ""))
            if SECRET_FILE_RE.search(fp) and not SECRET_EXEMPT_RE.search(fp):
                deny(f"Чтение секретов запрещено: {fp}. Используй .env.example и переменные окружения.")
                return 0
            return 0

        # --- Edit / Write / NotebookEdit ---
        if tool in ("Edit", "Write", "NotebookEdit"):
            fp = str(tool_input.get("file_path", ""))
            if SECRET_FILE_RE.search(fp) and not SECRET_EXEMPT_RE.search(fp):
                deny(f"Правка секретов запрещена: {fp}. В репозиторий идёт только .env.example.")
                return 0

            # Plan-First: код и конфиги требуют активного плана; документация/планы/задачи — нет
            p = Path(fp)
            if p.is_absolute():
                try:
                    rel = p.relative_to(root).as_posix()
                except ValueError:
                    rel = p.name
            else:
                rel = p.as_posix()
            is_documentation = p.suffix.lower() in (".md", ".mdc") or rel.startswith("agents/")
            if not is_documentation and not has_active_plan(root):
                deny(
                    "Plan-First: нет активного плана (agents/plans/plan_*.md со статусом DRAFT/APPROVED/IN_PROGRESS "
                    "или незакрытых шагов в agents/tasks/active_task.md). "
                    "Создай план: python brain.py plan \"<название>\" — затем повтори операцию."
                )
                return 0
            return 0

        return 0
    except Exception:
        return 0  # fail-open


if __name__ == "__main__":
    sys.exit(main())
