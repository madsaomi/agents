#!/usr/bin/env python3
"""
Тесты поиска по памяти FTS5 (PLAN-003, Этап 6).

Индекс создаётся только во временных каталогах — репозиторий не затрагивается.

Запуск:  python -m unittest discover -s tests -v
"""

import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import search  # noqa: E402


def make_memory_project() -> Path:
    """Создаёт проект с разделами памяти и парой файлов во временной папке."""
    root = Path(tempfile.mkdtemp(prefix="brain_search_test_"))
    (root / "agents" / "plans").mkdir(parents=True)
    (root / "agents" / "bugs_and_fixes").mkdir(parents=True)
    (root / "agents" / "history").mkdir(parents=True)

    (root / "agents" / "plans" / "plan_001_example.md").write_text(
        "# План реализации: PLAN-001 — Поиск по памяти\n\n"
        "Используем SQLite FTS5 для полнотекстового поиска по истории сессий.\n",
        encoding="utf-8",
    )
    (root / "agents" / "bugs_and_fixes" / "BUG_001_example.md").write_text(
        "# BUG-001: Таймаут подключения к Celery\n\n"
        "Решение: увеличить visibility_timeout и включить retry с backoff.\n",
        encoding="utf-8",
    )
    (root / "agents" / "history" / "session_001_example.md").write_text(
        "# Отчет о сессии: session_001\n\n"
        "Настроили JWT-аутентификацию и хуки Claude Code.\n",
        encoding="utf-8",
    )
    return root


