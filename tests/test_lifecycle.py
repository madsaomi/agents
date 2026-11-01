#!/usr/bin/env python3
"""
Тесты жизненного цикла памяти (PLAN-010): handoff, archive, memory lint.

Фикстуры создаются во временных каталогах — репозиторий не затрагивается.
Все модули вызываются с root=tmp (урок BUG-002).

Запуск:  python -m unittest discover -s tests -v
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import archive_task  # noqa: E402
import handoff  # noqa: E402
import memory_lint  # noqa: E402

BRAIN = PROJECT_ROOT / "agents" / "tools" / "brain.py"

GOOD_PLAN = """# 📐 План: PLAN-950 — Тестовый

> **Статус:** 🔵 IN_PROGRESS

- [x] Шаг один
- [ ] Шаг два
"""

GOOD_TASK = """# 📋 Активная задача: TASK-950 — Тестовая задача

**Статус:** 🔵 IN_PROGRESS  
**Связанный план:** [`PLAN-950`](../plans/plan_950_test.md)  

- [x] Сделано
- [ ] Осталось
"""

GOOD_BUG = """# 🐛 BUG-950: Тестовый баг

- **Статус:** 🟡 В ПРОЦЕССЕ

## 🔍 1. Симптом (Что произошло)
Что-то сломалось.

## 🔬 2. Первопричина (Root Cause — ПОЧЕМУ это произошло)
Потому что.
"""

GOOD_SESSION = """# 📝 Журнал сессии: тест

