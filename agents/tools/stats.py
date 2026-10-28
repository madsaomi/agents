#!/usr/bin/env python3
"""
Second Brain Memory Dashboard (PLAN-004, Этап 2).
Одна команда — здоровье всей долговременной памяти: записи по разделам,
открытые пункты чек-листов, битые относительные ссылки, устаревшие записи,
активные локи claim, размер FTS-индекса.

Использование:
    python agents/tools/stats.py [--json] [--root PATH]
    python brain.py stats [--json]        # то же самое через диспетчер

Только stdlib. Все функции принимают root — тестируемо.
"""

import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parent.parent

MEMORY_SECTIONS = ("plans", "tasks", "history", "bugs_and_fixes", "decisions", "walkthroughs")
STALE_DAYS = 90
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+")
SKIP_LINK_PREFIX = ("http://", "https://", "mailto:", "#", "ftp://")


def _iter_memory_files(root: Path):
    """Все .md памяти кроме README; yield (раздел, файл)."""
    agents = root / "agents"
    for section in MEMORY_SECTIONS:
        d = agents / section
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*.md")):
            if f.name.lower() == "readme.md":
                continue
            yield section, f


def _count_checkboxes(md_files):
    """(открытых, закрытых) пунктов чек-листов в списке файлов."""
    open_n = done_n = 0
    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            m = CHECKBOX_RE.match(line)
            if m:
                if m.group(1) == " ":
                    open_n += 1
                else:
                    done_n += 1
    return open_n, done_n


def _broken_links(root: Path, md_files):
    """Относительные markdown-ссылки, ведущие в никуда: [{file, line, target}]."""
    broken = []
    for f in md_files:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            for m in LINK_RE.finditer(line):
                target = m.group(1).strip()
                if not target or target.startswith(SKIP_LINK_PREFIX):
                    continue
                path_part = target.split("#", 1)[0]
                if not path_part:
                    continue
                candidate = (f.parent / path_part)
                if not candidate.exists():
                    try:
                        rel = f.relative_to(root).as_posix()
                    except ValueError:
                        rel = f.as_posix()
                    broken.append({"file": rel, "line": lineno, "target": target})
    return broken


def collect_stats(root: Path = None, stale_days: int = STALE_DAYS) -> dict:
    """Собирает дашборд памяти. Возвращает dict (сериализуемый в JSON)."""
    import locks as task_locks  # та же папка

    base = Path(root) if root else DEFAULT_ROOT
    agents = base / "agents"

    # 1. Записи по разделам
    sections = {}
    all_files = []
    for section in MEMORY_SECTIONS:
        files = [f for s, f in _iter_memory_files(base) if s == section]
        sections[section] = len(files)
        all_files.extend(files)

    # 2. Чек-листы: активная задача + активные планы
    active_task = agents / "tasks" / "active_task.md"
    plan_files = sorted(
        [f for f in (agents / "plans").glob("plan_*.md")] if (agents / "plans").is_dir() else [],
        key=lambda x: x.stat().st_mtime, reverse=True,
    )
    active_plans = []
    for pf in plan_files:
        try:
            txt = pf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "IN_PROGRESS" in txt or "APPROVED" in txt:
            active_plans.append(pf)
    task_open, task_done = _count_checkboxes([active_task] if active_task.is_file() else [])
    plan_open, plan_done = _count_checkboxes(active_plans)

    # 3. Битые относительные ссылки (вся память + базовые доки)
    doc_files = list(all_files)
    for extra in (agents / "STATUS.md", agents / "AGENT_GUIDE.md"):
        if extra.is_file():
            doc_files.append(extra)
    broken = _broken_links(base, doc_files)

    # 4. Устаревшие записи (не изменялись > stale_days)
    import time
    cutoff = time.time() - stale_days * 86400
    stale = []
    for section, f in _iter_memory_files(base):
        try:
            if f.stat().st_mtime < cutoff:
                stale.append({"file": f.relative_to(base).as_posix(), "section": section})
        except OSError:
            pass

    # 5. Локи claim
    try:
        claims = task_locks.list_claims(root=base)
    except Exception:
        claims = []

    # 6. FTS-индекс (fail-soft)
    index_info = {"exists": False, "documents": None, "bytes": None}
    db = base / ".brain_index.db"
    if db.is_file():
        index_info["exists"] = True
        index_info["bytes"] = db.stat().st_size
        try:
            import sqlite3
            conn = sqlite3.connect(str(db))
            try:
                index_info["documents"] = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            finally:
                conn.close()
        except Exception:
            pass

    # 7. Заголовок активной задачи
    task_title = None
    task_status = None
    if active_task.is_file():
        try:
            first = active_task.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            task_title = first.lstrip("# ").replace("Активная задача:", "", 1).lstrip("📋 ").strip()
        except (OSError, IndexError):
            pass
        try:
            for line in active_task.read_text(encoding="utf-8", errors="replace").splitlines()[:8]:
                if "Статус:" in line:
                    task_status = line.split("Статус:", 1)[1].strip().lstrip("*").strip()
                    break
        except OSError:
            pass

    return {
        "root": str(base),
        "sections": sections,
        "total_records": sum(sections.values()),
        "active_task": {"title": task_title, "status": task_status},
        "checklists": {
            "task_open": task_open, "task_done": task_done,
            "plans_open": plan_open, "plans_done": plan_done,
            "active_plans": [p.name for p in active_plans],
        },
        "broken_links": broken,
        "stale_days": stale_days,
        "stale_files": stale,
        "claims": [{"task": c.get("task"), "agent": c.get("agent"), "status": c.get("status")}
                   for c in claims],
        "index": index_info,
    }


