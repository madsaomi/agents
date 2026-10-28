#!/usr/bin/env python3
"""
Тесты пресетов стека и upgrade (PLAN-003, Этап 5).

Пресеты применяются во временные каталоги — репозиторий не затрагивается.

Запуск:  python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import brain  # noqa: E402

EXPECTED_PRESETS = {"django-drf", "aiogram-bot", "fastapi", "nextjs"}


def make_target_project() -> Path:
    """Создаёт скелет целевого проекта (agents/ + .claude/) во временной папке."""
    root = Path(tempfile.mkdtemp(prefix="brain_preset_test_"))
    (root / "agents" / "rules").mkdir(parents=True)
    (root / "agents" / "architecture").mkdir(parents=True)
    (root / "agents" / "testing").mkdir(parents=True)
    (root / "agents" / "history").mkdir(parents=True)
    (root / ".claude" / "agents").mkdir(parents=True)
    (root / ".claude" / "skills").mkdir(parents=True)
    return root


class TestPresetManifests(unittest.TestCase):
    """Каждый пресет — валидный манифест, все src-файлы существуют."""

    def test_expected_presets_present(self):
        self.assertEqual(set(brain.list_presets()), EXPECTED_PRESETS)

    def test_manifests_valid(self):
        for name in brain.list_presets():
            with self.subTest(preset=name):
                preset_dir = brain.PRESETS_SOURCE_DIR / name
                manifest = json.loads((preset_dir / "preset.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["name"], name)
                self.assertTrue(manifest.get("description"))
                self.assertTrue(manifest.get("files"), "Манифест без файлов")
                for entry in manifest["files"]:
                    self.assertTrue((preset_dir / entry["src"]).is_file(),
                                    f"{name}: нет файла {entry['src']}")
                    # dst — относительный путь внутри проекта, без выхода наружу
                    dst = entry["dst"]
                    self.assertFalse(dst.startswith("/") and ":" not in dst[:3])
                    self.assertNotIn("..", Path(dst).parts, f"{name}: подозрительный dst {dst}")

    def test_django_preset_covers_stack(self):
        """django-drf — флагманский пресет: полный набор артефактов."""
        manifest = json.loads(
            (brain.PRESETS_SOURCE_DIR / "django-drf" / "preset.json").read_text(encoding="utf-8")
        )
        dsts = {e["dst"] for e in manifest["files"]}
        for required in (
            "agents/rules/CODING_STANDARDS.md",
            "agents/architecture/CODEBASE_MAP.md",
            "agents/testing/QA_CHECKLIST.md",
            ".env.example",
            "docker-compose.yml",
            ".github/workflows/ci.yml",
            ".claude/agents/django-migration-reviewer.md",
            ".claude/skills/new-drf-endpoint/SKILL.md",
        ):
            self.assertIn(required, dsts, f"django-drf: нет {required}")

    def test_preset_agents_have_valid_frontmatter(self):
        """Субагенты пресетов должны валидироваться как и базовые (.claude/agents)."""
        for preset in brain.list_presets():
            agents_dir = brain.PRESETS_SOURCE_DIR / preset / "agents"
            if not agents_dir.is_dir():
                continue
            for f in agents_dir.glob("*.md"):
                with self.subTest(preset=preset, agent=f.name):
                    lines = f.read_text(encoding="utf-8").splitlines()
                    self.assertEqual(lines[0].strip(), "---", f"{f.name}: нет frontmatter")
                    fm = "\n".join(lines[1:20])
                    self.assertIn("name:", fm)
                    self.assertIn("description:", fm)

    def test_preset_skills_have_valid_frontmatter(self):
        for preset in brain.list_presets():
            skills_dir = brain.PRESETS_SOURCE_DIR / preset / "skills"
            if not skills_dir.is_dir():
                continue
            for f in skills_dir.glob("*/SKILL.md"):
                with self.subTest(preset=preset, skill=f.parent.name):
                    lines = f.read_text(encoding="utf-8").splitlines()
                    self.assertEqual(lines[0].strip(), "---")
                    self.assertIn("description:", "\n".join(lines[1:20]))

    def test_env_examples_have_no_real_secrets(self):
        """
        env.example — шаблон: значения-заглушки, не реальные ключи.
        Проверяются только чувствительные ключи (TOKEN/SECRET/PASSWORD/KEY/DSN).
        """
        sensitive = ("TOKEN", "SECRET", "PASSWORD", "KEY", "DSN", "CREDENTIAL")
        placeholders = ("change-me", "replace-me", "example", "your-", "xxxx", "...")
        for preset in brain.list_presets():
            env = brain.PRESETS_SOURCE_DIR / preset / "files" / "env.example"
            if not env.is_file():
                continue
            text = env.read_text(encoding="utf-8")
            self.assertIn("НИКОГДА не коммить", text, f"{preset}: нет предупреждения про .env")
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.upper(), value.strip()
                if not any(s in key for s in sensitive):
                    continue  # не-секретные ключи (хосты, бд, режимы) не проверяем
                if any(s in key for s in ("_TTL", "_EXPIRE", "_DAYS", "_MINUTES", "_LIMIT", "_PORT")):
                    continue  # числовые настройки — не секреты
                if not value or value.startswith("${"):
                    continue
                is_placeholder = any(p in value.lower() or p in value for p in placeholders)
                with self.subTest(preset=preset, var=key):
                    self.assertTrue(is_placeholder,
                                    f"{preset}: значение {key} не похоже на заглушку — убери секрет!")


class TestApplyPreset(unittest.TestCase):
    def setUp(self):
        self.root = make_target_project()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def _apply(self, name, force=False):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            return brain.apply_preset(name, force=force, root=self.root), buf.getvalue()

    def test_applies_all_files_to_empty_project(self):
        applied, out = self._apply("django-drf")
        self.assertEqual(applied, 11, out)
        self.assertTrue((self.root / "agents" / "rules" / "CODING_STANDARDS.md").is_file())
        self.assertTrue((self.root / ".env.example").is_file())
        self.assertTrue((self.root / ".claude" / "agents" / "django-migration-reviewer.md").is_file())
        # lock записан
        self.assertTrue((self.root / "agents" / ".preset_lock.json").is_file())

    def test_does_not_overwrite_user_files(self):
        """Повторное применение без force не затирает правки пользователя."""
        self._apply("fastapi")
        target = self.root / "agents" / "rules" / "CODING_STANDARDS.md"
        target.write_text("# МОИ ПРАВКИ ПОЛЬЗОВАТЕЛЯ\n", encoding="utf-8")
        applied, out = self._apply("fastapi")
        self.assertEqual(applied, 0)
        self.assertIn("пользовательских", out)
        self.assertEqual(target.read_text(encoding="utf-8"), "# МОИ ПРАВКИ ПОЛЬЗОВАТЕЛЯ\n")

    def test_force_overwrites(self):
        self._apply("fastapi")
        target = self.root / "agents" / "rules" / "CODING_STANDARDS.md"
        target.write_text("# Правки\n", encoding="utf-8")
        applied, _ = self._apply("fastapi", force=True)
        self.assertGreater(applied, 0)
        self.assertNotEqual(target.read_text(encoding="utf-8"), "# Правки\n")

    def test_unknown_preset(self):
        applied, out = self._apply("cobol-mainframe")
        self.assertEqual(applied, 0)
        self.assertIn("не найден", out)

    def test_all_presets_apply_cleanly(self):
        for name in brain.list_presets():
            root = make_target_project()
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    applied = brain.apply_preset(name, root=root)
                self.assertGreater(applied, 0, f"{name}: ничего не применено\n{buf.getvalue()}")
            finally:
                shutil.rmtree(root, ignore_errors=True)


class TestUpgrade(unittest.TestCase):
    def setUp(self):
        self.root = make_target_project()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            brain.apply_preset("aiogram-bot", root=self.root)

    def _upgrade(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            return brain.upgrade_tool(root=self.root), buf.getvalue()

    def test_upgrade_keeps_user_edits(self):
        target = self.root / "agents" / "rules" / "CODING_STANDARDS.md"
        target.write_text("# Мои правила\n", encoding="utf-8")
        self._upgrade()
        self.assertEqual(target.read_text(encoding="utf-8"), "# Мои правила\n", "upgrade затёр правки пользователя!")

    def test_upgrade_refreshes_untouched_files(self):
        """Нетронутый пользователем шаблон обновляется до версии пресета."""
        target = self.root / "agents" / "rules" / "CODING_STANDARDS.md"
        target.write_text("# Устаревшая копия\n", encoding="utf-8")
        # lock хранит старый hash — обновляем lock, имитируя «нашу» установку
        lock_path = self.root / "agents" / ".preset_lock.json"
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["agents/rules/CODING_STANDARDS.md"]["sha256"] = brain._sha256(target)
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        self._upgrade()
        content = target.read_text(encoding="utf-8")
        self.assertNotEqual(content, "# Устаревшая копия\n", "upgrade не обновил нетронутый шаблон")

    def test_upgrade_restores_missing_files(self):
        target = self.root / ".env.example"
        target.unlink()
        self._upgrade()
        self.assertTrue(target.is_file(), "upgrade не восстановил удалённый шаблон")

    def test_upgrade_never_touches_history(self):
        log = self.root / "agents" / "history" / "session_001.md"
        log.write_text("# Важная история\n", encoding="utf-8")
        self._upgrade()
        self.assertEqual(log.read_text(encoding="utf-8"), "# Важная история\n")


class TestProjectRootDetection(unittest.TestCase):
    def test_dev_mode_uses_repo_root(self):
        """Из репозитория шаблона brain.py находит корень: cwd или своё расположение."""
        # dev-режим: PROJECT_ROOT указывает на репозиторий (cwd в тестах — корень)
        self.assertEqual(brain.PROJECT_ROOT, PROJECT_ROOT)
        self.assertEqual(brain.AGENTS_DIR, PROJECT_ROOT / "agents")

    def test_presets_source_next_to_script(self):
        self.assertEqual(brain.PRESETS_SOURCE_DIR, brain.SCRIPT_DIR.parent / "presets")
        self.assertTrue(brain.PRESETS_SOURCE_DIR.is_dir(), "Пресеты должны лежать рядом с инструментом")


if __name__ == "__main__":
    unittest.main()
