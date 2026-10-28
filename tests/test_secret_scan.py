#!/usr/bin/env python3
"""
Тесты секрет-сканера (PLAN-004, Этап 1) и GitHub-аннотаций check_integrity.

Все находки создаются во временных каталогах — репозиторий не затрагивается.

Запуск:  python -m unittest discover -s tests -v
"""

import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import secret_scan  # noqa: E402
from check_integrity import log_check  # noqa: E402


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_secret_test_"))
    (root / "agents").mkdir()
    return root


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class TestDetection(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def _scan(self, rel, text):
        p = write(self.root, rel, text)
        return secret_scan.scan_files([p], root=self.root)

    def test_detects_known_token_types(self):
        cases = [
            ("api.md", "ключ: sk-proj-REDACTED-DUMMY", "OpenAI"),
            ("api.md", "токен: ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4o5P6q7R8", "GitHub"),
            ("api.md", "slack: xoxb-REDACTED-DUMMY", "Slack"),
            ("api.md", "aws: AKIA" + "ABCDEFGHIJKLMNOP", "AWS"),
            ("key.md", "-----BEGIN RSA PRIVATE KEY-----", "Private key"),
        ]
        for rel, line, expect in cases:
            with self.subTest(kind=expect):
                findings = self._scan(rel, line)
                self.assertEqual(len(findings), 1, f"{expect}: {findings}")
                self.assertIn(expect, findings[0]["kind"])
                self.assertEqual(findings[0]["line"], 1)

    def test_detects_generic_password(self):
        findings = self._scan("cfg.md", 'password = "Hunter2SuperSecret"')
        self.assertEqual(len(findings), 1)
        self.assertIn("password", findings[0]["kind"].lower())

    def test_placeholders_are_not_secrets(self):
        ok_lines = [
            "api_key = ${DATABASE_URL}",
            "token: {SERVICE_TOKEN}",
            "password: your_token_here_please",
            "secret = os.environ.get('SECRET_KEY')",
            "password: <insert-password>",
            "password: changeme",
            "api_key: xxxxxxxxxxxxxx",
            "password: short",           # < 8 символов
        ]
        for line in ok_lines:
            with self.subTest(line=line):
                findings = self._scan("cfg.md", line)
                self.assertEqual(findings, [], f"Ложное срабатывание: {line}")

    def test_real_and_placeholder_on_same_file(self):
        text = ("token: sk-ant-Apikey1234567890abcdefghij\n"
                "secret = ${BACKUP_TOKEN}\n")
        findings = self._scan("mix.md", text)
        self.assertEqual(len(findings), 1)
        self.assertIn("Anthropic", findings[0]["kind"])

    def test_off_marker_skips_whole_file(self):
        text = "# secretscan: off\npassword: TotallyReal123Secret\n"
        self.assertEqual(self._scan("skip.md", text), [])

    def test_snippet_is_masked(self):
        secret = "sk-proj-" + "A" * 30
        findings = self._scan("leak.md", f"key: {secret}")
        self.assertEqual(len(findings), 1)
        self.assertNotIn(secret, findings[0]["snippet"])
        self.assertIn("…", findings[0]["snippet"])

    def test_line_numbers_are_correct(self):
        text = "первая строка\nвторая строка\npassword: Hunter2SuperSecret\n"
        findings = self._scan("lines.md", text)
        self.assertEqual(findings[0]["line"], 3)


class TestProjectScan(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_scan_project_covers_untracked_files(self):
        """Секрет в новом (не закоммиченном) файле тоже должен находиться."""
        write(self.root, "docs/leak.md", "password: Hunter2SuperSecret99")
        findings = secret_scan.scan_project(root=self.root)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["file"], "docs/leak.md")

    def test_tests_dir_is_skipped(self):
        """Фикстуры в tests/ с намеренными фейками не блокируют коммит."""
        write(self.root, "tests/fake_secrets.py", "password = 'Hunter2SuperSecret99'")
        self.assertEqual(secret_scan.scan_project(root=self.root), [])

    def test_env_example_is_skipped(self):
        write(self.root, ".env.example", "API_KEY=SuperSecretValue123")
        self.assertEqual(secret_scan.scan_project(root=self.root), [])

    def test_clean_project_finds_nothing(self):
        write(self.root, "agents/STATUS.md", "# Статус\napi_key = ${KEY}\n")
        self.assertEqual(secret_scan.scan_project(root=self.root), [])

    def test_main_exit_codes(self):
        import io
        from contextlib import redirect_stdout
        clean = make_root()
        self.addCleanup(shutil.rmtree, clean, ignore_errors=True)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(secret_scan.main(["--root", str(clean)]), 0)
            write(clean, "leak.md", "password: Hunter2SuperSecret99")
            self.assertEqual(secret_scan.main(["--root", str(clean)]), 1)


class TestGithubAnnotations(unittest.TestCase):
    """FAIL/WARN дублируются ::error/::warning при GITHUB_ACTIONS=true."""

    def _capture(self, env_value, name, passed, details="", file=None, is_warning=False):
        old = os.environ.get("GITHUB_ACTIONS")
        buf = io.StringIO()
        try:
            if env_value is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = env_value
            with redirect_stdout(buf):
                log_check(name, passed, details, is_warning=is_warning, file=file)
        finally:
            if old is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = old
        return buf.getvalue()

    def test_annotation_emitted_in_actions(self):
        out = self._capture("true", "Секреты в файлах", False,
                            "leak.md:1", file="leak.md")
        self.assertIn("::error file=leak.md::", out)
        self.assertIn("Секреты в файлах", out)

    def test_warning_level_for_warn_checks(self):
        out = self._capture("true", "Некая проверка", False, "детали", is_warning=True)
        self.assertIn("::warning::", out)
        self.assertNotIn("::error", out)

    def test_no_annotation_outside_actions(self):
        out = self._capture(None, "Проверка", False, "детали")
        self.assertNotIn("::", out)

    def test_no_annotation_for_passed_checks(self):
        out = self._capture("true", "Проверка", True)
        self.assertNotIn("::error", out)


if __name__ == "__main__":
    unittest.main()