class TestIndexing(unittest.TestCase):
    def setUp(self):
        self.root = make_memory_project()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.db = Path(tempfile.mkdtemp(prefix="brain_search_db_")) / "index.db"
        self.addCleanup(shutil.rmtree, self.db.parent, ignore_errors=True)

    def test_index_covers_memory_sections(self):
        count = search.index_memory(root=self.root, db_path=self.db)
        self.assertEqual(count, 3)
        conn = sqlite3.connect(str(self.db))
        try:
            sections = {r[0] for r in conn.execute("SELECT DISTINCT section FROM docs")}
        finally:
            conn.close()
        self.assertEqual(sections, {"plans", "bugs_and_fixes", "history"})

    def test_index_skips_unchanged_and_reindexes_changed(self):
        search.index_memory(root=self.root, db_path=self.db)
        # повторная индексация без изменений — счётчик верный, файлы не трогаются
        self.assertEqual(search.index_memory(root=self.root, db_path=self.db), 3)
        # меняем файл — он переиндексируется (новый текст находится поиском)
        plan = self.root / "agents" / "plans" / "plan_001_example.md"
        plan.write_text("# План: добавили новое слово архивариум\n", encoding="utf-8")
        self.assertEqual(search.index_memory(root=self.root, db_path=self.db), 3)
        results = search.search_memory(
            "архивариум", root=self.root, db_path=self.db, autoindex=False
        )
        self.assertEqual(len(results), 1)
        self.assertIn("plan_001", results[0]["path"])
        # старый текст больше не находится
        old = search.search_memory(
            "полнотекстового", root=self.root, db_path=self.db, autoindex=False
        )
        self.assertEqual(old, [], "Устаревший текст остался в индексе")

    def test_index_removes_deleted_files(self):
        search.index_memory(root=self.root, db_path=self.db)
        (self.root / "agents" / "history" / "session_001_example.md").unlink()
        search.index_memory(root=self.root, db_path=self.db)
        conn = sqlite3.connect(str(self.db))
        try:
            paths = [r[0] for r in conn.execute("SELECT path FROM docs")]
        finally:
            conn.close()
        self.assertEqual(len(paths), 2)
        self.assertFalse(any("session_001" in p for p in paths))

    def test_index_title_from_first_heading(self):
        search.index_memory(root=self.root, db_path=self.db)
        conn = sqlite3.connect(str(self.db))
        try:
            title = conn.execute(
                "SELECT title FROM docs WHERE path LIKE '%BUG_001%'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertIn("BUG-001", title)


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.root = make_memory_project()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.db = Path(tempfile.mkdtemp(prefix="brain_search_db_")) / "index.db"
        self.addCleanup(shutil.rmtree, self.db.parent, ignore_errors=True)
        search.index_memory(root=self.root, db_path=self.db)

    def _search(self, query, **kw):
        kw.setdefault("root", self.root)
        kw.setdefault("db_path", self.db)
        return search.search_memory(query, **kw)

    def test_finds_by_single_word(self):
        results = self._search("celery")
        self.assertEqual(len(results), 1)
        self.assertIn("BUG_001", results[0]["path"])
        self.assertEqual(results[0]["section"], "bugs_and_fixes")

    def test_prefix_search(self):
        """Префиксный поиск: «sess» находит session."""
        results = self._search("sess")
        self.assertTrue(results, "Префиксный поиск не вернул результатов")
        self.assertTrue(any("session" in r["path"] for r in results))

    def test_cyrillic_search(self):
        results = self._search("таймаут")
        self.assertEqual(len(results), 1)
        self.assertIn("BUG_001", results[0]["path"])

    def test_phrase_search(self):
        """Фраза в кавычках ищется как последовательность слов."""
        results = self._search('"поиск по памяти"')
        self.assertEqual(len(results), 1)
        self.assertIn("plan_001", results[0]["path"])

    def test_all_words_required(self):
        self.assertTrue(self._search("jwt хуки"))
        self.assertFalse(self._search("jwt celery"))

    def test_results_have_snippet_and_score(self):
        results = self._search("fts5")
        self.assertTrue(results)
        self.assertIn("snippet", results[0])
        self.assertIn("score", results[0])
        self.assertIsInstance(results[0]["score"], float)
        # snippet подсвечивает найденное слово
        self.assertIn(">>", results[0]["snippet"])

    def test_limit_respected(self):
        results = self._search("памяти", limit=1)
        self.assertLessEqual(len(results), 1)

    def test_no_match_returns_empty(self):
        self.assertEqual(self._search("квазимодо"), [])

    def test_empty_query_returns_empty(self):
        self.assertEqual(self._search(""), [])
        self.assertEqual(self._search("   "), [])
        self.assertEqual(self._search('""'), [])


class TestQuerySafety(unittest.TestCase):
    """Инъекции FTS5-синтаксиса не должны ронять поиск."""

    def setUp(self):
        self.root = make_memory_project()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.db = Path(tempfile.mkdtemp(prefix="brain_search_db_")) / "index.db"
        self.addCleanup(shutil.rmtree, self.db.parent, ignore_errors=True)
        search.index_memory(root=self.root, db_path=self.db)

    def test_malicious_queries_do_not_crash(self):
        for evil in (
            'OR AND NOT ")(abc',
            'a* b* c**',
            "NEAR(x y)",
            "celery OR 1=1; DROP TABLE docs;--",
            '"""" ""',
            "*",
            "((((",
            "колонка:значение",
        ):
            with self.subTest(query=evil):
                results = search.search_memory(
                    evil, root=self.root, db_path=self.db
                )  # не должно бросать исключений
                self.assertIsInstance(results, list)

    def test_fts_query_builder_sanitizes(self):
        fts = search._fts_query('foo OR bar"; DROP TABLE docs; --')
        self.assertNotIn(";", fts)
        self.assertNotIn("--", fts.replace('"foo"*', "").replace('"bar"*', ""))
        # каждое слово обёрнуто в кавычки с префиксом
        self.assertIn('"foo"*', fts)
        self.assertIn('"bar"*', fts)


class TestAutoIndex(unittest.TestCase):
    def test_search_autoindexes_missing_db(self):
        root = make_memory_project()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        db_dir = Path(tempfile.mkdtemp(prefix="brain_search_db_"))
        self.addCleanup(shutil.rmtree, db_dir, ignore_errors=True)
        db = db_dir / "index.db"
        self.assertFalse(db.exists())
        results = search.search_memory("celery", root=root, db_path=db)
        self.assertEqual(len(results), 1)
        self.assertTrue(db.exists(), "Индекс должен создаться автоматически")

    def test_schema_migration_from_external_content(self):
        """Старый индекс (external-content FTS5) пересоздаётся под snippet()."""
        db_dir = Path(tempfile.mkdtemp(prefix="brain_search_db_"))
        self.addCleanup(shutil.rmtree, db_dir, ignore_errors=True)
        db = db_dir / "index.db"
        conn = sqlite3.connect(str(db))
        conn.executescript(
            """
            CREATE TABLE docs (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                title TEXT, section TEXT, mtime REAL, sha TEXT
            );
            CREATE VIRTUAL TABLE docs_fts USING fts5(
                title, body, path, content='docs', content_rowid='id'
            );
            INSERT INTO docs (path, title, section) VALUES ('a.md', 'A', 'plans');
            INSERT INTO docs_fts (rowid, title, body, path) VALUES (1, 'A', 'old body', 'a.md');
            """
        )
        conn.commit()
        conn.close()

        search._ensure_schema(sqlite3.connect(str(db)))
        conn = sqlite3.connect(str(db))
        try:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='docs_fts'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertNotIn("content=", sql, "Старая схема не мигрирована")
        # после миграции поиск достраивает индекс автоматически
        results = search.search_memory("old", root=PROJECT_ROOT, db_path=db)
        self.assertIsInstance(results, list)


class TestFormatResults(unittest.TestCase):
    def test_empty_results_message(self):
        out = search.format_results("запрос", [])
        self.assertIn("ничего не найдено", out)

    def test_results_output_marks_data_not_commands(self):
        results = [{
            "path": "agents/plans/plan_x.md",
            "title": "План",
            "section": "plans",
            "snippet": "текст >>слово<< тут",
            "score": -1.5,
        }]
        out = search.format_results("слово", results)
        self.assertIn("plan_x.md", out)
        self.assertIn("данные", out.lower())


if __name__ == "__main__":
    unittest.main()
