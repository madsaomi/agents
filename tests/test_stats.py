#!/usr/bin/env python3
"""
Тесты дашборда памяти stats (PLAN-004, Этап 2) + смоук тура (Этап 3).

Фикстуры создаются во временных каталогах — репозиторий не затрагивается.

Запуск:  python -m unittest discover -s tests -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import stats  # noqa: E402
import locks  # noqa: E402


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_stats_test_"))
    agents = root / "agents"
    for sub in ("plans", "tasks", "history", "bugs_and_fixes", "decisions", "walkthroughs"):
        (agents / sub).mkdir(parents=True, exist_ok=True)

    (agents / "plans" / "plan_001_x.md").write_text(
        "# План\n**Статус:** IN_PROGRESS\n- [x] Готово\n- [ ] Осталось\n",
        encoding="utf-8",
    )
    (agents / "plans" / "plan_002_y.md").write_text(
        "# План\n**Статус:** COMPLETED\n- [x] Готово\n", encoding="utf-8",
    )
    (agents / "tasks" / "active_task.md").write_text(
        "# 📋 Активная задача: TASK-999 — Тестовая\n\n"
        "**Статус:** 🔵 IN_PROGRESS ( Этап 1 )  \n\n"
        "- [ ] Шаг один\n- [ ] Шаг два\n- [x] Сделано\n",
        encoding="utf-8",
    )
    (agents / "tasks" / "archive").mkdir()
    (agents / "history" / "session_001.md").write_text("# Сессия\n", encoding="utf-8")
    (agents / "bugs_and_fixes" / "BUG_001.md").write_text("# BUG-001\n", encoding="utf-8")
    (agents / "decisions" / "ADR_001.md").write_text("# ADR-001\n", encoding="utf-8")
    (agents / "walkthroughs" / "WT_001.md").write_text("# WT-001\n", encoding="utf-8")
    (agents / "STATUS.md").write_text("# Статус\n\n[cссылка](plans/plan_001_x.md)\n", encoding="utf-8")
    return root


class TestCollectStats(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_section_counts(self):
        s = stats.collect_stats(root=self.root)
        self.assertEqual(s["sections"]["plans"], 2)
        self.assertEqual(s["sections"]["tasks"], 1)      # archive/ пуст в фикстуре
        self.assertEqual(s["sections"]["history"], 1)
        self.assertEqual(s["sections"]["bugs_and_fixes"], 1)
        self.assertEqual(s["sections"]["decisions"], 1)
        self.assertEqual(s["sections"]["walkthroughs"], 1)

    def test_active_task_parsed(self):
        s = stats.collect_stats(root=self.root)
        self.assertIn("TASK-999", s["active_task"]["title"])
        self.assertNotIn("Активная задача:", s["active_task"]["title"])
        self.assertIn("IN_PROGRESS", s["active_task"]["status"])
        self.assertNotIn("*", s["active_task"]["status"])

    def test_checkboxes_counted(self):
        s = stats.collect_stats(root=self.root)
        cl = s["checklists"]
        self.assertEqual(cl["task_open"], 2)
        self.assertEqual(cl["task_done"], 1)
        # активен только IN_PROGRESS-план (COMPLETED не в счёт)
        self.assertEqual(cl["active_plans"], ["plan_001_x.md"])
        self.assertEqual(cl["plans_open"], 1)
        self.assertEqual(cl["plans_done"], 1)

    def test_broken_link_detected(self):
        (self.root / "agents" / "STATUS.md").write_text(
            "[битая](plans/plan_999_missing.md) и [ок](plans/plan_001_x.md)\n"
            "[веб](https://example.com) и [якорь](#раздел)\n", encoding="utf-8")
        s = stats.collect_stats(root=self.root)
        self.assertEqual(len(s["broken_links"]), 1)
        self.assertEqual(s["broken_links"][0]["target"], "plans/plan_999_missing.md")
        self.assertEqual(s["broken_links"][0]["line"], 1)

    def test_no_broken_links_in_fixture(self):
        s = stats.collect_stats(root=self.root)
        self.assertEqual(s["broken_links"], [])

    def test_stale_files_respect_threshold(self):
        old = self.root / "agents" / "history" / "session_001.md"
        stamp = time.time() - 100 * 86400
        os.utime(old, (stamp, stamp))
        s = stats.collect_stats(root=self.root, stale_days=90)
        self.assertEqual(len(s["stale_files"]), 1)
        self.assertIn("session_001", s["stale_files"][0]["file"])
        # тем же файлом в большой порог — не устаревший
        s2 = stats.collect_stats(root=self.root, stale_days=365)
        self.assertEqual(s2["stale_files"], [])

    def test_claims_listed(self):
        ok, _ = locks.claim_task("TASK-777", agent="tester", root=self.root)
        self.assertTrue(ok)
        s = stats.collect_stats(root=self.root)
        self.assertEqual(len(s["claims"]), 1)
        self.assertEqual(s["claims"][0]["task"], "TASK-777")
        self.assertEqual(s["claims"][0]["status"], "active")

    def test_stats_are_json_serializable(self):
        s = stats.collect_stats(root=self.root)
        data = json.loads(json.dumps(s, ensure_ascii=False))
        self.assertEqual(data["total_records"], sum(data["sections"].values()))

    def test_format_contains_sections(self):
        s = stats.collect_stats(root=self.root)
        out = stats.format_stats(s)
        for marker in ("ДАШБОРД", "plans", "Битые ссылки", "Локи claim", "Чек-листы"):
            self.assertIn(marker, out)

    def test_format_reports_broken_links(self):
        (self.root / "agents" / "STATUS.md").write_text(
            "[битая](plans/plan_999_missing.md)\n", encoding="utf-8")
        out = stats.format_stats(stats.collect_stats(root=self.root))
        self.assertIn("Битые ссылки: 1", out)
        self.assertIn("plan_999_missing.md", out)

    def test_missing_sections_do_not_crash(self):
        root = Path(tempfile.mkdtemp(prefix="brain_stats_empty_"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "agents").mkdir()
        s = stats.collect_stats(root=root)
        self.assertEqual(s["total_records"], 0)
        self.assertIsNone(s["active_task"]["title"])


class TestStatsCli(unittest.TestCase):
    def test_main_json_output(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = stats.main(["--root", str(root), "--json"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["sections"]["plans"], 2)


class TestTourSmoke(unittest.TestCase):
    """Смоук: brain.py tour --list отрабатывает и печатает все экраны."""

    def test_tour_list_runs(self):
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "agents" / "tools" / "brain.py"),
             "tour", "--list"],
            capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        out = proc.stdout
        self.assertIn("Второй Мозг", out)
        self.assertIn("plan", out)          # Plan-First упомянут
        self.assertIn("search", out)        # поиск упомянут
        self.assertIn("claim", out)         # мультиагентность упомянута
        self.assertIn("7/7", out)           # все экраны отрисованы


if __name__ == "__main__":
    unittest.main()
