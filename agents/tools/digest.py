#!/usr/bin/env python3
"""
Second Brain Digest (PLAN-013 / TASK-012): компактная сводка проекта для
вставки в веб-чаты. Ниша: `dump` — полный контекст (десятки КБ), `handoff` —
эстафета входящему агенту, `digest` — короткая выжимка «что за проект, где мы,
что открыто» за ~1 экран.

Переиспользует готовые сборщики (без нового парсинга markdown):
  handoff.collect_handoff() — фаза/задача/план/баги/локи/бэклог
  stats.collect_stats()     — счётчики памяти, битые связи, устаревшее

Использование:
    python agents/tools/digest.py [--tokens N] [--root PATH] [--json]
    python brain.py digest [--tokens N] [--copy]    # через диспетчер

Только stdlib.
"""

import argparse
import json
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

# Грубая оценка токенов, как в dump_context (~3 символа/токен)
CHARS_PER_TOKEN = 3


def render_digest(handoff_report: dict, stats: dict, max_tokens: int = None) -> str:
    """Компактный дайджест из готовых отчётов handoff и stats."""
    lines = []
    h = handoff_report or {}

    lines.append("# 🧠 Дайджест проекта")
    lines.append(f"_Сгенерировано `brain digest` · {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("")

    st = h.get("status") or {}
    if st.get("phase"):
        lines.append(f"**📊 Фаза:** {st['phase']}")

    at = h.get("active_task")
    if at:
        bits = []
        if at.get("title"):
            bits.append(at["title"])
        if at.get("status"):
            bits.append(at["status"])
        line = "**📋 Задача:** " + " — ".join(bits)
        if at.get("open_items"):
            first = at["open_items"][0].lstrip("-* ").strip()
            line += f" (открыто пунктов: {len(at['open_items'])}, первый: {first})"
        lines.append(line)
    else:
        lines.append("**📋 Задача:** не выбрана — см. backlog")

    plan = h.get("plan")
    if plan and plan.get("status"):
        lines.append(f"**📐 План:** {plan.get('id', '')} ({plan.get('file', '')}) — {plan['status']}")

    bugs = h.get("open_bugs") or []
    lines.append(f"**🐛 Открытые баги:** {', '.join(bugs) if bugs else 'нет'}")

    if h.get("claims_error"):
        lines.append(f"**🔒 Локи:** недоступны ({h['claims_error']})")
    elif h.get("claims"):
        lines.append(f"**🔒 Локи:** {', '.join(c.get('task', '?') for c in h['claims'])}")
    else:
        lines.append("**🔒 Локи:** свободно")

    s = stats or {}
    sect = s.get("sections", {})
    counts = ", ".join(f"{k} {v}" for k, v in sect.items() if v)
    lines.append(f"**📈 Память:** записей {s.get('total_records', '—')} ({counts or 'нет данных'}), "
                 f"битых связей {len(s.get('broken_links', []))}, устаревших {len(s.get('stale', []))}")

    if h.get("backlog_next"):
        lines.append(f"**🚀 Бэклог:** {h['backlog_next']}")

    lines.append("")
    lines.append("> Это дайджест. Полный контекст: `brain dump`, эстафета: `brain handoff`, "
                 "исходники правил: `agents/rules/CORE_RULES.md`.")
    text = "\n".join(lines)

    # Бюджет токенов: усекаем хвост с пометкой (грубая оценка ~3 символа/токен)
    if max_tokens:
        limit = max_tokens * CHARS_PER_TOKEN
        if len(text) > limit:
            text = text[:limit].rsplit("\n", 1)[0] + "\n\n_…дайджест усечён под бюджет "
            text += f"{max_tokens} токенов; полный: `brain digest` без --tokens._"
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="🧠 Компактный дайджест проекта для веб-чатов")
    parser.add_argument("--tokens", type=int, default=None, help="Бюджет токенов (усечение хвоста)")
    parser.add_argument("--json", action="store_true", help="Вывести исходные данные (handoff+stats) в JSON")
    parser.add_argument("--root", default=None, help="Корень проекта")
    args = parser.parse_args()
    root = Path(args.root) if args.root else None

    import handoff as brain_handoff
    import stats as memory_stats
    report = brain_handoff.collect_handoff(root=root)
    if args.json:
        print(json.dumps({"handoff": report,
                          "stats": memory_stats.collect_stats(root=root)},
                         ensure_ascii=False, indent=2))
        return 0
    print(render_digest(report, memory_stats.collect_stats(root=root), max_tokens=args.tokens))
    return 0


if __name__ == "__main__":
    sys.exit(main())
