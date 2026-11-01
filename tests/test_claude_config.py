#!/usr/bin/env python3
"""
Тесты конфигурации Claude Code (PLAN-003, Этап 3): субагенты, skills, слэш-команды.
Форматы сверены с официальной документацией (code.claude.com/docs/en/sub-agents, /skills, /hooks).

Запуск:  python -m unittest discover -s tests -v
"""

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"
COMMANDS_DIR = PROJECT_ROOT / ".claude" / "commands"


def parse_frontmatter(path: Path) -> dict:
    """Минимальный парсер YAML-frontmatter (stdlib-only): первая строка '---', вторая '---'."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


class TestSubagents(unittest.TestCase):
    """Субагенты: .claude/agents/*.md, обязательны name и description (иначе файл игнорируется)."""

    REQUIRED = {"planner", "implementer", "reviewer", "test-writer",
                "security-auditor", "debugger", "docs-keeper"}

    def test_expected_agents_exist(self):
        present = {p.stem for p in AGENTS_DIR.glob("*.md")}
        self.assertEqual(self.REQUIRED - present, set(), f"Нет субагентов: {self.REQUIRED - present}")

    def test_frontmatter_valid(self):
        names = []
        for f in AGENTS_DIR.glob("*.md"):
            fm = parse_frontmatter(f)
            with self.subTest(agent=f.name):
                self.assertIn("name", fm, f"{f.name}: нет обязательного поля name")
                self.assertIn("description", fm, f"{f.name}: нет обязательного поля description")
                self.assertNotIn(":", fm["name"], f"{f.name}: имя не может содержать ':'")
                self.assertNotIn("-", fm["name"][0], f"{f.name}: имя не может начинаться с '-'")
                self.assertTrue(fm["description"].strip(), f"{f.name}: пустой description")
                names.append(fm["name"])
        self.assertEqual(len(names), len(set(names)), f"Имена субагентов дублируются: {names}")

    def test_readonly_agents_have_no_write_tools(self):
        """planner/reviewer/security-auditor должны быть read-only (tools без Write/Edit)."""
        for name in ("planner", "reviewer", "security-auditor"):
            fm = parse_frontmatter(AGENTS_DIR / f"{name}.md")
            tools = fm.get("tools", "")
            with self.subTest(agent=name):
                self.assertNotIn("Write", tools, f"{name}: не должен иметь Write")
                self.assertNotIn("Edit", tools, f"{name}: не должен иметь Edit")

    def test_descriptions_are_short(self):
        """Описание субагента — это контекст каждой сессии: держим коротким (<600 символов)."""
        for f in AGENTS_DIR.glob("*.md"):
            fm = parse_frontmatter(f)
            self.assertLess(len(fm.get("description", "")), 600, f"{f.name}: description слишком длинный")


class TestSkills(unittest.TestCase):
    """Skills: .claude/skills/<name>/SKILL.md с description."""

    REQUIRED = {"session-handoff", "bug-triage", "adr-writer", "release-checklist"}

    def test_expected_skills_exist(self):
        present = {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}
        self.assertEqual(self.REQUIRED - present, set(), f"Нет скиллов: {self.REQUIRED - present}")

    def test_skill_frontmatter_has_description(self):
        for f in SKILLS_DIR.glob("*/SKILL.md"):
            fm = parse_frontmatter(f)
            with self.subTest(skill=f.parent.name):
                self.assertIn("description", fm, f"{f.parent.name}: нет description")
                self.assertTrue(fm["description"].strip())
                # первая строка файла — открывающий '---' (иначе frontmatter игнорируется)
                first = f.read_text(encoding="utf-8", errors="replace").splitlines()[0]
                self.assertEqual(first.strip(), "---", f"{f.parent.name}: frontmatter не в первой строке")

    def test_skill_bodies_non_empty(self):
        for f in SKILLS_DIR.glob("*/SKILL.md"):
            body = f.read_text(encoding="utf-8", errors="replace")
            self.assertGreater(len(body), 300, f"{f.parent.name}: тело скилла слишком короткое")


class TestCommands(unittest.TestCase):
    """Слэш-команды: .claude/commands/*.md, обязательны description; тонкие обёртки над brain.py."""

    REQUIRED = {"plan", "bug", "adr", "review", "handoff", "status"}

    def test_expected_commands_exist(self):
        present = {p.stem for p in COMMANDS_DIR.glob("*.md")}
        self.assertEqual(self.REQUIRED - present, set(), f"Нет команд: {self.REQUIRED - present}")

    def test_commands_have_description(self):
        for f in COMMANDS_DIR.glob("*.md"):
            fm = parse_frontmatter(f)
            with self.subTest(command=f.stem):
                self.assertIn("description", fm, f"{f.name}: нет description")
                self.assertTrue(fm["description"].strip())

    def test_brain_commands_wrap_cli(self):
        """Команды, обёртывающие brain.py, должны реально ссылаться на CLI."""
        for name in ("plan", "bug", "adr", "status"):
            text = (COMMANDS_DIR / f"{name}.md").read_text(encoding="utf-8", errors="replace")
            self.assertIn("brain.py", text, f"/{name}: не ссылается на brain.py")

    def test_no_file_scheme_links(self):
        for f in list(AGENTS_DIR.glob("*.md")) + list(SKILLS_DIR.glob("*/SKILL.md")) + list(COMMANDS_DIR.glob("*.md")):
            self.assertNotIn("](file:///", f.read_text(encoding="utf-8", errors="replace"),
                             f"{f.name}: устаревшие ссылки file:///")


if __name__ == "__main__":
    unittest.main()
