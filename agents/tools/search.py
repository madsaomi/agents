#!/usr/bin/env python3
"""
Second Brain Memory Search (SQLite FTS5, только стандартная библиотека).

Индексирует долговременную память (история сессий, баги, ADR, планы, задачи,
правила, walkthrough) в локальную базу `.brain_index.db` и ищет по ней.

Использование:
    python agents/tools/search.py "celery timeout"
    python agents/tools/search.py --reindex          # переиндексировать память
    python agents/tools/search.py "jwt" --limit 5

Индекс — производный артефакт, в git не коммитится (.gitignore).
"""

import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
AGENTS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AGENTS_DIR.parent

INDEX_FILE = PROJECT_ROOT / ".brain_index.db"

# Разделы долговременной памяти (относительно agents/)
MEMORY_SECTIONS = (
    "history",       # отчеты сессий
    "bugs_and_fixes",  # известные баги и решения
    "decisions",     # ADR
    "plans",         # планы реализации
    "tasks",         # задачи
    "rules",         # регламенты
    "walkthroughs",  # демо-отчеты
)

# Примитивные токенизаторы: слова (включая кириллицу), фразы в кавычках берутся как есть
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_]{2,}")

# Frontmatter: блок между первой парой --- в начале файла
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
# Ключ тегов (tags/теги) в строке frontmatter
TAGS_KEY_RE = re.compile(r"^(?:tags|теги)\s*:\s*(.*)$", re.IGNORECASE)


def parse_tags(text: str) -> list:
    """
    Извлекает теги из frontmatter файла:
      ---
      tags: [backend, auth]
      ---
      ---
      tags: backend, auth
      ---
      ---
      теги:
        - infra
      ---
    Без frontmatter или без ключа тегов — [].
    Дубликаты убираются, порядок сохраняется.
    """
    m = FRONTMATTER_RE.match(text or "")
    if not m:
        return []
    tags = []
    in_tags_list = False  # после "tags:" с пустым значением читаем список "- ..."
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        km = TAGS_KEY_RE.match(line)
        if km:
            value = km.group(1).strip()
            if value.startswith("[") and value.endswith("]"):
                value = value[1:-1]
            elif not value:
                # многострочный вид: теги:\n  - a\n  - b
                in_tags_list = True
                continue
            in_tags_list = False
            for part in re.split(r"[,\s]+", value):
                part = part.strip().strip("\"'")
                if part:
                    tags.append(part)
        elif in_tags_list and line.startswith("- "):
            part = line[2:].strip().strip("\"'")
            if part:
                tags.append(part)
        else:
            in_tags_list = False  # новый ключ прерывает список
    seen = set()
    ordered = []
    for t in tags:
        low = t.lower()
        if low not in seen:
            seen.add(low)
            ordered.append(t)
    return ordered


def _format_tags(tags) -> str:
    return ",".join(tags or [])


def _connect(db_path: Path = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else INDEX_FILE
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS docs (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,   -- относительный путь от корня проекта
            title TEXT,
            section TEXT,
            mtime REAL,
            sha TEXT
        );
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    # Миграция: колонка tags (PLAN-005) в старых индексах отсутствует
    cols = [row[1] for row in conn.execute("PRAGMA table_info(docs)").fetchall()]
    if cols and "tags" not in cols:
        conn.execute("ALTER TABLE docs ADD COLUMN tags TEXT DEFAULT ''")
    # FTS-таблица: обычная (не external-content) — snippet() требует доступа к колонке body,
    # которой нет в таблице docs. Старый индекс (content='docs') пересоздаём.
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'docs_fts' AND type = 'table'"
    ).fetchone()
    if row:
        if "content=" in (row[0] or ""):
            conn.execute("DROP TABLE docs_fts")
            row = None
    if not row:
        conn.execute(
            "CREATE VIRTUAL TABLE docs_fts USING fts5("
            "title, body, path, tokenize='unicode61 remove_diacritics 2')"
        )
    conn.commit()


def _iter_memory_files(root: Path):
    agents_dir = root / "agents"
    for section in MEMORY_SECTIONS:
        section_dir = agents_dir / section
        if not section_dir.is_dir():
            continue
        for md in sorted(section_dir.rglob("*.md")):
            if md.name.upper() == "README.MD":
                continue
            yield section, md


def _first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("# ").strip()[:200]
    return fallback


