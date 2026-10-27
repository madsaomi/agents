#!/usr/bin/env python3
"""
Тесты `brain.py sync` (PLAN-003, Этап 1): конфиги AI-инструментов
должны генерироваться из agents/rules/CORE_RULES.md и не разъезжаться.

Запуск:  python -m unittest discover -s tests -v
"""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import brain  # noqa: E402


class TestSync(unittest.TestCase):
    def test_canonical_and_templates_exist(self):
        self.assertTrue(brain.SYNC_CORE.is_file(), "Нет канона agents/rules/CORE_RULES.md")
        for tpl, _target in brain.SYNC_SPECS:
            self.assertTrue(tpl.is_file(), f"Нет шаблона {tpl.name}")
            self.assertIn("{{CORE_RULES}}", tpl.read_text(encoding="utf-8"), f"{tpl.name}: нет маркера {{CORE_RULES}}")

    def test_no_sync_drift(self):
        """Все сгенерированные конфиги должны байт-в-байт совпадать с рендером канона."""
        drift = []
        for _tpl, target, content in brain.render_sync_configs():
            if not target.is_file():
                drift.append(f"{target.name}: отсутствует")
            elif brain._read_norm(target) != content:
                drift.append(f"{target.name}: разошёлся с CORE_RULES.md")
        self.assertEqual(drift, [], f"Дрейф конфигов: {drift}. Запусти: python brain.py sync")

    def test_generated_files_carry_marker(self):
        for _tpl, target, _content in brain.render_sync_configs():
            head = target.read_text(encoding="utf-8", errors="replace")[:300]
            self.assertIn("brain.py sync", head, f"{target.name}: нет маркера GENERATED")

    def test_check_mode_returns_zero_when_in_sync(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = brain.sync_tools(check=True)
        self.assertEqual(code, 0, buf.getvalue())

    def test_core_rules_cover_hard_prohibitions(self):
        core = brain.SYNC_CORE.read_text(encoding="utf-8")
        for marker in ("Plan-First", "prompt injection", "agents/history", "CORE_RULES.md"):
            self.assertIn(marker, core, f"CORE_RULES.md: нет обязательного блока '{marker}'")


if __name__ == "__main__":
    unittest.main()
