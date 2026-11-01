#!/usr/bin/env python3
"""
Handoff (PLAN-010): эстафета для следующего агента одной командой.

Собирает из памяти всё, что нужно вошедшему агенту (каждая секция fail-soft —
отсутствие файла/раздела не ломает отчёт):
  1. Статус проекта   — фаза и блок «Что делается прямо сейчас» из STATUS.md
  2. Активная задача  — заголовок, статус, незакрытые пункты active_task.md
  3. Активный план    — файл плана из ссылки в задаче, его статус и шаги
  4. Открытые баги    — BUG_*.md без «РЕШЕНО»
  5. Активные локи    — locks.list_claims()
  6. Бэклог           — первый кандидат из «Высокий приоритет»
  7. Прошлая сессия   — «Инструкция для следующего агента» из свежайшей записи

Использование:
    python agents/tools/handoff.py [--root PATH] [--json]
    python brain.py handoff [--copy]     # через диспетчер

Только stdlib. collect_handoff() принимает root — тестируемо (урок BUG-002).
"""

import json
import re
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

OPEN_ITEM_LINE = r"^\s*[-*]\s+\[ \]\s+\S"


def _read(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _section(text: str, header_substring: str):
    """Содержимое секции «##…### …header…» до следующего заголовка (None — нет секции)."""
    if not text:
        return None
    out, capturing = [], False
    for line in text.splitlines():
        if re.match(r"^#{2,6}\s", line):  # h2–h6: секции документов (h1 — заголовок файла)
            if capturing:
                break
            capturing = header_substring.lower() in line.lower()
            continue
        if capturing:
            out.append(line)
    block = "\n".join(out).strip()
    return block or None


def collect_handoff(root=None) -> dict:
    target_root = Path(root) if root else DEFAULT_ROOT
    agents = target_root / "agents"
    report = {"root": str(target_root),
              "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")}

    # 1. STATUS.md: фаза + «что делается прямо сейчас»
    st = _read(agents / "STATUS.md")
    phase = now_block = None
    if st:
        m = re.search(r"\*\*Текущая фаза:\*\*\s*(.+)", st)
        phase = m.group(1).strip() if m else None
        now_block = _section(st, "Что делается прямо сейчас")
    report["status"] = {"phase": phase, "now": now_block}

    # 2. Активная задача
    active_task = None
    plan_info = None
    at = _read(agents / "tasks" / "active_task.md")
    if at and "не выбрана" not in at.lower():
        title = next((l for l in at.splitlines() if l.startswith("# ")), None)
        m = re.search(r"\*\*Статус:\*\*\s*(.+)", at)
        plan_m = re.search(r"\[([^\]]+)\]\(\.\./plans/([^)|\s\]]+)", at)  # любая ссылка на ../plans/
        active_task = {
            "title": title.lstrip("# ").strip() if title else None,
            "status": m.group(1).strip() if m else None,
            "open_items": [l.strip() for l in at.splitlines() if re.match(OPEN_ITEM_LINE, l)],
        }
        # 3. Активный план (по ссылке из задачи)
        if plan_m:
            plan_id, plan_file = plan_m.group(1), plan_m.group(2)
            pt = _read(agents / "plans" / plan_file)
            if pt:
                status_line = next(
                    (l.strip().lstrip("> ").strip() for l in pt.splitlines() if "**Статус:**" in l), None)
                plan_info = {
                    "id": plan_id,
                    "file": plan_file,
                    "status": status_line,
                    "open_steps": [l.strip() for l in pt.splitlines() if re.match(OPEN_ITEM_LINE, l)],
                }
    report["active_task"] = active_task
    report["plan"] = plan_info

    # 4. Открытые баги (без «РЕШЕНО»; example-файлы не считаются)
    open_bugs = []
    bugs_dir = agents / "bugs_and_fixes"
    if bugs_dir.is_dir():
        for f in sorted(bugs_dir.glob("BUG_*.md")):
            if "example" in f.name.lower():
                continue
            bt = _read(f)
            if bt and "РЕШЕНО" not in bt:
                open_bugs.append(f.name)
    report["open_bugs"] = open_bugs

    # 5. Активные локи (ленивый импорт, fail-soft)
    claims, claims_error = [], None
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        import locks as task_locks
        claims = task_locks.list_claims(root=target_root)
    except Exception as e:  # локи — необязательная секция, но ошибку не глотаем молча
        claims_error = str(e)
    report["claims"] = claims
    report["claims_error"] = claims_error

    # 6. Бэклог: первый кандидат из «Высокий приоритет»
    backlog_next = None
    bt = _read(agents / "tasks" / "backlog.md")
    if bt:
        in_high = False
        for line in bt.splitlines():
            if line.startswith("###"):
                in_high = "высокий" in line.lower()
                continue
            if in_high and re.match(OPEN_ITEM_LINE, line):
                backlog_next = line.strip().lstrip("-* ").strip()
                break
    report["backlog_next"] = backlog_next

    # 7. Прошлая сессия: инструкция для следующего агента из свежайшей записи
    last_session = None
    hist = agents / "history"
    if hist.is_dir():
        sessions = sorted(f for f in hist.glob("session_*.md"))
        if sessions:
            newest = sessions[-1]  # имена session_YYYY-MM-DD_NN_* сортируются лексикографически
            info = {"file": newest.name}
            st_text = _read(newest)
            if st_text:
                title = next((l for l in st_text.splitlines() if l.startswith("# ")), None)
                info["title"] = title.lstrip("# ").strip() if title else None
                info["next_steps"] = _section(st_text, "Инструкция для следующего агента")
            last_session = info
    report["last_session"] = last_session

    return report


