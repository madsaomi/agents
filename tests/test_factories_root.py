#!/usr/bin/env python3
"""
Тесты root-aware фабрик артефактов (PLAN-011 / TASK-013, класс BUG-002).

Каждая фабрика обязана писать артефакт в root/agents/..., а шаблоны читать
из расположения модуля (пакетный ресурс). CLI-регресс: brain.py plan из tmp
создаёт файл в tmp, живой репозиторий не трогается.

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

import brain  # noqa: E402
import end_session as end_session_mod  # noqa: E402
import init_project  # noqa: E402
import new_plan  # noqa: E402

BRAIN = PROJECT_ROOT / "agents" / "tools" / "brain.py"


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_factories_test_"))
    agents = root / "agents"
    for sub in ("plans", "tasks", "history", "bugs_and_fixes", "decisions",
                "walkthroughs", "registry", "tasks/archive"):
        (agents / sub).mkdir(parents=True, exist_ok=True)
    return root


class TestFactoriesWriteToRoot(unittest.TestCase):
    """Каждая фабрика кладёт артефакт в root/agents/<раздел>, нумерация — по root."""

    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_create_plan_writes_to_root(self):
        p = new_plan.create_plan("Root Test", task_id="TASK-900", agent="Тестер", root=self.root)
        self.assertTrue(str(p).startswith(str(self.root / "agents" / "plans")), str(p))
        self.assertEqual(p.name, "plan_001_root_test.md")
        text = p.read_text(encoding="utf-8")
        self.assertIn("Root Test", text)      # шаблон подставлен (модульный ресурс)
        self.assertIn("PLAN-001", text)
        p2 = new_plan.create_plan("Second Plan", task_id="TASK-900", agent="Тестер", root=self.root)
        self.assertEqual(p2.name, "plan_002_second_plan.md")  # нумерация по tmp-каталогу

    def test_create_bug_report_writes_to_root(self):
        p = brain.create_bug_report("Тестовый баг", component="CLI", agent="Тестер", root=self.root)
        self.assertTrue(str(p).startswith(str(self.root / "agents" / "bugs_and_fixes")))
        self.assertIn("Тестовый баг", p.read_text(encoding="utf-8"))

    def test_create_adr_writes_to_root(self):
        p = brain.create_adr_record("Тестовое решение", agent="Тестер", root=self.root)
        self.assertTrue(str(p).startswith(str(self.root / "agents" / "decisions")))
        self.assertIn("Тестовое решение", p.read_text(encoding="utf-8"))

    def test_create_task_card_writes_to_root(self):
        p = brain.create_task_card("Тестовая задача", priority="HIGH", agent="Тестер", root=self.root)
        self.assertTrue(str(p).startswith(str(self.root / "agents" / "tasks")))
        self.assertIn("TASK-001", p.read_text(encoding="utf-8"))

    def test_create_walkthrough_writes_to_root(self):
        p = brain.create_walkthrough("Тестовое демо", plan_id="PLAN-900",
                                     task_id="TASK-900", agent="Тестер", root=self.root)
        self.assertTrue(str(p).startswith(str(self.root / "agents" / "walkthroughs")))
        self.assertIn("Тестовое демо", p.read_text(encoding="utf-8"))


class TestEndSessionRoot(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "agents" / "tasks" / "active_task.md").write_text(
            "# Задача\n- [x] Сделал шаг один\n- [x] Сделал шаг два\n- [ ] Осталось\n",
            encoding="utf-8",
        )
        (self.root / "agents" / "STATUS.md").write_text(
            "# Статус\n**Последнее обновление:** старая дата\n**Ответственный агент:** кто-то\n",
            encoding="utf-8",
        )

    def test_extract_completed_from_root(self):
        done = end_session_mod.extract_completed_tasks_from_active(root=self.root)
        self.assertEqual(done, ["Сделал шаг один", "Сделал шаг два"])

    def test_end_session_writes_to_root(self):
        end_session_mod.end_session(agent="ТестАгент", task_id="TASK-900",
                                    done_items=["работа"], next_steps="дальше", root=self.root)
        sessions = list((self.root / "agents" / "history").glob("session_*.md"))
        self.assertEqual(len(sessions), 1, "запись сессии должна появиться в tmp")
        status = (self.root / "agents" / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("ТестАгент", status)
        self.assertNotIn("старая дата", status)


class TestInitProjectRoot(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_placeholders_filled_in_root_only(self):
        real_status = PROJECT_ROOT / "agents" / "STATUS.md"
        real_before = real_status.read_text(encoding="utf-8")

        (self.root / "agents" / "STATUS.md").write_text(
            "# Статус\n**Проект:** {{PROJECT_NAME}}\n**Стек:** {{TECH_STACK}}\n",
            encoding="utf-8",
        )
        init_project.init_project(name="Проект Икс", desc="тест", stack="Python",
                                  agent="Тестер", root=self.root)

        filled = (self.root / "agents" / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("Проект Икс", filled)
        self.assertNotIn("{{PROJECT_NAME}}", filled)
        self.assertEqual(real_status.read_text(encoding="utf-8"), real_before,
                         "init с root не должен трогать живой репозиторий")


class TestCliPlanTmpRegression(unittest.TestCase):
    """CLI-регресс всего класса BUG-002: plan из cwd=tmp пишет в tmp."""

    def test_plan_from_tmp_cwd_lands_in_tmp(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        plans_before = {p.name for p in (PROJECT_ROOT / "agents" / "plans").glob("*.md")}

        proc = subprocess.run(
            [sys.executable, str(BRAIN), "plan", "Root Test", "--task", "TASK-900", "--agent", "Тестер"],
            cwd=str(root), capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])

        created = list((root / "agents" / "plans").glob("plan_001_*.md"))
        self.assertEqual(len(created), 1, f"план должен появиться в tmp: {proc.stdout[-300:]}")
        self.assertIn("Root Test", created[0].read_text(encoding="utf-8"))

        plans_after = {p.name for p in (PROJECT_ROOT / "agents" / "plans").glob("*.md")}
        self.assertEqual(plans_before, plans_after, "живой репозиторий не должен измениться")


if __name__ == "__main__":
    unittest.main()