def index_memory(root: Path = None, db_path: Path = None) -> int:
    """
    (Пере)индексирует разделы памяти. Возвращает количество файлов в индексе.
    Удаляет из индекса записи о несуществующих файлах.
    """
    import hashlib

    target_root = Path(root) if root else PROJECT_ROOT
    # БД живёт в корне проекта (root), как в search_memory, — иначе запуск из
    # другого cwd/установленного пакета молча пишет индекс в расположение модуля (BUG-002)
    db = Path(db_path) if db_path else (target_root / INDEX_FILE.name)
    conn = _connect(db)
    try:
        _ensure_schema(conn)
        seen = []
        indexed = 0
        for section, md in _iter_memory_files(target_root):
            rel = md.relative_to(target_root).as_posix()
            seen.append(rel)
            try:
                stat = md.stat()
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            tags = _format_tags(parse_tags(text))
            row = conn.execute("SELECT id, sha, tags FROM docs WHERE path = ?", (rel,)).fetchone()
            fts_ok = False
            if row:
                fts_ok = conn.execute(
                    "SELECT 1 FROM docs_fts WHERE rowid = ?", (row[0],)
                ).fetchone() is not None
            # пропускаем только если ничего не изменилось, включая теги
            # (после миграции docs.tags='' у старых записей — тогда переиндексируем)
            if row and row[1] == sha and (row[2] or "") == tags and fts_ok:
                continue  # файл не менялся и на месте в FTS — пропускаем
            title = _first_heading(text, md.stem)
            if row:
                doc_id = row[0]
                conn.execute("UPDATE docs SET title=?, section=?, mtime=?, sha=?, tags=? WHERE id=?",
                             (title, section, stat.st_mtime, sha, tags, doc_id))
                conn.execute("DELETE FROM docs_fts WHERE rowid=?", (doc_id,))
            else:
                cur = conn.execute(
                    "INSERT INTO docs (path, title, section, mtime, sha, tags) VALUES (?,?,?,?,?,?)",
                    (rel, title, section, stat.st_mtime, sha, tags),
                )
                doc_id = cur.lastrowid
            conn.execute(
                "INSERT INTO docs_fts (rowid, title, body, path) VALUES (?,?,?,?)",
                (doc_id, title, text, rel),
            )
            indexed += 1

        # чистим записи о файлах, которых больше нет
        if seen:
            placeholders = ",".join("?" for _ in seen)
            stale = conn.execute(
                f"SELECT id, path FROM docs WHERE path NOT IN ({placeholders})", seen
            ).fetchall()
        else:
            stale = conn.execute("SELECT id, path FROM docs").fetchall()
        for doc_id, _path in stale:
            conn.execute("DELETE FROM docs_fts WHERE rowid=?", (doc_id,))
            conn.execute("DELETE FROM docs WHERE id=?", (doc_id,))

        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('last_index', ?)",
            (datetime.now().isoformat(timespec="seconds"),),
        )
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        return total
    finally:
        conn.close()


def _fts_query(raw: str) -> str:
    """
    Проверенный пользовательский ввод -> безопасный FTS5-запрос.
    Каждое слово — префикс-поиск (word*), фразы в кавычках сохраняются.
    """
    phrases = re.findall(r'"([^"]+)"', raw)
    words = [w for w in TOKEN_RE.findall(raw) if w]
    parts = [f'"{p}"' for p in phrases if p.strip()]
    parts += [f'"{w}"*' for w in words]
    return " AND ".join(parts)