def format_stats(stats: dict) -> str:
    lines = ["📊 ДАШБОРД ПАМЯТИ ВТОРОГО МОЗГА", ""]

    # Разделы
    lines.append(f"{'Раздел':<20} {'Записей':>8}")
    lines.append("-" * 30)
    for name, count in stats["sections"].items():
        lines.append(f"{name:<20} {count:>8}")
    lines.append(f"{'ИТОГО':<20} {stats['total_records']:>8}")

    # Задача
    at = stats["active_task"]
    if at["title"]:
        lines.append("")
        lines.append(f"🎯 {at['title']}")
        if at["status"]:
            lines.append(f"   Статус: {at['status']}")

    # Чек-листы
    cl = stats["checklists"]
    lines.append("")
    lines.append(f"☑️  Чек-листы: задача {cl['task_open']} открытых / {cl['task_done']} выполнено, "
                 f"планы {cl['plans_open']} / {cl['plans_done']}")
    if cl["active_plans"]:
        lines.append(f"   Активные планы: {', '.join(cl['active_plans'])}")

    # Проблемы
    lines.append("")
    if stats["broken_links"]:
        lines.append(f"🔗 Битые ссылки: {len(stats['broken_links'])}")
        for b in stats["broken_links"][:5]:
            lines.append(f"   {b['file']}:{b['line']} → {b['target']}")
    else:
        lines.append("🔗 Битые ссылки: 0")

    if stats["stale_files"]:
        lines.append(f"🕰 Устаревшие записи (>{stats['stale_days']} дней): {len(stats['stale_files'])}")
        for s in stats["stale_files"][:5]:
            lines.append(f"   {s['file']}")
    else:
        lines.append(f"🕰 Устаревшие записи (>{stats['stale_days']} дней): 0")

    # Локи
    claims = stats["claims"]
    lines.append("")
    if claims:
        lines.append(f"🔒 Локи claim: {len(claims)} активных")
        for c in claims:
            mark = {"active": "🟢", "stale": "💀", "unknown": "❓"}.get(c["status"], "❓")
            lines.append(f"   {mark} {c['task']} — {c['agent']}")
    else:
        lines.append("🔒 Локи claim: свободно")

    # Индекс
    idx = stats["index"]
    lines.append("")
    if idx["exists"]:
        docs = idx["documents"] if idx["documents"] is not None else "?"
        size = f"{idx['bytes'] / 1024:.0f} КБ" if idx["bytes"] else "?"
        lines.append(f"🔍 Поисковый индекс: {docs} документов, {size} (brain.py search)")
    else:
        lines.append("🔍 Поисковый индекс: не создан (создастся при первом search)")

    return "\n".join(lines)


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="📊 Дашборд здоровья памяти")
    parser.add_argument("--json", action="store_true", help="Вывод JSON для машинного чтения")
    parser.add_argument("--root", default=None, help="Корень проекта")
    parser.add_argument("--stale-days", type=int, default=STALE_DAYS,
                        help=f"Порог устаревания записей в днях (по умолчанию {STALE_DAYS})")
    args = parser.parse_args(argv)

    stats = collect_stats(root=Path(args.root) if args.root else None,
                          stale_days=args.stale_days)
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print(format_stats(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
