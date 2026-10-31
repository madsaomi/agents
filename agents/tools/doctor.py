#!/usr/bin/env python3
"""
Second Brain Doctor (PLAN-008): диагностика окружения и инфраструктуры.
Отвечает на вопрос «будут ли инструменты шаблона работать на этой машине/в этом
проекте»: Python >= 3.9, SQLite FTS5, git, свежесть FTS-индекса, бэкенд буфера
обмена, optional extra [mcp], права записи в agents/.

Разделение ответственности: `brain check` валидирует память и структуру (секции
1–11), `brain stats` — данные памяти, `brain doctor` — окружение.
Exit code: 1 если есть [FAIL], иначе 0 ([WARN] exit code не валят).

Использование:
    python agents/tools/doctor.py [--json] [--root PATH]
    python brain.py doctor [--json]      # то же самое через диспетчер

Только stdlib. collect_doctor() принимает root — тестируемо.
"""

import argparse
import importlib.util
import json
import platform
import shutil
import sqlite3
import subprocess
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
DEFAULT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from search import MEMORY_SECTIONS as SEARCH_SECTIONS, INDEX_FILE as SEARCH_INDEX_FILE  # noqa: E402

# Цвета ANSI (как в check_integrity.py)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

MARKS = {"ok": (GREEN, "[OK]"), "warn": (YELLOW, "[WARN]"), "fail": (RED, "[FAIL]")}


def _memory_newest_mtime(root: Path) -> float:
    """Свежайший mtime среди индексируемых .md памяти (то же множество, что у search)."""
    newest = 0.0
    agents = root / "agents"
    for section in SEARCH_SECTIONS:
        d = agents / section
        if not d.is_dir():
            continue
        for md in d.rglob("*.md"):
            if md.name.lower() == "readme.md":  # README не индексируется
                continue
            try:
                newest = max(newest, md.stat().st_mtime)
            except OSError:
                continue
    return newest


def _check_python() -> dict:
    ver = platform.python_version()
    ok = sys.version_info >= (3, 9)
    return {
        "name": "python",
        "title": "Python >= 3.9",
        "status": "ok" if ok else "fail",
        "details": f"Python {ver}" + ("" if ok else " — инструменты шаблона требуют 3.9+"),
        "hint": None if ok else "Обнови Python до 3.9+ (pyproject.toml: requires-python >=3.9)",
    }


def _check_fts5() -> dict:
    base = {"name": "fts5", "title": "SQLite FTS5 (полнотекстовый поиск)"}
    try:
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("CREATE VIRTUAL TABLE temp.doctor_fts5 USING fts5(text)")
        finally:
            conn.close()
    except sqlite3.Error as e:
        return {**base, "status": "fail",
                "details": f"FTS5 недоступен: {e}",
                "hint": "brain search не заработает: нужен sqlite, собранный с FTS5 "
                        "(в официальном CPython для Windows/macOS включён)"}
    return {**base, "status": "ok",
            "details": f"SQLite {sqlite3.sqlite_version}, FTS5 доступен",
            "hint": None}


def _check_git(root: Path) -> dict:
    base = {"name": "git", "title": "Git (локи claim, worktree, integrity)"}
    binary = shutil.which("git")
    if not binary:
        return {**base, "status": "warn",
                "details": "git не найден в PATH",
                "hint": "Мультиагентность (claim/release/worktree) ограничена без git"}
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return {**base, "status": "warn", "details": f"git не отвечает: {e}",
                "hint": "Проверь установку git"}
    if proc.returncode != 0:
        return {**base, "status": "warn",
                "details": "Каталог не является git-репозиторием",
                "hint": "git init — для локов claim, секрет-сканера и проверки целостности"}
    ver = ""
    try:
        ver = subprocess.run(["git", "--version"], capture_output=True, text=True,
                             timeout=15).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        ver = "git-репозиторий обнаружен"
    return {**base, "status": "ok", "details": ver, "hint": None}


def _check_index(root: Path) -> dict:
    base = {"name": "index", "title": "Индекс поиска .brain_index.db"}
    db = root / SEARCH_INDEX_FILE.name
    newest = _memory_newest_mtime(root)
    if not db.exists():
        if newest == 0.0:
            return {**base, "status": "warn",
                    "details": "Индекса нет, но и записей памяти пока нет",
                    "hint": 'Индекс создастся при первом поиске: python brain.py search "..."'}
        return {**base, "status": "warn", "details": "Индекса поиска нет",
                "hint": "python brain.py search --reindex"}
    try:
        db_mtime = db.stat().st_mtime
    except OSError as e:
        return {**base, "status": "warn", "details": f"Индекс нечитаем: {e}",
                "hint": "Удали .brain_index.db и запусти python brain.py search --reindex"}
    if newest and db_mtime < newest:
        return {**base, "status": "warn",
                "details": f"Индекс устарел: память менялась после индексации "
                           f"({datetime.fromtimestamp(db_mtime):%Y-%m-%d %H:%M})",
                "hint": "python brain.py search --reindex"}
    return {**base, "status": "ok",
            "details": f"Свежий (обновлён {datetime.fromtimestamp(db_mtime):%Y-%m-%d %H:%M})",
            "hint": None}


