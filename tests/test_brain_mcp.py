#!/usr/bin/env python3
"""
Тесты MCP-сервера brain-mcp (PLAN-003, Этап 4).

Инструменты-функции тестируются без пакета mcp (stdlib-only);
серверный каркас тестируется только если SDK установлен (skipIf).

Запуск:  python -m unittest discover -s tests -v
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "mcp"))

import brain_mcp  # noqa: E402

try:
    import mcp  # noqa: F401
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False


def make_project() -> Path:
    """Минимальный скелет Second Brain во временной папке."""
    root = Path(tempfile.mkdtemp(prefix="brain_mcp_test_"))
    (root / "agents" / "plans").mkdir(parents=True)
    (root / "agents" / "tasks").mkdir(parents=True)
    (root / "agents" / "history").mkdir(parents=True)
    (root / "agents" / "bugs_and_fixes").mkdir(parents=True)
    (root / "agents" / "decisions").mkdir(parents=True)
    (root / "agents" / "rules").mkdir(parents=True)
    (root / "agents" / "tasks" / "active_task.md").write_text(
        "# Задача\n- [x] Готовый шаг\n- [ ] Шаг про celery timeout\n- [ ] Другой шаг\n",
        encoding="utf-8",
    )
    (root / "agents" / "bugs_and_fixes" / "BUG_001.md").write_text(
        "# BUG-001\nСимптом: celery timeout при долгой задаче.\nРешение: поднять visibility_timeout.\n",
        encoding="utf-8",
    )
    (root / "agents" / "history" / "session_001.md").write_text(
        "# Сессия\nНастройка celery timeout в kombu.\n",
        encoding="utf-8",
    )
    return root


class TestToolSurface(unittest.TestCase):
    """Состав инструментов должен соответствовать спецификации PLAN-003/PLAN-007."""

    EXPECTED = {
        "get_status", "create_plan", "log_bug", "search_memory", "complete_task", "end_session",
        "list_links", "list_claims", "get_stats",
    }

    def test_all_nine_tools_present(self):
        present = {fn.__name__ for fn in brain_mcp.TOOL_FUNCTIONS}
        self.assertEqual(present, self.EXPECTED)

    def test_tools_have_docstrings(self):
        """Docstring инструмента — это его описание в UI MCP-клиента."""
        for fn in brain_mcp.TOOL_FUNCTIONS:
            with self.subTest(tool=fn.__name__):
                self.assertTrue(fn.__doc__ and fn.__doc__.strip(), f"{fn.__name__}: нет docstring")

    def test_search_memory_accepts_root_override(self):
        """Функции с файловыми эффектами должны принимать root для тестируемости."""
        import inspect
        for fn in (brain_mcp.search_memory, brain_mcp.complete_task):
            self.assertIn("root", inspect.signature(fn).parameters, fn.__name__)


class TestSearchMemory(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_finds_match_in_bugs_and_history(self):
        out = brain_mcp.search_memory("celery timeout", root=self.root)
        self.assertIn("BUG_001.md", out)
        self.assertIn("session_001.md", out)

    def test_no_match(self):
        out = brain_mcp.search_memory("kubernetes ingress", root=self.root)
        self.assertIn("ничего не найдено", out)

    def test_empty_query(self):
        out = brain_mcp.search_memory("", root=self.root)
        self.assertIn("❌", out)

    def test_output_marks_data_not_command(self):
        """Защита от prompt injection: найденное помечается как данные."""
        out = brain_mcp.search_memory("celery", root=self.root)
        self.assertIn("данные", out)


class TestCompleteTask(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_completes_first_unchecked(self):
        out = brain_mcp.complete_task(root=self.root)
        self.assertIn("✅", out)
        active = (self.root / "agents" / "tasks" / "active_task.md").read_text(encoding="utf-8")
        self.assertIn("- [x] Шаг про celery timeout", active)
        self.assertIn("- [ ] Другой шаг", active)  # следующий не тронут

    def test_completes_matching_step(self):
        out = brain_mcp.complete_task("другой шаг", root=self.root)
        self.assertIn("✅", out)
        active = (self.root / "agents" / "tasks" / "active_task.md").read_text(encoding="utf-8")
        self.assertIn("- [x] Другой шаг", active)
        self.assertIn("- [ ] Шаг про celery timeout", active)  # не тронут

    def test_idempotent_when_all_done(self):
        brain_mcp.complete_task("celery", root=self.root)
        out = brain_mcp.complete_task("celery", root=self.root)
        self.assertIn("ℹ️", out)

    def test_missing_file(self):
        empty = Path(tempfile.mkdtemp(prefix="brain_mcp_empty_"))
        try:
            out = brain_mcp.complete_task(root=empty)
            self.assertIn("❌", out)
        finally:
            shutil.rmtree(empty, ignore_errors=True)


class TestGetStatus(unittest.TestCase):
    def test_returns_plain_text_without_ansi(self):
        out = brain_mcp.get_status()
        self.assertTrue(out)
        self.assertNotIn("\x1b[", out)
        self.assertIn("Проект", out)


class TestListLinks(unittest.TestCase):
    """PLAN-007: list_links — вики-связи [[...]] без дублирования парсинга."""

    def setUp(self):
        self.root = make_project()
        (self.root / "agents" / "plans").mkdir(parents=True, exist_ok=True)
        (self.root / "agents" / "plans" / "plan_999_links.md").write_text(
            "# План\nСм. [[BUG-001]] и [[MISSING-999]] для контекста.\n",
            encoding="utf-8",
        )
        (self.root / "agents" / "bugs_and_fixes" / "BUG_001.md").write_text(
            (self.root / "agents" / "bugs_and_fixes" / "BUG_001.md").read_text(encoding="utf-8")
            + "См. [[plan_999_links|план]]\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_empty_query_summary_counts_broken(self):
        out = brain_mcp.list_links(root=self.root)
        self.assertIn("🔗 Связи памяти:", out)
        self.assertIn("разрешённых", out)
        self.assertIn("1 битых", out)  # [[MISSING-999]]
        self.assertIn("MISSING-999", out)  # битая связь перечислена

    def test_query_shows_outgoing_and_backlinks(self):
        out = brain_mcp.list_links("BUG-001", root=self.root)
        self.assertIn("🔗 Связи для", out)
        self.assertIn("➡️ Исходящие", out)
        self.assertIn("⬅️ Обратные ссылки", out)
        self.assertIn("plan_999_links.md", out)  # файл с обратной ссылкой на BUG-001

    def test_unknown_query_marks_not_found(self):
        out = brain_mcp.list_links("NOPE-4242", root=self.root)
        self.assertIn("❓ Запись не найдена: 'NOPE-4242'", out)

    def test_broken_target_hint(self):
        """Запись не найдена, но есть битые связи с такой целью — подсказка."""
        out = brain_mcp.list_links("MISSING-999", root=self.root)
        self.assertIn("❓ Запись не найдена", out)
        self.assertIn("Но есть битые связи с такой целью", out)

    def test_accepts_root_override(self):
        import inspect
        self.assertIn("root", inspect.signature(brain_mcp.list_links).parameters)


class TestListClaims(unittest.TestCase):
    """PLAN-007: list_claims — активные локи claim (мультиагентность)."""

    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_no_locks_reports_free(self):
        out = brain_mcp.list_claims(root=self.root)
        self.assertEqual(out, "Свободно: активных блокировок нет.")

    def test_shows_claim_with_status_marker(self):
        import locks
        ok, msg = locks.claim_task("TASK-999", agent="TestAgent", root=self.root)
        self.assertTrue(ok, msg)
        out = brain_mcp.list_claims(root=self.root)
        self.assertIn("🔒 Активные блокировки (1):", out)
        self.assertIn("TASK-999", out)
        self.assertIn("TestAgent", out)
        self.assertIn("🟢", out)  # PID тестового процесса жив → active

    def test_accepts_root_override(self):
        import inspect
        self.assertIn("root", inspect.signature(brain_mcp.list_claims).parameters)


class TestGetStats(unittest.TestCase):
    """PLAN-007: get_stats — дашборд здоровья памяти (текст / JSON)."""

    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_text_mode_contains_dashboard_and_sections(self):
        out = brain_mcp.get_stats(root=self.root)
        self.assertIn("ДАШБОРД", out)
        self.assertIn("Раздел", out)
        self.assertIn("plans", out)
        self.assertIn("Чек-листы", out)

    def test_json_mode_is_valid_with_expected_keys(self):
        out = brain_mcp.get_stats(as_json=True, root=self.root)
        data = json.loads(out)
        for key in ("sections", "claims", "wiki"):
            self.assertIn(key, data)

    def test_empty_skeleton_failsoft(self):
        empty = Path(tempfile.mkdtemp(prefix="brain_mcp_stats_"))
        try:
            out = brain_mcp.get_stats(root=empty)
            self.assertIn("ДАШБОРД", out)  # пустой проект не падает
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_accepts_root_override(self):
        import inspect
        params = inspect.signature(brain_mcp.get_stats).parameters
        self.assertIn("root", params)
        self.assertIn("as_json", params)


class TestServerWiring(unittest.TestCase):
    """Серверный каркас — только при установленном SDK."""

    @unittest.skipUnless(MCP_SDK_AVAILABLE, "пакет mcp не установлен (optional extra [mcp])")
    def test_build_server_registers_tools(self):
        server = brain_mcp.build_server()
        self.assertIsNotNone(server)

    @unittest.skipIf(MCP_SDK_AVAILABLE, "SDK установлен — сообщение об установке не показывается")
    def test_missing_sdk_gives_clear_error(self):
        with self.assertRaises(SystemExit) as ctx:
            brain_mcp.build_server()
        self.assertIn("mcp", str(ctx.exception))


class TestMcpJson(unittest.TestCase):
    """Конфиг .mcp.json: валидный JSON, brain-сервер, секреты только через ${VAR}."""

    def setUp(self):
        self.cfg = json.loads((PROJECT_ROOT / ".mcp.json").read_text(encoding="utf-8"))

    def test_has_brain_server(self):
        brain = self.cfg["mcpServers"]["brain"]
        self.assertIn("brain_mcp.py", " ".join(brain["args"]))

    def test_expected_presets_present(self):
        expected = {"brain", "filesystem", "github", "postgres", "context7", "playwright", "sentry"}
        self.assertEqual(set(self.cfg["mcpServers"]), expected)

    def test_no_inline_secrets(self):
        """Значения секретов не хранятся — только ссылки на переменные окружения."""
        for name, server in self.cfg["mcpServers"].items():
            for key, value in (server.get("env") or {}).items():
                with self.subTest(server=name, var=key):
                    self.assertTrue(
                        value == "" or value.startswith("${"),
                        f"{name}.{key}: значение должно быть '${{VAR}}', а не секрет",
                    )

    def test_all_stdio_with_command(self):
        for name, server in self.cfg["mcpServers"].items():
            with self.subTest(server=name):
                self.assertEqual(server.get("type", "stdio"), "stdio")
                self.assertTrue(server.get("command"))
                self.assertIsInstance(server.get("args"), list)


class TestPyproject(unittest.TestCase):
    def test_mcp_is_optional_extra_not_core_dependency(self):
        text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('[project.optional-dependencies]', text)
        self.assertIn('mcp = ["mcp>=1.2"]', text)
        # пакет mcp не должен попадать в основные dependencies (stdlib-only принцип)
        core_section = text.split("[project.optional-dependencies]")[0]
        self.assertIn("dependencies = []", core_section, "Основные зависимости должны быть пустыми")
        self.assertNotIn("mcp>=", core_section)


if __name__ == "__main__":
    unittest.main()