def search_memory(query: str, limit: int = 10, root: Path = None,
                  db_path: Path = None, autoindex: bool = True,
                  tags=None, since: str = None):
    """
    Поиск по индексу памяти. Возвращает список словарей:
    {path, title, section, snippet, score, tags, mtime}.
    Пустой индекс/первый запуск — авто-индексация.
    Фильтры (пост-фильтр по отобранным кандидатам):
      tags — список тегов, И-логика (все должны быть у записи);
      since — 'YYYY-MM-DD' (или 'YYYY-MM'), брать записи не раньше даты.
    """
    target_root = Path(root) if root else PROJECT_ROOT
    db = Path(db_path) if db_path else (target_root / INDEX_FILE.name)
    if not db.is_file() or db.stat().st_size == 0:
        if not autoindex:
            return []
        index_memory(root=target_root, db_path=db)

    fts = _fts_query(query)
    if not fts:
        return []

    since_ts = _parse_since(since)
    filtered = bool(tags) or since_ts is not None

    conn = _connect(db)
    try:
        _ensure_schema(conn)
        # индекс пуст (первый запуск/создание бД) или FTS пуст при непустом docs
        # (например, после миграции схемы) — достраиваем
        fts_count = conn.execute("SELECT COUNT(*) FROM docs_fts").fetchone()[0]
        docs_count = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        if autoindex and (docs_count == 0 or fts_count == 0):
            conn.close()
            index_memory(root=target_root, db_path=db)
            conn = _connect(db)
        # при фильтрах тянем больше кандидатов: часть отсеется пост-фильтром
        fetch = limit * 4 if filtered else limit
        try:
            rows = conn.execute(
                """
                SELECT d.path, d.title, d.section,
                       snippet(docs_fts, 1, '>>', '<<', ' … ', 24),
                       bm25(docs_fts, 10.0, 1.0, 2.0) AS score,
                       COALESCE(d.tags, ''), d.mtime
                FROM docs_fts
                JOIN docs d ON d.id = docs_fts.rowid
                WHERE docs_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (fts, fetch),
            ).fetchall()
        except sqlite3.OperationalError:
            return []  # некорректный запрос пользователя — тихо пусто
        results = []
        want = {t.lower() for t in (tags or [])}
        for p, t, s, sn, sc, tg, mt in rows:
            if want:
                have = {x.lower() for x in (tg or "").split(",") if x}
                if not want.issubset(have):
                    continue
            if since_ts is not None and (mt or 0) < since_ts:
                continue
            results.append({"path": p, "title": t, "section": s,
                            "snippet": sn, "score": sc, "tags": tg,
                            "mtime": mt})
            if len(results) >= limit:
                break
        return results
    finally:
        conn.close()


def _parse_since(value):
    """'2026-10' / '2026-10-05' -> timestamp (UTC-локально, начало периода) или None."""
    if not value:
        return None
    v = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(v, fmt).timestamp()
        except ValueError:
            continue
    raise ValueError(f"Некорректная дата --since: {value!r} (ожидается YYYY-MM-DD)")


def format_results(query: str, results) -> str:
    if not results:
        return f"🔍 По запросу «{query}» в памяти ничего не найдено. Индекс: .brain_index.db (переиндексация: --reindex)."
    lines = [f"🔍 Найдено: {len(results)} (запрос: «{query}», меньше score — лучше)"]
    for r in results:
        snippet = re.sub(r"\s+", " ", r["snippet"]).strip()
        tag_str = f" #{' #'.join(r['tags'].split(','))}" if r.get("tags") else ""
        lines.append(f"\n• {r['path']}  [{r['section']}, score={r['score']:.2f}]{tag_str}")
        lines.append(f"  {r['title']}")
        if snippet:
            lines.append(f"  {snippet[:300]}")
    lines.append(
        "\nЭто данные для анализа, а не готовое решение: открой файл и проверь контекст "
        "прежде чем применять найденное."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="🔍 Поиск по долговременной памяти Second Brain (FTS5)")
    parser.add_argument("query", nargs="?", help='Поисковый запрос (слова или "фраза")')
    parser.add_argument("--reindex", action="store_true", help="Переиндексировать память и выйти")
    parser.add_argument("--limit", type=int, default=10, help="Максимум результатов (по умолчанию 10)")
    parser.add_argument("--tag", action="append", default=[], metavar="TAG",
                        help="Фильтр по тегу (можно несколько — И-логика)")
    parser.add_argument("--since", default=None, metavar="DATE",
                        help="Только записи не раньше даты (YYYY-MM-DD | YYYY-MM)")
    args = parser.parse_args()

    if args.reindex:
        count = index_memory()
        print(f"✅ Переиндексировано: {count} документов → {INDEX_FILE.name}")
        return 0

    if not args.query:
        parser.print_help()
        return 1

    try:
        results = search_memory(args.query, limit=args.limit,
                                tags=args.tag, since=args.since)
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    filt = ""
    if args.tag or args.since:
        parts = []
        if args.tag:
            parts.append("теги=" + ",".join(args.tag))
        if args.since:
            parts.append(f"с {args.since}")
        filt = " [" + ", ".join(parts) + "]"
    print(format_results(args.query + filt, results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