def _check_clipboard() -> dict:
    base = {"name": "clipboard", "title": "Буфер обмена (brain dump)"}
    if sys.platform == "win32":
        backend, backend_name = shutil.which("clip"), "clip.exe"
    elif sys.platform == "darwin":
        backend, backend_name = shutil.which("pbcopy"), "pbcopy"
    else:
        backend, backend_name = shutil.which("xclip"), "xclip"
    if backend:
        return {**base, "status": "ok", "details": f"Бэкенд: {backend_name}", "hint": None}
    return {**base, "status": "warn", "details": f"Бэкенд {backend_name} не найден",
            "hint": "brain dump сохранит контекст в файл без копирования в буфер обмена"}


def _check_mcp() -> dict:
    base = {"name": "mcp", "title": "Extra [mcp] (MCP-сервер brain-mcp)"}
    if importlib.util.find_spec("mcp") is None:
        return {**base, "status": "warn", "details": "Пакет mcp не установлен",
                "hint": 'pip install ".[mcp]" → python agents/mcp/brain_mcp.py'}
    ver = ""
    try:
        from importlib.metadata import PackageNotFoundError, version
        ver = version("mcp")
    except PackageNotFoundError:
        ver = ""
    details = f"mcp {ver}" if ver else "mcp установлен (версия не определена)"
    return {**base, "status": "ok", "details": details, "hint": None}


def _check_write_access(root: Path) -> dict:
    base = {"name": "write_access", "title": "Права записи в agents/"}
    probe = root / "agents" / ".doctor_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        return {**base, "status": "fail", "details": f"Запись не удалась: {e}",
                "hint": "Проверь права на каталог agents/ (read-only, антивирус, диск)"}
    return {**base, "status": "ok", "details": "Запись и удаление файла проходят", "hint": None}


def collect_doctor(root=None) -> dict:
    """Собрать отчёт диагностики окружения. root — корень проекта (тестируемость)."""
    target_root = Path(root) if root else DEFAULT_ROOT
    checks = [
        _check_python(),
        _check_fts5(),
        _check_git(target_root),
        _check_index(target_root),
        _check_clipboard(),
        _check_mcp(),
        _check_write_access(target_root),
    ]
    errors = sum(1 for c in checks if c["status"] == "fail")
    warnings = sum(1 for c in checks if c["status"] == "warn")
    return {
        "root": str(target_root),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "checks": checks,
        "summary": {"errors": errors, "warnings": warnings, "checks": len(checks)},
    }


def format_doctor(report: dict) -> str:
    lines = []
    bar = "═" * 58
    lines.append(f"{BOLD}{CYAN}{bar}{RESET}")
    lines.append(f"{BOLD}   🩺 Second Brain Doctor — диагностика окружения{RESET}")
    lines.append(f"{CYAN}{bar}{RESET}")
    lines.append("")
    for c in report["checks"]:
        color, mark = MARKS.get(c["status"], (YELLOW, "[?] "))
        lines.append(f"  {color}{mark}{RESET} {c['title']}")
        if c.get("details"):
            if c["status"] == "ok":
                lines.append(f"       {c['details']}")
            else:
                lines.append(f"       {color}--> {c['details']}{RESET}")
        if c.get("hint") and c["status"] != "ok":
            lines.append(f"       {CYAN}💡 {c['hint']}{RESET}")
    s = report["summary"]
    lines.append("")
    if s["errors"]:
        lines.append(f"{RED}🔴 Итог: {s['errors']} ошибок, {s['warnings']} предупреждений — исправь [FAIL] выше.{RESET}")
    elif s["warnings"]:
        lines.append(f"{YELLOW}🟡 Итог: ошибок нет, {s['warnings']} предупреждений — окружение рабочее.{RESET}")
    else:
        lines.append(f"{GREEN}🟢 Итог: окружение полностью готово ({s['checks']} проверок).{RESET}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="🩺 Диагностика окружения Второго Мозга")
    parser.add_argument("--json", action="store_true", help="Вывести отчёт в JSON")
    parser.add_argument("--root", default=None, help="Корень проекта (по умолчанию — репозиторий шаблона)")
    args = parser.parse_args()
    root = Path(args.root) if args.root else DEFAULT_ROOT
    report = collect_doctor(root=root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_doctor(report))
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
