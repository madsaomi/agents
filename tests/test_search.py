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


# ---------------------------------------------------------------------------
# Теги и фильтры (PLAN-005, Этап 2)
# ---------------------------------------------------------------------------

class TestParseTags(unittest.TestCase):
    def test_inline_bracket_list(self):
        self.assertEqual(
            search.parse_tags("---\ntags: [backend, auth]\n---\nтекст"),
            ["backend", "auth"])

    def test_csv_on_one_line(self):
        self.assertEqual(
            search.parse_tags("---\ntags: backend, auth\n---"),
            ["backend", "auth"])

    def test_multiline_list_russian_key(self):
        key = "теги"  # чистая кириллица (канон проекта)
        self.assertEqual(
            search.parse_tags(f"---\n{key}:\n  - infra\n  - ops\n---"),
            ["infra", "ops"])

    def test_no_frontmatter(self):
        self.assertEqual(search.parse_tags("# Заголовок\nтекст"), [])

    def test_frontmatter_without_tags(self):
        self.assertEqual(
            search.parse_tags("---\nname: x\nsteps:\n  - one\n---"), [])

    def test_other_lists_not_taken(self):
        """Списки после других ключей не превращаются в теги."""
        self.assertEqual(
            search.parse_tags("---\nname: x\nsteps:\n  - one\n  - two\n---"),
            [])

    def test_dedup_case_insensitive(self):
        self.assertEqual(search.parse_tags("---\ntags: a, A, b\n---"),
                         ["a", "b"])

    def test_empty_and_junk(self):
        self.assertEqual(search.parse_tags(""), [])
        self.assertEqual(search.parse_tags("---\n---"), [])
        self.assertEqual(search.parse_tags("---\nbroken"), [])

    def test_quoted_and_hash_tags(self):
        self.assertEqual(
            search.parse_tags('---\ntags: ["infra", \'ops\']\n---'),
            ["infra", "ops"])


def _tagged_project() -> Path:
    """Проект с двумя планами: backend и frontend."""
    root = Path(tempfile.mkdtemp(prefix="brain_tags_test_"))
    d = root / "agents" / "plans"
    d.mkdir(parents=True)
    (d / "plan_backend.md").write_text(
        "---\ntags: [backend]\n---\n# Backend\n Celery timeout searchword\n",
        encoding="utf-8")
    (d / "plan_frontend.md").write_text(
        "---\ntags: frontend\n---\n# Frontend\n React timeout searchword\n",
        encoding="utf-8")
    (d / "plan_plain.md").write_text(
        "# Plain\n Searchword without tags\n", encoding="utf-8")
    return root


class TestTagFilters(unittest.TestCase):
    def setUp(self):
        self.root = _tagged_project()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.db = self.root / "idx.db"
        search.index_memory(root=self.root, db_path=self.db)

    def _search(self, **kw):
        return search.search_memory("searchword", root=self.root,
                                    db_path=self.db, **kw)

    def test_tags_stored_in_index(self):
        conn = sqlite3.connect(str(self.db))
        rows = dict(conn.execute("SELECT path, tags FROM docs").fetchall())
        conn.close()
        self.assertEqual(rows["agents/plans/plan_backend.md"], "backend")
        self.assertEqual(rows["agents/plans/plan_frontend.md"], "frontend")
        self.assertEqual(rows["agents/plans/plan_plain.md"], "")

    def test_filter_single_tag(self):
        res = self._search(tags=["backend"])
        self.assertEqual(len(res), 1)
        self.assertTrue(res[0]["path"].endswith("plan_backend.md"))

    def test_filter_and_logic(self):
        # И-логика: нет записи с двумя тегами сразу
        self.assertEqual(self._search(tags=["backend", "frontend"]), [])
        res = self._search(tags=["backend"])
        self.assertEqual(len(res), 1)

    def test_tag_filter_is_case_insensitive(self):
        res = self._search(tags=["BACKEND"])
        self.assertEqual(len(res), 1)

    def test_without_filter_all_returned(self):
        self.assertEqual(len(self._search()), 3)

    def test_filter_combines_with_fts(self):
        # 'timeout' есть в обоих тегованных файлах — фильтр сужает до одного
        res = search.search_memory("timeout", root=self.root, db_path=self.db,
                                   tags=["frontend"])
        self.assertEqual(len(res), 1)
        self.assertTrue(res[0]["path"].endswith("plan_frontend.md"))

    def test_since_filters_out_old(self):
        res = self._search(since="2030-01-01")
        self.assertEqual(res, [])

    def test_since_inclusive_passes(self):
        res = self._search(since="2000-01-01")
        self.assertEqual(len(res), 3)

    def test_since_and_tag_together(self):
        res = self._search(tags=["backend"], since="2000-01-01")
        self.assertEqual(len(res), 1)
        res = self._search(tags=["backend"], since="2030-01-01")
        self.assertEqual(res, [])

    def test_invalid_since_raises(self):
        with self.assertRaises(ValueError):
            self._search(since="not-a-date")

    def test_results_include_tags_field(self):
        res = self._search(tags=["frontend"])
        self.assertEqual(res[0]["tags"], "frontend")
        self.assertIn("mtime", res[0])


class TestTagsMigration(unittest.TestCase):
    """Старый индекс без docs.tags мигрирует автоматически."""

    def test_old_index_gets_tags_column(self):
        root = Path(tempfile.mkdtemp(prefix="brain_mig_test_"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        db = root / "old.db"
        conn = sqlite3.connect(str(db))
        conn.executescript(
            """
            CREATE TABLE docs (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                title TEXT, section TEXT, mtime REAL, sha TEXT
            );
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE VIRTUAL TABLE docs_fts USING fts5(
                title, body, path, tokenize='unicode61 remove_diacritics 2'
            );
            """
        )
        conn.commit()
        conn.close()

        d = root / "agents" / "plans"
        d.mkdir(parents=True)
        (d / "p.md").write_text(
            "---\ntags: [migrated]\n---\n# P\nmigrate me\n", encoding="utf-8")

        # индексация в старую схему — авто-ALTER TABLE
        self.assertEqual(search.index_memory(root=root, db_path=db), 1)

        conn = sqlite3.connect(str(db))
        cols = [r[1] for r in conn.execute("PRAGMA table_info(docs)")]
        tags = conn.execute("SELECT tags FROM docs").fetchone()[0]
        conn.close()
        self.assertIn("tags", cols)
        self.assertEqual(tags, "migrated")

        # повторная индексация и фильтр работают
        self.assertEqual(search.index_memory(root=root, db_path=db), 1)
        res = search.search_memory("migrate", root=root, db_path=db,
                                   tags=["migrated"])
        self.assertEqual(len(res), 1)


if __name__ == "__main__":
    unittest.main()