def format_handoff(report: dict) -> str:
    lines = [
        "# 🤝 Эстафета для следующего агента",
        "",
        f"_Сгенерировано `brain handoff` · {report['generated_at']}_",
        "",
        "## 📊 Статус проекта",
        "",
    ]
    st = report.get("status") or {}
    if st.get("phase"):
        lines.append(f"**Фаза:** {st['phase']}")
    if st.get("now"):
        lines += ["", st["now"]]
    if not st.get("phase") and not st.get("now"):
        lines.append("(STATUS.md не найден или пуст)")

    lines += ["", "## 📋 Активная задача", ""]
    at = report.get("active_task")
    if at:
        if at.get("title"):
            lines.append(f"**{at['title']}**")
        if at.get("status"):
            lines.append(f"Статус: {at['status']}")
        if at.get("open_items"):
            lines += ["", "Незакрытые пункты (продолжить ровно с них):"]
            lines += [f"- {i.lstrip('-* ').strip()}" for i in at["open_items"]]
    else:
        lines.append("(не выбрана — возьми задачу из бэклога и заведи план, Plan-First)")

    plan = report.get("plan")
    if plan:
        lines += ["", "## 📐 Активный план", ""]
        if plan.get("status"):
            lines.append(f"{plan['id']} ({plan['file']}) — {plan['status']}")
        if plan.get("open_steps"):
            lines += ["", "Открытые шаги плана:"]
            lines += [f"- {s.lstrip('-* ').strip()}" for s in plan["open_steps"]]

    lines += ["", "## 🐛 Открытые баги", ""]
    if report.get("open_bugs"):
        lines += [f"- {name}" for name in report["open_bugs"]]
    else:
        lines.append("(нет)")

    lines += ["", "## 🔒 Активные локи", ""]
    if report.get("claims_error"):
        lines.append(f"(локи недоступны: {report['claims_error']})")
    elif report.get("claims"):
        for c in report["claims"]:
            lines.append(f"- {c.get('task', '?')} — {c.get('agent', '?')} (PID {c.get('pid', '?')}, {c.get('status', '?')})")
    else:
        lines.append("(свободно)")

    lines += ["", "## 🚀 Следующий кандидат из бэклога", ""]
    lines.append(report.get("backlog_next") or "(бэклог пуст или не найден)")

    last = report.get("last_session")
    lines += ["", "## 📝 Прошлая сессия", ""]
    if last:
        if last.get("title"):
            lines.append(f"{last['title']} (`agents/history/{last['file']}`)")
        if last.get("next_steps"):
            lines += ["", last["next_steps"]]
        elif last.get("title") is None:
            lines.append(f"`agents/history/{last['file']}` (не читается)")
    else:
        lines.append("(записей сессий нет)")

    lines += [
        "",
        "## 🧭 Как продолжать",
        "",
        "1. Прочти `agents/AGENT_GUIDE.md` и `agents/rules/ANTI_PATTERNS.md`.",
        "2. Продолжи с первого незакрытого пункта выше, не переделывая сделанное.",
        "3. Отмечай прогресс `[x]` параллельно с работой; ошибки — в `bugs_and_fixes/`.",
        "4. В конце сессии: `python brain.py end` → `python brain.py handoff` → `brain archive`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="🤝 Эстафета для следующего агента")
    parser.add_argument("--root", default=None, help="Корень проекта")
    parser.add_argument("--json", action="store_true", help="Вывести собранные данные в JSON")
    args = parser.parse_args()
    report = collect_handoff(root=Path(args.root) if args.root else None)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_handoff(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
