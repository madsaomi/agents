#!/usr/bin/env python3
"""
Тесты brain graph (PLAN-012 / TASK-011): mermaid-граф вики-связей.

Фикстуры создаются во временных каталогах — репозиторий не затрагивается.

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
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import graph  # noqa: E402

BRAIN = PROJECT_ROOT / "agents" / "tools" / "brain.py"


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_graph_test_"))
    agents = root / "agents"
    for sub in ("plans", "bugs_and_fixes"):
        (agents / sub).mkdir(parents=True)
    (agents / "plans" / "plan_900_a.md").write_text(
        "# План A\n\n[[BUG-900]]\n[[BUG-900]]\n[[plan_900_a]]\n", encoding="utf-8")
    (agents / "bugs_and_fixes" / "BUG_900_test.md").write_text(
        "# BUG-900\n\nСм. [[plan_900_a]]\n", encoding="utf-8")
    (agents / "plans" / "plan_901_b.md").write_text(
        "# План B\n\nБитая: [[MISSING-999]]\n", encoding="utf-8")
    return root


def run_cli(args, cwd=PROJECT_ROOT, timeout=120):
    return subprocess.run(
        [sys.executable, str(BRAIN), *args],
        cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
    )


class TestCollectGraph(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_nodes_and_edges(self):
        g = graph.collect_graph(root=self.root)
        self.assertEqual(g["summary"]["nodes"], 3)
        # plan_900_a→BUG_900 (2 объявления = 1 ребро count=2) + BUG_900→plan_900_a
        self.assertEqual(g["summary"]["edges"], 2)
        edge_map = {(e["src"], e["dst"]): e["count"] for e in g["edges"]}
        self.assertEqual(edge_map[("agents/plans/plan_900_a.md",
                                  "agents/bugs_and_fixes/BUG_900_test.md")], 2)
        self.assertEqual(edge_map[("agents/bugs_and_fixes/BUG_900_test.md",
                                  "agents/plans/plan_900_a.md")], 1)

    def test_self_link_is_not_an_edge(self):
        g = graph.collect_graph(root=self.root)
        self.assertFalse(any(e["src"] == e["dst"] for e in g["edges"]))

    def test_unresolved_links_captured(self):
        g = graph.collect_graph(root=self.root)
        self.assertEqual(g["summary"]["unresolved"], 1)
        self.assertEqual(g["unresolved"][0]["target"], "MISSING-999")
        self.assertEqual(g["unresolved"][0]["src"], "agents/plans/plan_901_b.md")

    def test_sections_parsed(self):
        g = graph.collect_graph(root=self.root)
        self.assertEqual(g["nodes"]["agents/plans/plan_900_a.md"]["section"], "plans")
        self.assertEqual(g["nodes"]["agents/bugs_and_fixes/BUG_900_test.md"]["section"],
                         "bugs_and_fixes")

    def test_json_serializable(self):
        loaded = json.loads(json.dumps(graph.collect_graph(root=self.root), ensure_ascii=False))
        self.assertIn("summary", loaded)


class TestRenderMermaid(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.mermaid = graph.render_mermaid(graph.collect_graph(root=self.root))

    def test_header_and_fences(self):
        self.assertTrue(self.mermaid.startswith("```mermaid\ngraph TD"))
        self.assertTrue(self.mermaid.rstrip().endswith("```"))

    def test_quoted_labels_with_section_emoji(self):
        self.assertIn('["📐 plan_900_a"]', self.mermaid)
        self.assertIn('["🐛 BUG_900_test"]', self.mermaid)

    def test_solid_and_dashed_edges(self):
        self.assertIn("-->", self.mermaid)            # разрешённая связь
        self.assertIn("-.->", self.mermaid)           # битая связь
        self.assertIn('p0["⚠️ MISSING-999"]', self.mermaid)  # фантом

    def test_ids_are_sanitized(self):
        # id узлов — только m<N>/p<N>, имена файлов только внутри кавычек
        body = self.mermaid.splitlines()
        for line in body:
            if line.startswith("    m") or line.startswith("    p"):
                node_id = line.strip().split("[")[0].split(" ")[0]
                self.assertRegex(node_id, r"^[mp]\d+$", line)

    def test_max_nodes_limit(self):
        g = graph.collect_graph(root=self.root)
        out = graph.render_mermaid(g, max_nodes=2)
        self.assertEqual(out.count('["'), 2)  # два узла + без фантомов (источник фантома отсечён)
        self.assertIn("и ещё 1", out)         # комментарий об отсечённых

    def test_empty_memory_renders_header_only(self):
        empty_root = Path(tempfile.mkdtemp(prefix="brain_graph_empty_"))
        self.addCleanup(shutil.rmtree, empty_root, ignore_errors=True)
        (empty_root / "agents" / "plans").mkdir(parents=True)
        out = graph.render_mermaid(graph.collect_graph(root=empty_root))
        self.assertIn("graph TD", out)
        self.assertNotIn("-.->", out)


class TestCliGraphSmoke(unittest.TestCase):
    def test_graph_runs_on_real_repo(self):
        proc = run_cli(["graph"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        self.assertIn("graph TD", proc.stdout)
        self.assertIn("Узлов:", proc.stdout)

    def test_graph_json_parseable(self):
        proc = run_cli(["graph", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        data = json.loads(proc.stdout)
        self.assertIn("summary", data)
        self.assertIn("nodes", data)

    def test_graph_max_flag_accepted(self):
        proc = run_cli(["graph", "--max", "5"])
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
