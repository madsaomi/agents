#!/usr/bin/env python3
"""
Тесты вики-связей памяти (PLAN-005, Этап 1).

Фикстуры создаются во временных каталогах — репозиторий не затрагивается.

Запуск:  python -m unittest discover -s tests -v
"""

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import links  # noqa: E402


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_links_test_"))
    for sub in ("plans", "tasks", "history", "bugs_and_fixes",
                "decisions", "walkthroughs"):
        (root / "agents" / sub).mkdir(parents=True, exist_ok=True)
    return root


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class TestExtraction(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_basic_extraction_with_line_numbers(self):
        write(self.root, "agents/plans/p.md",
              "Вступление.\nСм. [[BUG-001]] тут.\nИ ещё [[plan_002|второй план]].\n")
        found = links.find_links(self.root)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["target"], "BUG-001")
        self.assertEqual(found[0]["line"], 2)
        self.assertEqual(found[1]["target"], "plan_002")
        self.assertEqual(found[1]["label"], "второй план")

    def test_anchor_is_split_off(self):
        write(self.root, "agents/plans/p.md", "Секция [[ADR-001#решение]]\n")
        found = links.find_links(self.root)
        self.assertEqual(found[0]["target"], "ADR-001")

    def test_readme_is_skipped(self):
        write(self.root, "agents/plans/README.md", "[[BUG-001]]\n")
        self.assertEqual(links.find_links(self.root), [])

    def test_no_links_returns_empty(self):
        write(self.root, "agents/plans/p.md", "Обычный текст без связей.\n")
        self.assertEqual(links.find_links(self.root), [])


class TestResolution(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        write(self.root, "agents/bugs_and_fixes/BUG_001_subagent_model_issue.md",
              "# BUG-001\n")
        write(self.root, "agents/plans/plan_002_unified_cli.md", "# PLAN-002\n")
        write(self.root, "agents/decisions/ADR_003_sqlite.md", "# ADR-003\n")
        write(self.root, "agents/plans/p.md", "См. [[BUG-001]].\n")

    def test_id_resolves_to_prefixed_filename(self):
        """[[BUG-001]] -> файл BUG_001_subagent_model_issue.md (префикс по ID)."""
        r = links.links_for(self.root, "BUG-001")
        self.assertIsNotNone(r["file"])
        self.assertTrue(r["file"].endswith("BUG_001_subagent_model_issue.md"))

    def test_exact_basename_resolves(self):
        r = links.links_for(self.root, "plan_002_unified_cli.md")
        self.assertEqual(r["file"], "agents/plans/plan_002_unified_cli.md")

    def test_stem_resolves(self):
        r = links.links_for(self.root, "plan_002_unified_cli")
        self.assertEqual(r["file"], "agents/plans/plan_002_unified_cli.md")

    def test_case_and_separator_invariant(self):
        for q in ("bug-001", "BUG_001", "Bug001", "bug001"):
            with self.subTest(query=q):
                r = links.links_for(self.root, q)
                self.assertIsNotNone(r["file"], q)

    def test_outgoing_links(self):
        r = links.links_for(self.root, "agents/plans/p.md")
        self.assertEqual(len(r["outgoing"]), 1)
        self.assertTrue(r["outgoing"][0]["dst"].endswith(
            "BUG_001_subagent_model_issue.md"))

    def test_incoming_backlinks(self):
        r = links.links_for(self.root, "BUG-001")
        self.assertEqual(len(r["incoming"]), 1)
        self.assertEqual(r["incoming"][0]["src"], "agents/plans/p.md")
        self.assertEqual(r["incoming"][0]["line"], 1)

    def test_unresolved_reported(self):
        write(self.root, "agents/plans/p2.md", "См. [[MISSING-77]].\n")
        r = links.links_for(self.root, "agents/plans/p2.md")
        self.assertEqual(len(r["unresolved"]), 1)
        self.assertEqual(r["unresolved"][0]["target"], "MISSING-77")
        self.assertIsNone(r["unresolved"][0]["dst"])

    def test_unknown_query_returns_none_file(self):
        r = links.links_for(self.root, "NOPE-999")
        self.assertIsNone(r["file"])
        self.assertEqual(r["query"], "NOPE-999")

    def test_unresolved_links_helper(self):
        write(self.root, "agents/plans/p2.md",
              "См. [[MISSING-77]] и [[MISSING-77|подпись]].\n")
        broken = links.unresolved_links(self.root)
        self.assertEqual(len(broken), 2)
        self.assertTrue(all(l["target"] == "MISSING-77" for l in broken))


class TestPlaceholders(unittest.TestCase):
    """[[...]] и подобное — плейсхолдеры, не битые связи."""

    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def _count(self, text, placeholder=True):
        write(self.root, "agents/plans/p.md", text)
        found = links.find_links(self.root)
        return sum(1 for l in found if l["placeholder"] is placeholder)

    def test_ellipsis_placeholder(self):
        self.assertEqual(self._count("См. [[...]] для примера.\n"), 1)

    def test_short_target_is_placeholder(self):
        """[[bug#1]] -> цель 'bug' (< 4 символов) — плейсхолдер."""
        self.assertEqual(self._count("См. [[bug#1]] в тексте.\n"), 1)

    def test_special_chars_are_placeholders(self):
        for target in ("файл с пробелом", "bug#1", "a b", "café!"):
            with self.subTest(target=target):
                self.assertEqual(self._count(f"См. [[{target}]].\n"), 1)

    def test_placeholder_not_in_unresolved(self):
        write(self.root, "agents/plans/p.md",
              "[[...]] и [[bug#1]] и [[real-target-9]]\n")
        broken = links.unresolved_links(self.root)
        # плейсхолдеры не считаются; real-target-9 — валидная цель (нет файла)
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]["target"], "real-target-9")

    def test_real_id_is_not_placeholder(self):
        self.assertEqual(self._count("См. [[BUG-001]].\n", placeholder=False), 1)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        write(self.root, "agents/bugs_and_fixes/BUG_001_x.md", "# BUG-001\n")
        write(self.root, "agents/plans/p.md", "См. [[BUG-001]].\n")

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = links.main(argv + ["--root", str(self.root)])
        return code, buf.getvalue()

    def test_summary_without_args(self):
        code, out = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("Связи памяти", out)

    def test_query_output(self):
        code, out = self._run(["BUG-001"])
        self.assertEqual(code, 0)
        self.assertIn("Обратные ссылки", out)
        self.assertIn("agents/plans/p.md", out)

    def test_unresolved_clean(self):
        code, out = self._run(["--unresolved"])
        self.assertEqual(code, 0)
        self.assertIn("Битых", out)

    def test_unresolved_with_broken_link(self):
        write(self.root, "agents/plans/bad.md", "См. [[GHOST-42]].\n")
        code, out = self._run(["--unresolved"])
        self.assertEqual(code, 1)
        self.assertIn("GHOST-42", out)

    def test_unknown_query_exit_1(self):
        code, out = self._run(["NOPE-999"])
        self.assertEqual(code, 1)
        self.assertIn("не найдена", out)

    def test_combined_unresolved_and_query(self):
        code, out = self._run(["BUG-001", "--unresolved"])
        self.assertEqual(code, 0)
        self.assertIn("Битых", out)
        self.assertIn("Обратные ссылки", out)


if __name__ == "__main__":
    unittest.main()
