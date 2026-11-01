#!/usr/bin/env python3
"""
Тесты финального кода перед релизом (PLAN-013):
root в run_integrity_check, цель brain dump в root, brain digest.

Запуск:  python -m unittest discover -s tests -v
"""

import argparse
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import brain  # noqa: E402
import check_integrity  # noqa: E402
import digest  # noqa: E402
import handoff as brain_handoff  # noqa: E402
import stats as memory_stats  # noqa: E402


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_final_test_"))
    agents = root / "agents"
    for sub in ("plans", "tasks", "history", "bugs_and_fixes", "decisions",
                "walkthroughs", "tools"):
        (agents / sub).mkdir(parents=True, exist_ok=True)
    (agents / "plans" / "plan_900_t.md").write_text(
        "# План\n> **Статус:** 🔵 IN_PROGRESS\n- [ ] Шаг\n[[BUG-900]]\n", encoding="utf-8")
    (agents / "bugs_and_fixes" / "BUG_900_t.md").write_text(
        "# BUG-900\n**Статус:** 🟡\n## Симптом\ns\n## Первопричина\np\n", encoding="utf-8")
    (agents / "tasks" / "active_task.md").write_text(
        "# 📋 Активная задача: TASK-900 — Т\n\n**Статус:** 🔵 IN_PROGRESS\n- [ ] Шаг\n",
        encoding="utf-8")
    return root


class TestIntegrityRoot(unittest.TestCase):
    """run_integrity_check(root=...) — проверяет указанный проект, не модуль."""

    def test_accepts_root_and_returns_code(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        code = check_integrity.run_integrity_check(root=root)  # tmp-скелет: будут FAIL
        self.assertIsInstance(code, int)

    def test_real_repo_check_passes_with_root(self):
        code = check_integrity.run_integrity_check(root=PROJECT_ROOT)
        self.assertEqual(code, 0)

    def test_no_root_keeps_legacy_behavior(self):
        code = check_integrity.run_integrity_check()
        self.assertEqual(code, 0)


class TestDumpTarget(unittest.TestCase):
    """brain dump пишет context_dump.md в PROJECT_ROOT/agents/tools, не рядом с модулем."""

    def test_dump_lands_in_root(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        real_dump = PROJECT_ROOT / "agents" / "tools" / "context_dump.md"
        real_before = real_dump.read_text(encoding="utf-8") if real_dump.exists() else None
        args = argparse.Namespace(budget=800)
        with mock.patch.object(brain, "PROJECT_ROOT", root):
            brain.cmd_dump(args)
        produced = root / "agents" / "tools" / "context_dump.md"
        self.assertTrue(produced.exists(), "дамп должен появиться в tmp-проекте")
        self.assertGreater(produced.stat().st_size, 100, "дамп не должен быть пустым")
        real_after = real_dump.read_text(encoding="utf-8") if real_dump.exists() else None
        self.assertEqual(real_before, real_after, "живой context_dump.md не должен меняться")


class TestDigest(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def _report(self):
        return (brain_handoff.collect_handoff(root=self.root),
                memory_stats.collect_stats(root=self.root))

    def test_sections_rendered(self):
        h, s = self._report()
        text = digest.render_digest(h, s)
        self.assertIn("Дайджест проекта", text)
        self.assertIn("TASK-900", text)
        self.assertIn("BUG_900_t.md", text)
        self.assertIn("Локи:", text)
        self.assertIn("Память:", text)

    def test_no_task_variant(self):
        (self.root / "agents" / "tasks" / "active_task.md").write_text(
            "# Активная задача: (не выбрана)\n", encoding="utf-8")
        h, s = self._report()
        text = digest.render_digest(h, s)
        self.assertIn("не выбрана", text)

    def test_token_budget_truncates(self):
        h, s = self._report()
        full = digest.render_digest(h, s)
        short = digest.render_digest(h, s, max_tokens=15)
        self.assertLess(len(short), len(full))
        self.assertIn("усечён", short)

    def test_without_budget_no_truncation_marker(self):
        h, s = self._report()
        self.assertNotIn("усечён", digest.render_digest(h, s))


class TestCliDigestSmoke(unittest.TestCase):
    def test_digest_runs_on_real_repo(self):
        proc = __import__("subprocess").run(
            [sys.executable, str(PROJECT_ROOT / "agents" / "tools" / "brain.py"), "digest"],
            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("Дайджест проекта", proc.stdout)

    def test_digest_tokens_flag(self):
        proc = __import__("subprocess").run(
            [sys.executable, str(PROJECT_ROOT / "agents" / "tools" / "brain.py"),
             "digest", "--tokens", "40"],
            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("усечён", proc.stdout)


if __name__ == "__main__":
    unittest.main()
