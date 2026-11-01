#!/usr/bin/env python3
"""
Тесты хуков Claude Code (PLAN-003, Этап 2).
Все сценарии гоняются во временных каталогах — без побочных эффектов на репозиторий.

Запуск:  python -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = PROJECT_ROOT / "agents" / "tools" / "hooks"


def run_hook(script: str, payload: dict, project_dir: Path) -> tuple:
    """Гоняет хук-скрипт с stdin JSON; возвращает (exit_code, stdout)."""
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project_dir))
    res = subprocess.run(
        [sys.executable, str(HOOKS_DIR / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=env,
    )
    return res.returncode, res.stdout


def make_project(with_plan: bool) -> Path:
    """Создаёт минимальный скелет Second Brain во временной папке."""
    root = Path(tempfile.mkdtemp(prefix="brain_hook_test_"))
    (root / "agents" / "plans").mkdir(parents=True)
    (root / "agents" / "tasks").mkdir(parents=True)
    (root / "agents" / "history").mkdir(parents=True)
    (root / "agents" / "STATUS.md").write_text("# STATUS\nПроект: Test", encoding="utf-8")
    if with_plan:
        (root / "agents" / "plans" / "plan_001_test.md").write_text(
            "# План\n> **Статус:** 🔵 IN_PROGRESS\n", encoding="utf-8"
        )
    else:
        (root / "agents" / "tasks" / "active_task.md").write_text(
            "# Активная задача\n- [x] всё сделано\n", encoding="utf-8"
        )
    return root


class TestPreToolGate(unittest.TestCase):
    def decision(self, payload, root):
        code, out = run_hook("pre_tool_gate.py", payload, root)
        self.assertEqual(code, 0, "Хук должен всегда выходить с 0 (deny передаётся через stdout JSON)")
        return json.loads(out) if out.strip() else None

    def test_blocks_code_edit_without_plan(self):
        root = make_project(with_plan=False)
        d = self.decision(
            {"tool_name": "Edit", "cwd": str(root),
             "tool_input": {"file_path": str(root / "src" / "app.py")}},
            root,
        )
        self.assertIsNotNone(d, "Правка кода без плана должна блокироваться")
        self.assertEqual(d["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Plan-First", d["hookSpecificOutput"]["permissionDecisionReason"])

    def test_allows_code_edit_with_active_plan(self):
        root = make_project(with_plan=True)
        d = self.decision(
            {"tool_name": "Edit", "cwd": str(root),
             "tool_input": {"file_path": str(root / "src" / "app.py")}},
            root,
        )
        self.assertIsNone(d, "При активном плане правка кода должна проходить")

    def test_allows_markdown_without_plan(self):
        """Создание плана/задачи/документации не должно требовать... плана (анти-дедлок)."""
        root = make_project(with_plan=False)
        d = self.decision(
            {"tool_name": "Write", "cwd": str(root),
             "tool_input": {"file_path": str(root / "agents" / "plans" / "plan_002_new.md")}},
            root,
        )
        self.assertIsNone(d, "Запись .md (планы, задачи, доки) не блокируется")

    def test_blocks_env_write_even_with_plan(self):
        root = make_project(with_plan=True)
        d = self.decision(
            {"tool_name": "Write", "cwd": str(root),
             "tool_input": {"file_path": str(root / ".env")}},
            root,
        )
        self.assertIsNotNone(d)
        self.assertIn("секрет", d["hookSpecificOutput"]["permissionDecisionReason"].lower())

    def test_allows_env_example(self):
        root = make_project(with_plan=True)
        d = self.decision(
            {"tool_name": "Write", "cwd": str(root),
             "tool_input": {"file_path": str(root / ".env.example")}},
            root,
        )
        self.assertIsNone(d, ".env.example должен разрешён")

    def test_blocks_reading_env(self):
        root = make_project(with_plan=True)
        d = self.decision(
            {"tool_name": "Read", "cwd": str(root),
             "tool_input": {"file_path": str(root / ".env")}},
            root,
        )
        self.assertIsNotNone(d, "Чтение .env должно блокироваться")

    def test_blocks_rm_rf(self):
        root = make_project(with_plan=True)
        d = self.decision(
            {"tool_name": "Bash", "cwd": str(root),
             "tool_input": {"command": "rm -rf /tmp/build"}},
            root,
        )
        self.assertIsNotNone(d)

    def test_blocks_force_push(self):
        root = make_project(with_plan=True)
        d = self.decision(
            {"tool_name": "Bash", "cwd": str(root),
             "tool_input": {"command": "git push --force origin main"}},
            root,
        )
        self.assertIsNotNone(d)

    def test_allows_normal_commands(self):
        root = make_project(with_plan=True)
        d = self.decision(
            {"tool_name": "Bash", "cwd": str(root),
             "tool_input": {"command": "python -m unittest discover -s tests"}},
            root,
        )
        self.assertIsNone(d, "Обычные команды не блокируются")

    def test_fails_open_on_garbage_input(self):
        root = make_project(with_plan=False)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
        res = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "pre_tool_gate.py")],
            input="не json", capture_output=True, text=True, timeout=30, env=env,
        )
        self.assertEqual(res.returncode, 0)


class TestInjectContext(unittest.TestCase):
    def test_injects_status_and_task(self):
        root = make_project(with_plan=True)
        (root / "agents" / "tasks" / "active_task.md").write_text(
            "# Активная задача\n- [ ] Шаг 1\n", encoding="utf-8"
        )
        code, out = run_hook("inject_context.py", {"session_id": "test-sess", "source": "startup"}, root)
        self.assertEqual(code, 0)
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertIn("STATUS", ctx)
        self.assertIn("Шаг 1", ctx)
        # маркер сессии записан для session_log.py
        state = json.loads((root / ".claude" / ".session_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["session_id"], "test-sess")


class TestSessionLog(unittest.TestCase):
    def _state(self, root, session_id="sess-1", started_at="2020-01-01T00:00:00"):
        (root / ".claude").mkdir(exist_ok=True)
        (root / ".claude" / ".session_state.json").write_text(
            json.dumps({"session_id": session_id, "started_at": started_at}), encoding="utf-8"
        )

    def test_creates_stub_once(self):
        root = make_project(with_plan=True)
        self._state(root)
        run_hook("session_log.py", {"session_id": "sess-1"}, root)
        files = list((root / "agents" / "history").glob("session_*_claude-code.md"))
        self.assertEqual(len(files), 1, "Хук должен создать ровно одну заготовку")
        # повторный Stop той же сессии — без дублей
        run_hook("session_log.py", {"session_id": "sess-1"}, root)
        files = list((root / "agents" / "history").glob("session_*_claude-code.md"))
        self.assertEqual(len(files), 1, "Дубликаты записей истории запрещены")

    def test_skips_if_agent_already_logged(self):
        import time
        root = make_project(with_plan=True)
        self._state(root, started_at="2020-01-01T00:00:00")
        # агент сам создал запись позже старта сессии
        agent_log = root / "agents" / "history" / "session_2026-10-27_10-00_agent.md"
        agent_log.write_text("# Сессия агента", encoding="utf-8")
        now = time.time()
        os.utime(agent_log, (now, now))
        run_hook("session_log.py", {"session_id": "sess-1"}, root)
        files = [f for f in (root / "agents" / "history").glob("*.md") if f.name != "README.md"]
        self.assertEqual(len(files), 1, "Хук не должен дублировать запись агента")

    def test_no_state_file_no_action(self):
        root = make_project(with_plan=True)
        run_hook("session_log.py", {"session_id": "x"}, root)
        self.assertEqual(list((root / "agents" / "history").glob("*.md")), [])


class TestPostEditLint(unittest.TestCase):
    def test_non_python_file_silent(self):
        root = make_project(with_plan=True)
        code, out = run_hook(
            "post_edit_lint.py",
            {"tool_name": "Write", "tool_input": {"file_path": str(root / "README.md")}},
            root,
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")

    def test_missing_python_file_silent(self):
        root = make_project(with_plan=True)
        code, out = run_hook(
            "post_edit_lint.py",
            {"tool_name": "Edit", "tool_input": {"file_path": str(root / "nope.py")}},
            root,
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")


class TestSettingsJson(unittest.TestCase):
    def test_settings_valid_and_complete(self):
        settings = json.loads((PROJECT_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        hooks = settings["hooks"]
        for event in ("SessionStart", "PreToolUse", "PostToolUse", "Stop"):
            self.assertIn(event, hooks, f"В settings.json нет события {event}")
        # каждый зарегистрированный скрипт существует
        for event, groups in hooks.items():
            for group in groups:
                for handler in group["hooks"]:
                    args = handler.get("args", [])
                    for a in args:
                        if a.endswith(".py"):
                            script = Path(a.replace("${CLAUDE_PROJECT_DIR}", str(PROJECT_ROOT)))
                            self.assertTrue(script.is_file(), f"{event}: нет скрипта {script}")


if __name__ == "__main__":
    unittest.main()
