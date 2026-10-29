#!/usr/bin/env python3
"""
Тесты `brain.py sync` (PLAN-003/006): конфиги AI-инструментов
должны генерироваться из agents/rules/CORE_RULES.md и не разъезжаться.

PLAN-006 добавляет: .codex/hooks.json, opencode.jsonc, трансформы
Claude -> OpenCode (команды/агенты) и зеркала скиллов.

Запуск:  python -m unittest discover -s tests -v
"""

import io
import json
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import brain  # noqa: E402

# Шаблоны без {{CORE_RULES}}: JSON-конфиги (подстановка правил там не нужна)
NO_MARKER_TPLS = {"hooks.json.tpl", "opencode.jsonc.tpl"}


def _strip_json_comments(text: str) -> str:
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


class TestSync(unittest.TestCase):
    def test_canonical_and_templates_exist(self):
        self.assertTrue(brain.SYNC_CORE.is_file(), "Нет канона agents/rules/CORE_RULES.md")
        for tpl, _target in brain.SYNC_SPECS:
            self.assertTrue(tpl.is_file(), f"Нет шаблона {tpl.name}")
            if tpl.name not in NO_MARKER_TPLS:
                self.assertIn(
                    "{{CORE_RULES}}", tpl.read_text(encoding="utf-8"),
                    f"{tpl.name}: нет маркера {{CORE_RULES}}",
                )

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
        core_spec_targets = {t for _tpl, t in brain.SYNC_SPECS}
        for _tpl, target, _content in brain.render_sync_configs():
            if target not in core_spec_targets:
                continue  # маркер канона обязателен только для конфигов из CORE_RULES.md
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


class TestCodexRender(unittest.TestCase):
    """PLAN-006, Этап 1: .codex/hooks.json."""

    @classmethod
    def setUpClass(cls):
        cls.target = PROJECT_ROOT / ".codex" / "hooks.json"
        cls.data = json.loads(_strip_json_comments(cls.target.read_text(encoding="utf-8")))

    def test_hooks_json_is_valid_and_has_events(self):
        self.assertEqual(
            sorted(self.data["hooks"]),
            ["PostToolUse", "PreToolUse", "SessionStart", "Stop"],
        )

    def test_hooks_reuse_shared_python_scripts(self):
        commands = [
            h["command"]
            for groups in self.data["hooks"].values()
            for group in groups
            for h in group["hooks"]
        ]
        self.assertEqual(len(commands), 4)
        for cmd in commands:
            self.assertIn("git rev-parse --show-toplevel", cmd, "Путь должен вести от корня git")
            self.assertIn("agents/tools/hooks/", cmd, "Должны использоваться общие python-хуки")

    def test_pre_tool_use_covers_edit_read_bash(self):
        matchers = [g["matcher"] for g in self.data["hooks"]["PreToolUse"]]
        joined = " ".join(matchers)
        for tool in ("Edit", "Write", "apply_patch", "Read", "Bash"):
            self.assertIn(tool, joined, f"PreToolUse: нет мэтчера для {tool}")

    def test_no_core_rules_placeholder_left(self):
        text = self.target.read_text(encoding="utf-8")
        self.assertNotIn("{{CORE_RULES}}", text)


