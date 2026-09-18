# Claude Code & Claude Assistant Guidelines

This repository strictly follows the **Second Brain** engineering methodology located in the `agents/` directory.

## Core Protocols
- **Entrypoint:** Read `AGENTS.md` and `agents/AGENT_GUIDE.md` first.
- **Rules & Prohibitions:** Study `agents/rules/AGENT_RULES.md` and `agents/rules/ANTI_PATTERNS.md`.
- **Project State:** Inspect `agents/STATUS.md` and `agents/tasks/active_task.md` before making edits.
- **Code Standards:** Adhere to `agents/rules/CODING_STANDARDS.md`.
- **Session Continuity:** Always append a session summary to `agents/history/` at the end of work. Never overwrite existing history files.
- **Integrity Validation:** Run `python agents/tools/check_integrity.py` before finalizing any task.