### 🔜 5. Инструкция для следующего агента:
- Начни с шага два плана PLAN-950
"""


def make_root(with_active_task: bool = True) -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_life_test_"))
    agents = root / "agents"
    for sub in ("plans", "tasks", "history", "bugs_and_fixes", "decisions", "tasks/archive"):
        (agents / sub).mkdir(parents=True, exist_ok=True)

    (agents / "plans" / "plan_950_test.md").write_text(GOOD_PLAN, encoding="utf-8")
    if with_active_task:
        (agents / "tasks" / "active_task.md").write_text(GOOD_TASK, encoding="utf-8")
    (agents / "bugs_and_fixes" / "BUG_950_test.md").write_text(GOOD_BUG, encoding="utf-8")
    (agents / "bugs_and_fixes" / "BUG_000_example.md").write_text("# Пример\n", encoding="utf-8")
    (agents / "decisions" / "ADR_950_test.md").write_text(
        "# ADR-950\n\n**Статус:** принято\n", encoding="utf-8")
    (agents / "history" / "session_2026-11-01_01_test.md").write_text(GOOD_SESSION, encoding="utf-8")
    (agents / "tasks" / "backlog.md").write_text(
        "# Бэклог\n\n### 📌 Высокий приоритет (High)\n"
        "- [ ] **TASK-999:** Первая высокоприоритетная задача.\n"
        "- [ ] **TASK-998:** Вторая.\n"
        "\n### 📌 Средний приоритет (Medium)\n- [ ] **TASK-997:** Не высокая.\n",
        encoding="utf-8",
    )
    return root


def run_cli(args, cwd, timeout=120):
    return subprocess.run(
        [sys.executable, str(BRAIN), *args],
        cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
    )


class TestMemoryLint(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_good_skeleton_is_clean(self):
        self.assertEqual(memory_lint.lint_memory(root=self.root), [])

    def test_plan_without_status_flagged(self):
        (self.root / "agents" / "plans" / "plan_951_bad.md").write_text("# План без статуса\n", encoding="utf-8")
        findings = memory_lint.lint_memory(root=self.root)
        names = [f["name"] for f in findings]
        self.assertTrue(any("plan_951_bad" in n for n in names), findings)

    def test_plan_without_checkboxes_flagged(self):
        (self.root / "agents" / "plans" / "plan_952_bad.md").write_text(
            "# План\n> **Статус:** ✅ COMPLETED\n", encoding="utf-8")
        findings = memory_lint.lint_memory(root=self.root)
        self.assertTrue(any("plan_952_bad" in f["name"] for f in findings), findings)

    def test_active_task_without_checkboxes_flagged(self):
        (self.root / "agents" / "tasks" / "active_task.md").write_text(
            "# Задача без декомпозиции\n\n**Статус:** 🔵 IN_PROGRESS\n", encoding="utf-8")
        findings = memory_lint.lint_memory(root=self.root)
        self.assertTrue(any("active_task" in f["name"] for f in findings), findings)

    def test_bug_without_sections_flagged(self):
        (self.root / "agents" / "bugs_and_fixes" / "BUG_951_bad.md").write_text(
            "# Баг без разбора\n", encoding="utf-8")
        findings = memory_lint.lint_memory(root=self.root)
        self.assertTrue(any("BUG_951_bad" in f["name"] for f in findings), findings)

    def test_example_files_excluded(self):
        (self.root / "agents" / "decisions" / "ADR_000_example.md").write_text("# Пример\n", encoding="utf-8")
        (self.root / "agents" / "bugs_and_fixes" / "BUG_000_example.md").write_text("# Пример\n", encoding="utf-8")
        self.assertEqual(memory_lint.lint_memory(root=self.root), [])


class TestArchiveTask(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_refuses_with_open_items(self):
        ok, msg = archive_task.archive_active_task(root=self.root)
        self.assertFalse(ok)
        self.assertIn("открытые пункты", msg)

    def test_force_archives_and_resets(self):
        ok, msg = archive_task.archive_active_task(root=self.root, force=True)
        self.assertTrue(ok, msg)
        archived = self.root / "agents" / "tasks" / "archive" / "task_950_completed.md"
        self.assertTrue(archived.exists(), msg)  # номер из TASK-950 в заголовке
        active_text = (self.root / "agents" / "tasks" / "active_task.md").read_text(encoding="utf-8")
        self.assertIn("не выбрана", active_text.lower())

    def test_no_task_is_polite_refusal(self):
        (self.root / "agents" / "tasks" / "active_task.md").write_text(
            archive_task.STUB_TEMPLATE.format(date="2026-11-01"), encoding="utf-8")
        ok, msg = archive_task.archive_active_task(root=self.root)
        self.assertFalse(ok)
        self.assertIn("не выбрана", msg.lower())

    def test_never_overwrites_existing_archive(self):
        dest = self.root / "agents" / "tasks" / "archive" / "task_950_completed.md"
        dest.write_text("СТАРОЕ СОДЕРЖИМОЕ", encoding="utf-8")
        ok, msg = archive_task.archive_active_task(root=self.root, force=True)
        self.assertFalse(ok)
        self.assertIn("уже существует", msg)
        self.assertEqual(dest.read_text(encoding="utf-8"), "СТАРОЕ СОДЕРЖИМОЕ")

    def test_fallback_numbering_without_task_id(self):
        (self.root / "agents" / "tasks" / "active_task.md").write_text(
            "# 📋 Задача без ID\n\n**Статус:** ✅ COMPLETED\n- [x] Всё\n", encoding="utf-8")
        ok, msg = archive_task.archive_active_task(root=self.root)
        self.assertTrue(ok, msg)
        self.assertTrue((self.root / "agents" / "tasks" / "archive" / "task_001_completed.md").exists())


class TestHandoff(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_collects_active_task_and_plan(self):
        r = handoff.collect_handoff(root=self.root)
        self.assertIn("TASK-950", r["active_task"]["title"])
        self.assertEqual(len(r["active_task"]["open_items"]), 1)
        self.assertEqual(r["plan"]["file"], "plan_950_test.md")
        self.assertEqual(len(r["plan"]["open_steps"]), 1)
        self.assertEqual(r["open_bugs"], ["BUG_950_test.md"])
        self.assertIn("TASK-999", r["backlog_next"])  # первый из «Высокий приоритет»
        self.assertIn("шага два", r["last_session"]["next_steps"])

    def test_fail_soft_without_status_and_task(self):
        (self.root / "agents" / "tasks" / "active_task.md").unlink()
        r = handoff.collect_handoff(root=self.root)
        self.assertIsNone(r["active_task"])
        self.assertIsNone(r["plan"])
        self.assertIsNone(r["status"]["phase"])
        text = handoff.format_handoff(r)
        self.assertIn("Эстафета", text)
        self.assertIn("не выбрана", text)

    def test_status_sections_collected(self):
        (self.root / "agents" / "STATUS.md").write_text(
            "# Статус\n**Текущая фаза:** 🟢 тест-фаза\n\n"
            "## 🎯 Что делается прямо сейчас (Текущий фокус):\n"
            "- Фича X в работе\n\n## 🚧 Другое:\n- прочее\n",
            encoding="utf-8")
        r = handoff.collect_handoff(root=self.root)
        self.assertIn("тест-фаза", r["status"]["phase"])
        self.assertIn("Фича X в работе", r["status"]["now"])
        self.assertNotIn("прочее", r["status"]["now"])  # секция не переползает за следующий ##

    def test_stub_task_reported_as_none(self):
        (self.root / "agents" / "tasks" / "active_task.md").write_text(
            archive_task.STUB_TEMPLATE.format(date="2026-11-01"), encoding="utf-8")
        r = handoff.collect_handoff(root=self.root)
        self.assertIsNone(r["active_task"])


class TestCliLifecycleSmoke(unittest.TestCase):
    """Смоуки CLI: handoff — read-only на живом репо; archive — только tmp."""

    def test_handoff_runs_on_real_repo(self):
        proc = run_cli(["handoff"], cwd=PROJECT_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("Эстафета", proc.stdout)
        self.assertIn("Активная задача", proc.stdout)

    def test_archive_refuses_on_empty_tmp(self):
        root = make_root(with_active_task=False)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        proc = run_cli(["archive"], cwd=root)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("нечего", proc.stdout)

    def test_archive_force_cycle_on_tmp(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        proc = run_cli(["archive"], cwd=root)
        self.assertEqual(proc.returncode, 1)          # защита от открытых пунктов
        proc = run_cli(["archive", "--force"], cwd=root)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("task_950_completed.md", proc.stdout)


if __name__ == "__main__":
    unittest.main()
