#!/usr/bin/env python3
"""
Memory Lint (PLAN-010, секция 12 в check_integrity): дисциплина записей памяти.
Ловит «недокормленные» записи: план без статуса или чек-листа, активная задача
без декомпозиции на шаги, ADR без статуса, баг без разбора «Симптом → Первопричина».

Все находки — warn-уровень: check/CI не падают, но замечания видны.

Использование:
    python agents/tools/memory_lint.py [--root PATH] [--json]
    (из check_integrity — секция 12)

Только stdlib. lint_memory() принимает root — тестируемо.
"""

import argparse
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

CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+", re.MULTILINE)
YELLOW = "\033[93m"
RESET = "\033[0m"


def _read(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _is_service_file(name: str) -> bool:
    """README и эталонные example-файлы не участвуют в ленте."""
    return name.lower() == "readme.md" or "example" in name.lower()


def _finding(name: str, details: str) -> dict:
    return {"name": name, "passed": False, "details": details}


def lint_memory(root=None) -> list:
    """Собрать нарушения дисциплины записей. root — корень проекта (тестируемость)."""
    target_root = Path(root) if root else DEFAULT_ROOT
    agents = target_root / "agents"
    findings = []

    # 1. Планы: строка «Статус» и хотя бы один чекбокс-шаг
    plans_dir = agents / "plans"
    if plans_dir.is_dir():
        for p in sorted(plans_dir.glob("plan_*.md")):
            if _is_service_file(p.name):
                continue
            text = _read(p)
            if text is None:
                findings.append(_finding(f"план {p.name}", "файл не читается"))
                continue
            if "Статус" not in text:
                findings.append(_finding(f"план {p.name}", "нет строки «Статус» (шаблон template_plan.md)"))
            elif not CHECKBOX_RE.search(text):
                findings.append(_finding(f"план {p.name}", "нет ни одного чекбокса-шага — декомпозируй реализацию"))

    # 2. Активная задача: чекбоксы (если это не заглушка «задача не выбрана»)
    active = agents / "tasks" / "active_task.md"
    if active.is_file():
        text = _read(active)
        if text and "не выбрана" not in text.lower() and not CHECKBOX_RE.search(text):
            findings.append(_finding("tasks/active_task.md", "активная задача без чек-листа — декомпозируй шаги"))

    # 3. ADR: строка «Статус»
    decisions_dir = agents / "decisions"
    if decisions_dir.is_dir():
        for p in sorted(decisions_dir.glob("ADR_*.md")):
            if _is_service_file(p.name):
                continue
            text = _read(p)
            if text is not None and "Статус" not in text:
                findings.append(_finding(f"ADR {p.name}", "нет строки «Статус» (принято/отклонено/заменено?)"))

    # 4. Баг-репорты: разбор «Симптом → Первопричина»
    bugs_dir = agents / "bugs_and_fixes"
    if bugs_dir.is_dir():
        for p in sorted(bugs_dir.glob("BUG_*.md")):
            if _is_service_file(p.name):
                continue
            text = _read(p)
            if text is None:
                continue
            missing = [kw for kw in ("Симптом", "Первопричина") if kw not in text]
            if missing:
                findings.append(_finding(f"баг {p.name}", "нет разделов: " + ", ".join(f"«{m}»" for m in missing)))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="🧹 Линт памяти: дисциплина записей Второго Мозга")
    parser.add_argument("--root", default=None, help="Корень проекта (по умолчанию — репозиторий шаблона)")
    parser.add_argument("--json", action="store_true", help="Вывести находки в JSON")
    args = parser.parse_args()
    findings = lint_memory(root=Path(args.root) if args.root else None)
    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
        return 0
    if not findings:
        print("✅ Линт памяти: нарушений нет.")
        return 0
    for f in findings:
        print(f"  {YELLOW}[WARN]{RESET} {f['name']} — {f['details']}")
    print(f"\n{YELLOW}⚠️ Линт памяти: {len(findings)} замечаний (warn — check не падает).{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