class TestOpenCodeRender(unittest.TestCase):
    """PLAN-006, Этап 2: opencode.jsonc, команды, агенты, скиллы."""

    @classmethod
    def setUpClass(cls):
        cls.target = PROJECT_ROOT / "opencode.jsonc"
        cls.data = json.loads(_strip_json_comments(cls.target.read_text(encoding="utf-8")))

    def test_opencode_config_schema_and_servers(self):
        self.assertEqual(self.data["$schema"], "https://opencode.ai/config.json")
        servers = self.data["mcp"]["servers"]
        self.assertEqual(len(servers), 7)
        for name, srv in servers.items():
            self.assertEqual(srv["type"], "local", f"{name}: нужен type local")
            self.assertIsInstance(srv["command"], list, f"{name}: command — массив")

    def test_opencode_secrets_use_env_substitution(self):
        text = _strip_json_comments(self.target.read_text(encoding="utf-8"))
        self.assertNotIn("${", text, "OpenCode не раскрывает ${VAR} — нужен {env:VAR}")
        self.assertIn("{env:GITHUB_TOKEN}", text)

    def test_opencode_permissions_deny_secret_edits(self):
        rules = self.data["permissions"]
        denied = {r["resource"] for r in rules if r["effect"] == "deny"}
        self.assertTrue({"*.env", "*.pem", "*.key"} <= denied, f"Нет deny-правил секретов: {rules}")
        allowed = {r["resource"] for r in rules if r["effect"] == "allow"}
        self.assertIn("*.env.example", allowed, ".env.example должен оставаться редактируемым")

    def test_commands_transformed(self):
        pairs = [(s, t) for s, t, k in brain.SYNC_TRANSFORMS if k == "command"]
        self.assertEqual(len(pairs), 6, "Ожидалось 6 команд Claude")
        for src, target in pairs:
            text = target.read_text(encoding="utf-8")
            self.assertIn("description:", text, f"{target.name}: нет description")
            self.assertNotIn("argument-hint", text, f"{target.name}: остался Claude-ключ")
            self.assertNotIn("allowed-tools", text, f"{target.name}: остался Claude-ключ")
            # Тело-шаблон должен сохраниться: если канон использует $ARGUMENTS — зеркало тоже
            if "$ARGUMENTS" in src.read_text(encoding="utf-8"):
                self.assertIn("$ARGUMENTS", text, f"{target.name}: тело потеряло $ARGUMENTS")

    def test_agents_transformed(self):
        targets = [t for _s, t, k in brain.SYNC_TRANSFORMS if k == "agent"]
        self.assertEqual(len(targets), 7, "Ожидалось 7 агентов Claude")
        for target in targets:
            text = target.read_text(encoding="utf-8")
            self.assertIn("description:", text, f"{target.name}: нет description")
            self.assertIn("mode: subagent", text, f"{target.name}: нет mode: subagent")
            for banned in ("name:", "tools:", "model:"):
                self.assertNotIn(f"\n{banned}", text, f"{target.name}: остался Claude-ключ {banned}")

    def test_read_only_agents_deny_edit_and_shell(self):
        text = (PROJECT_ROOT / ".opencode" / "agents" / "planner.md").read_text(encoding="utf-8")
        self.assertIn("permissions:", text)
        self.assertIn("effect: deny", text)
        self.assertIn("action: edit", text)
        self.assertIn("action: shell", text)

    def test_writing_agents_have_no_deny(self):
        text = (PROJECT_ROOT / ".opencode" / "agents" / "implementer.md").read_text(encoding="utf-8")
        self.assertNotIn("permissions:", text, "implementer пишет файлы — deny не нужен")

    def test_skills_mirrored_byte_exact(self):
        for name in ("second-brain", "adr-writer", "bug-triage", "release-checklist", "session-handoff"):
            src_name = "second-brain" if name == "second-brain" else name
            src = PROJECT_ROOT / ".claude" / "skills" / src_name / "SKILL.md"
            oc = PROJECT_ROOT / ".opencode" / "skills" / name / "SKILL.md"
            self.assertEqual(
                brain._read_norm(oc), brain._read_norm(src),
                f"Скилл {name}: зеркало .opencode разошлось с каноном",
            )


class TestTransformOpencodeMd(unittest.TestCase):
    """Трансформа frontmatter: чистые функции."""

    def test_agent_read_only_gets_full_deny(self):
        src = "---\nname: x\ndescription: d\n tools: Read, Grep, Glob\nmodel: opus\n---\n\nBody $ARGUMENTS\n"
        out = brain.transform_opencode_md(src, "agent")
        self.assertIn("mode: subagent", out)
        self.assertIn("action: edit", out)
        self.assertIn("action: shell", out)
        self.assertNotIn("model:", out)
        self.assertNotIn("name:", out)
        self.assertIn("Body $ARGUMENTS", out)

    def test_agent_with_tools_keeps_permissions_out(self):
        src = "---\ndescription: d\ntools: Read, Write, Edit, Bash\n---\nBody\n"
        out = brain.transform_opencode_md(src, "agent")
        self.assertNotIn("permissions:", out)

    def test_command_keeps_description_drops_hint(self):
        src = "---\ndescription: d\nargument-hint: [x]\n---\nDo $ARGUMENTS\n"
        out = brain.transform_opencode_md(src, "command")
        self.assertIn("description: d", out)
        self.assertNotIn("argument-hint", out)
        self.assertIn("Do $ARGUMENTS", out)

    def test_text_without_frontmatter_passthrough(self):
        self.assertEqual(brain.transform_opencode_md("plain", "command"), "plain")


class TestPluginFile(unittest.TestCase):
    """PLAN-006, Этап 3: .opencode/plugins/second_brain/index.ts."""

    @classmethod
    def setUpClass(cls):
        cls.text = (PROJECT_ROOT / ".opencode" / "plugins" / "second_brain" / "index.ts").read_text(encoding="utf-8")

    def test_plugin_wired_to_shared_gate(self):
        self.assertIn('id: "second_brain"', self.text)
        self.assertIn('ctx.permission.hook("evaluate"', self.text)
        self.assertIn("pre_tool_gate.py", self.text)

    def test_plugin_fails_open(self):
        self.assertIn("spawnSync", self.text)
        self.assertIn("timeout: 3000", self.text)
        # fail-open: любой сбой возвращает пустое решение без throw
        self.assertIn("catch", self.text)

    def test_plugin_maps_actions_to_claude_payload(self):
        for marker in ('"edit"', '"read"', '"shell"', '"Edit"', '"Read"', '"Bash"'):
            self.assertIn(marker, self.text, f"Плагин: нет маппинга {marker}")


if __name__ == "__main__":
    unittest.main()
