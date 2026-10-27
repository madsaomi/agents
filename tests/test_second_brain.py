#!/usr/bin/env python3
"""
Тесты целостности «Второго Мозга» (PLAN-003, Этап 0).
Только стандартная библиотека Python (unittest).

Запуск:  python -m unittest discover -s tests -v
"""

import io
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"
TOOLS_DIR = AGENTS_DIR / "tools"

sys.path.insert(0, str(TOOLS_DIR))

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#")


def iter_markdown_files():
    yield PROJECT_ROOT / "AGENTS.md"
    yield PROJECT_ROOT / "README.md"
    for md in AGENTS_DIR.rglob("*.md"):
        yield md


class TestMarkdownLinks(unittest.TestCase):
    """Все локальные ссылки в .md должны резолвиться относительно документа."""

    def test_local_links_resolve(self):
        broken = []
        checked = 0
        for md in iter_markdown_files():
            if not md.is_file():
                continue
            content = md.read_text(encoding="utf-8", errors="replace")
            content_no_code = re.sub(r"```[\s\S]*?```", "", content)
            for _text, raw_url in LINK_PATTERN.findall(content_no_code):
                url = raw_url.strip()
                if url.startswith(EXTERNAL_PREFIXES):
                    continue
                target_part = url.split("#")[0]
                if not target_part:
                    continue
                if target_part.startswith("file:///"):
                    broken.append((md.name, url, "устаревший формат file:///"))
                    continue
                target = (md.parent / target_part).resolve()
                checked += 1
                if not (target.exists() or target.with_suffix(".md").exists()):
                    broken.append((md.name, url, "не существует"))
        self.assertGreater(checked, 10, "Ссылки почти не найдены — проверка бессмысленна")
        self.assertEqual(broken, [], f"Битые ссылки: {broken}")

    def test_no_legacy_file_scheme_anywhere(self):
        offenders = []
        for md in iter_markdown_files():
            if md.is_file() and "](file:///" in md.read_text(encoding="utf-8", errors="replace"):
                offenders.append(md.name)
        self.assertEqual(offenders, [], f"Ссылки file:/// остались в: {offenders}")


class TestIntegrityChecker(unittest.TestCase):
    """check_integrity.py должен проходить без ошибок (exit 0)."""

    def test_run_integrity_check_passes(self):
        from check_integrity import run_integrity_check

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run_integrity_check(fix=False)
        self.assertEqual(code, 0, f"Проверка целостности упала:\n{buf.getvalue()[-2000:]}")


class TestBrainCli(unittest.TestCase):
    """Команды brain.py не должны падать."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "brain.py"), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
            timeout=60,
        )

    def test_status(self):
        result = self._run("status")
        self.assertEqual(result.returncode, 0, result.stderr[-1000:])

    def test_help(self):
        result = self._run("--help")
        self.assertEqual(result.returncode, 0, result.stderr[-1000:])


class TestNoPlaceholders(unittest.TestCase):
    """После init плейсхолдеров {{VAR}} в рабочих файлах быть не должно."""

    def test_no_unfilled_placeholders_outside_templates(self):
        templates_dir = AGENTS_DIR / "templates"
        offenders = {}
        for md in iter_markdown_files():
            if not md.is_file() or templates_dir in md.parents:
                continue
            found = set(re.findall(r"\{\{([A-Z_]+)\}\}", md.read_text(encoding="utf-8", errors="replace")))
            if found:
                offenders[str(md.relative_to(PROJECT_ROOT))] = found
        self.assertEqual(offenders, {}, f"Незаполненные плейсхолдеры: {offenders}")


if __name__ == "__main__":
    unittest.main()
