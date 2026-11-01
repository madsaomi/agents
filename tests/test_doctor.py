#!/usr/bin/env python3
"""
Тесты doctor (PLAN-008): диагностика окружения.

Фикстуры создаются во временных каталогах — репозиторий не затрагивается.
Ошибки окружения симулируются через unittest.mock — без chmod и правки системы.

Запуск:  python -m unittest discover -s tests -v
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import doctor  # noqa: E402

CHECK_NAMES = ["python", "fts5", "git", "index", "clipboard", "mcp", "write_access"]


def make_root() -> Path:
    """Минимальный скелет проекта: agents/plans/ с одной записью памяти."""
    root = Path(tempfile.mkdtemp(prefix="brain_doctor_test_"))
    (root / "agents" / "plans").mkdir(parents=True)
    (root / "agents" / "plans" / "plan_001_x.md").write_text(
        "# План\n- [ ] Шаг\n", encoding="utf-8")
    return root


def by_name(report, name):
    return next(c for c in report["checks"] if c["name"] == name)


class TestCollectDoctorRealRepo(unittest.TestCase):
    """Отчёт на живом репозитории: форма контракта и детерминированные проверки."""

    def setUp(self):
        self.report = doctor.collect_doctor(root=PROJECT_ROOT)

    def test_seven_checks_in_order(self):
        self.assertEqual([c["name"] for c in self.report["checks"]], CHECK_NAMES)

    def test_summary_counts_match(self):
        checks = self.report["checks"]
        errors = sum(1 for c in checks if c["status"] == "fail")
        warnings = sum(1 for c in checks if c["status"] == "warn")
        self.assertEqual(self.report["summary"]["errors"], errors)
        self.assertEqual(self.report["summary"]["warnings"], warnings)
        self.assertEqual(self.report["summary"]["checks"], len(checks))

    def test_statuses_are_valid(self):
        for c in self.report["checks"]:
            self.assertIn(c["status"], ("ok", "warn", "fail"))

    def test_python_fts5_write_ok_on_dev_machine(self):
        for name in ("python", "fts5", "write_access"):
            self.assertEqual(by_name(self.report, name)["status"], "ok", name)


class TestCollectDoctorTmpSkeleton(unittest.TestCase):
    """Поведение на минимальном скелете (warn-сценарии, root-параметр)."""

    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_index_missing_warn_with_hint(self):
        c = by_name(doctor.collect_doctor(root=self.root), "index")
        self.assertEqual(c["status"], "warn")
        self.assertIn("reindex", c["hint"])

    def test_index_stale_warn(self):
        db = self.root / ".brain_index.db"
        db.write_text("", encoding="utf-8")
        old = time.time() - 30
        os.utime(db, (old, old))  # индекс старше записи памяти
        c = by_name(doctor.collect_doctor(root=self.root), "index")
        self.assertEqual(c["status"], "warn")
        self.assertIn("устарел", c["details"])

    def test_index_fresh_ok(self):
        db = self.root / ".brain_index.db"
        db.write_text("", encoding="utf-8")
        md = self.root / "agents" / "plans" / "plan_001_x.md"
        old = time.time() - 30
        os.utime(md, (old, old))  # память старше индекса
        c = by_name(doctor.collect_doctor(root=self.root), "index")
        self.assertEqual(c["status"], "ok")

    def test_empty_memory_no_index_warn_not_fail(self):
        shutil.rmtree(self.root / "agents" / "plans")
        c = by_name(doctor.collect_doctor(root=self.root), "index")
        self.assertEqual(c["status"], "warn")
        self.assertIn("записей памяти", c["details"])

    def test_git_warn_in_non_repo(self):
        c = by_name(doctor.collect_doctor(root=self.root), "git")
        self.assertEqual(c["status"], "warn")

    def test_report_json_serializable(self):
        report = doctor.collect_doctor(root=self.root)
        loaded = json.loads(json.dumps(report, ensure_ascii=False))
        self.assertEqual(loaded["summary"]["checks"], 7)


class TestFormatDoctor(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_contains_banner_marks_and_hint(self):
        report = doctor.collect_doctor(root=self.root)
        text = doctor.format_doctor(report)
        self.assertIn("Doctor", text)
        self.assertIn("[OK]", text)
        self.assertIn("[WARN]", text)   # на скелете index и git дают warn
        self.assertIn("reindex", text)  # хинты доезжают до вывода

    def test_fail_mark_and_summary(self):
        report = doctor.collect_doctor(root=self.root)
        report["checks"][1] = {**report["checks"][1], "status": "fail"}  # fts5 → fail
        report["summary"]["errors"] = 1
        text = doctor.format_doctor(report)
        self.assertIn("[FAIL]", text)
        self.assertIn("🔴", text)


class TestFailureInjection(unittest.TestCase):
    """Ошибки окружения симулируются mock'ом — кроссплатформенно и без chmod."""

    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_fts5_error_is_fail(self):
        with mock.patch("doctor.sqlite3.connect",
                        side_effect=sqlite3.OperationalError("no such module: fts5")):
            report = doctor.collect_doctor(root=self.root)
        c = by_name(report, "fts5")
        self.assertEqual(c["status"], "fail")
        self.assertEqual(report["summary"]["errors"], 1)
        self.assertIn("FTS5", c["details"])

    def test_write_access_error_is_fail(self):
        with mock.patch("pathlib.Path.write_text",
                        side_effect=OSError(13, "Permission denied")):
            report = doctor.collect_doctor(root=self.root)
        c = by_name(report, "write_access")
        self.assertEqual(c["status"], "fail")
        self.assertGreaterEqual(report["summary"]["errors"], 1)


if __name__ == "__main__":
    unittest.main()
