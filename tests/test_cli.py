#!/usr/bin/env python3
"""
Смок-тесты CLI-диспетчера brain.py (PLAN-009).

Read-only подкоманды — на живом репозитории; мутирующие (search/claim/release) —
на tmp-скелете: brain.py сам определяет root по cwd/agents.
Исключены из смока (пишут вне root-параметра — фабрики артефактов привязаны к
расположению модуля): plan, bug, adr, task, walkthrough, end, init, preset,
upgrade, dump. См. backlog: TASK-013 «фабрики артефактов должны уважать root».

Запуск:  python -m unittest discover -s tests -v
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRAIN = PROJECT_ROOT / "agents" / "tools" / "brain.py"


def run_cli(args, cwd=PROJECT_ROOT, timeout=120):
    return subprocess.run(
        [sys.executable, str(BRAIN), *args],
        cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
    )


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_cli_test_"))
    agents = root / "agents"
    for sub in ("plans", "tasks", "history", "bugs_and_fixes", "decisions", "walkthroughs"):
        (agents / sub).mkdir(parents=True)
    (agents / "plans" / "plan_001_x.md").write_text("# План\n[[BUG-001]]\n", encoding="utf-8")
    return root


class TestCliReadOnlyRealRepo(unittest.TestCase):
    """Read-only подкоманды на живом репозитории — ничего не пишут."""

    def test_help_lists_commands(self):
        proc = run_cli(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("Second Brain", proc.stdout)
        for cmd in ("plan", "sync", "search", "claim", "stats", "doctor", "tour"):
            self.assertIn(cmd, proc.stdout)

    def test_status_runs(self):
        proc = run_cli(["status"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("SECOND BRAIN", proc.stdout.upper())

    def test_tour_list_prints_all_screens(self):
        proc = run_cli(["tour", "--list"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("7/7", proc.stdout)
        self.assertIn("doctor", proc.stdout)  # экран 6/7 после PLAN-008

    def test_presets_lists_known_stacks(self):
        proc = run_cli(["presets"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        for preset in ("django-drf", "fastapi", "nextjs", "aiogram-bot"):
            self.assertIn(preset, proc.stdout)

    def test_claims_runs(self):
        proc = run_cli(["claims"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertTrue(
            "Свободно" in proc.stdout or "Активные блокировки" in proc.stdout,
            proc.stdout[-300:],
        )

    def test_stats_json_parseable(self):
        proc = run_cli(["stats", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        data = json.loads(proc.stdout)
        self.assertIn("sections", data)

    def test_doctor_json_parseable(self):
        proc = run_cli(["doctor", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        data = json.loads(proc.stdout)
        self.assertEqual(data["summary"]["checks"], 7)

    def test_sync_check_clean(self):
        proc = run_cli(["sync", "--check"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("канон", proc.stdout)

    def test_check_integrity_passes(self):
        proc = run_cli(["check"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("100%", proc.stdout)

    def test_links_runs(self):
        proc = run_cli(["links"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])

    def test_search_without_query_exits_1(self):
        proc = run_cli(["search"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Укажи запрос", proc.stdout)


class TestCliMutatingTmpSkeleton(unittest.TestCase):
    """Мутирующие подкоманды — только на tmp-скелете (cwd=tmp → root=tmp)."""

    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_search_reindex_then_query(self):
        proc = run_cli(["search", "--reindex"], cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("Переиндексировано", proc.stdout)
        self.assertTrue((self.root / ".brain_index.db").exists())

        proc = run_cli(["search", "План"], cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("plan_001_x", proc.stdout)

    def test_claim_claims_release_cycle(self):
        proc = run_cli(["claim", "TASK-950", "--agent", "Tester", "--note", "смок"], cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])

        proc = run_cli(["claims"], cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("TASK-950", proc.stdout)
        self.assertIn("Tester", proc.stdout)

        proc = run_cli(["release", "TASK-950", "--agent", "Tester"], cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        proc = run_cli(["claims"], cwd=self.root)
        self.assertIn("Свободно", proc.stdout)

    def test_root_detection_by_cwd(self):
        """brain.py должен взять root из cwd (cwd/agents), а не из расположения модуля."""
        # Индекс создаётся в tmp, а не в живом репо:
        proc = run_cli(["search", "--reindex"], cwd=self.root)
        self.assertTrue((self.root / ".brain_index.db").exists())


if __name__ == "__main__":
    unittest.main()
