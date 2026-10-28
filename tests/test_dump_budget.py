#!/usr/bin/env python3
"""
Тесты бюджета контекста dump --budget (PLAN-003, Этап 7.2).

Дамп собирается из временного проекта — репозиторий не затрагивается.

Запуск:  python -m unittest discover -s tests -v
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import dump_context  # noqa: E402
from dump_context import build_context_dump, estimate_tokens  # noqa: E402


def make_root() -> Path:
    """Проект со всеми секциями контекста, много «воды» в прозе."""
    root = Path(tempfile.mkdtemp(prefix="brain_budget_test_"))
    agents = root / "agents"
    (agents / "tasks").mkdir(parents=True)
    (agents / "architecture").mkdir()
    (agents / "history").mkdir()
    (agents / "plans").mkdir()
    (agents / "product").mkdir()
    (agents / "rules").mkdir()

    (agents / "STATUS.md").write_text(
        "# 📊 Статус\n\n**Проект:** TestProj  \n**Статус:** 🔵 IN_PROGRESS\n\n"
        + ("Очень длинное описание состояния проекта. " * 60) + "\n",
        encoding="utf-8",
    )
    (agents / "tasks" / "active_task.md").write_text(
        "# 📋 Активная задача: TASK-001\n\n- [x] Шаг один\n- [ ] Шаг два\n\n"
        + ("Подробности шага, которые не нужны в сжатом контексте. " * 50) + "\n",
        encoding="utf-8",
    )
    (agents / "architecture" / "CODEBASE_MAP.md").write_text(
        "# 🗺️ Карта\n\n" + ("Описание модулей и файлов. " * 80) + "\n",
        encoding="utf-8",
    )
    (agents / "GLOSSARY.md").write_text(
        "# 📖 Глоссарий\n\n"
        + "\n".join(f"| термин-{i:02d} | развёрнутое определение термина номер {i}. |"
                    for i in range(40))
        + "\n",
        encoding="utf-8",
    )
    (agents / "product" / "PRD.md").write_text(
        "# 🎯 PRD\n\n" + ("Требование продукта, сформулированное развёрнуто. " * 70) + "\n",
        encoding="utf-8",
    )
    (agents / "rules" / "AGENT_RULES.md").write_text(
        "# 📏 Правила\n\n1. Правило первое подробно раскрыто.\n2. Правило второе.\n",
        encoding="utf-8",
    )
    (agents / "plans" / "plan_001_x.md").write_text(
        "# 📐 План: PLAN-001\n\n**Статус:** IN_PROGRESS\n\n"
        "- [x] Шаг 1\n- [ ] Шаг 2\n\n" + ("Детали шага. " * 60) + "\n",
        encoding="utf-8",
    )
    (agents / "history" / "session_001.md").write_text(
        "# 📝 Сессия 001\n\n## Что сделано\n- пункт\n\n" + ("Рассказ о сессии. " * 70) + "\n",
        encoding="utf-8",
    )
    return root


class TestEstimate(unittest.TestCase):
    def test_estimate_tokens_gross_rule(self):
        self.assertEqual(estimate_tokens(""), 1)
        self.assertEqual(estimate_tokens("a" * 300), 100)
        # русский markdown — примерно 3 символа на токен (грубая оценка)
        self.assertEqual(estimate_tokens("абв" * 100), 100)


class TestCompact(unittest.TestCase):
    def test_compact_keeps_structure_drops_prose(self):
        content = (
            "# Заголовок\n\n"
            "Это длинный абзац воды, который не несёт структурной информации " * 10 + "\n"
            "- [x] Чек-лист пункт\n"
            "| колонка | значение |\n"
            "**Статус:** 🔵 IN_PROGRESS\n"
            "Ещё один абзац воды, он должен исчезнуть при автосуммаризации. " * 10 + "\n"
        )
        compact = dump_context._compact(content)
        self.assertIn("# Заголовок", compact)
        self.assertIn("- [x] Чек-лист пункт", compact)
        self.assertIn("| колонка |", compact)
        self.assertIn("**Статус:**", compact)
        self.assertLess(len(compact), len(content))
        self.assertIn("сжато под бюджет", compact)

    def test_truncate_marks_cut(self):
        text = ("строка номер один\n" * 100)
        cut = dump_context._truncate(text, 200)
        self.assertLess(len(cut), len(text))
        self.assertIn("обрезано", cut)
        self.assertTrue(cut.splitlines()[-1].startswith("…"))
        # не усекается, если влезает
        self.assertEqual(dump_context._truncate("короткий", 100), "короткий")


class TestBuildDump(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_full_dump_contains_all_sections(self):
        dump = build_context_dump(root=self.root)
        for marker in ("СТАТУС ПРОЕКТА", "АКТИВНАЯ ЗАДАЧА", "КАРТА КОДОВОЙ БАЗЫ",
                       "ПОСЛЕДНЯЯ СЕССИЯ", "ПЛАН РЕАЛИЗАЦИИ", "ГЛОССАРИЙ", "PRD"):
            self.assertIn(marker, dump, f"Секция {marker} потеряна")
        self.assertNotIn("Сжато под бюджет", dump, "Без бюджета сжатия быть не должно")

    def test_budget_reduces_size_and_fits(self):
        full = build_context_dump(root=self.root)
        full_est = estimate_tokens(full)
        budget = max(100, full_est // 4)

        compressed = build_context_dump(root=self.root, budget=budget)
        est = estimate_tokens(compressed)
        self.assertLessEqual(est, budget, f"Оценка {est} превышает бюджет {budget}")
        self.assertLess(len(compressed), len(full))
        self.assertIn("Сжато под бюджет", compressed)

    def test_core_sections_survive_medium_budget(self):
        """
        Средний бюджет: этап автосуммаризации (~1500 ток.) не влезает →
        глоссарий отбрасывается первым (низший приоритет), ядро удерживается.
        """
        compressed = build_context_dump(root=self.root, budget=700)
        self.assertLessEqual(estimate_tokens(compressed), 700)
        self.assertIn("СТАТУС ПРОЕКТА", compressed)
        self.assertIn("АКТИВНАЯ ЗАДАЧА", compressed)
        self.assertNotIn("ГЛОССАРИЙ", compressed, "Глоссарий должен отбрасываться первым")

    def test_tiny_budget_does_not_crash_and_keeps_status(self):
        dump = build_context_dump(root=self.root, budget=250)
        self.assertTrue(dump)
        self.assertIn("СТАТУС ПРОЕКТА", dump)
        self.assertLessEqual(estimate_tokens(dump), 250)

    def test_micro_budget_does_not_crash(self):
        """Бюджет меньше минимально возможного каркаса — не падает, режет до предела."""
        dump = build_context_dump(root=self.root, budget=10)
        self.assertTrue(dump)
        self.assertIn("СТАТУС ПРОЕКТА", dump)
        self.assertLess(estimate_tokens(dump), 200)

    def test_missing_root_sections_dont_crash(self):
        """Пустой проект (нет plans/history/PRD) — без падений."""
        root = Path(tempfile.mkdtemp(prefix="brain_budget_empty_"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "agents").mkdir()
        (root / "agents" / "STATUS.md").write_text("# Статус\nOK\n", encoding="utf-8")
        dump = build_context_dump(root=root)
        self.assertIn("СТАТУС ПРОЕКТА", dump)
        self.assertNotIn("ГЛОССАРИЙ", dump)
        # с бюджетом тоже не падает
        self.assertTrue(build_context_dump(root=root, budget=100))


if __name__ == "__main__":
    unittest.main()
