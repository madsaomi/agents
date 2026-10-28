#!/usr/bin/env python3
"""
Second Brain Context Dumper.
Собирает ключевой контекст проекта (статус, активную задачу, карту кодовой базы,
последнюю сессию) в один компактный блок текста и копирует его в буфер обмена.
Идеально для передачи контекста в веб-чаты ChatGPT, Claude.ai, DeepSeek или Gemini.
"""

import sys
import os
import subprocess
from pathlib import Path

# Обеспечиваем поддержку UTF-8 в консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
AGENTS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AGENTS_DIR.parent

def copy_to_clipboard(text: str) -> bool:
    """Пытается скопировать текст в буфер обмена кроссплатформенно."""
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            process.communicate(text.encode("utf-16le"))
            return True
        elif sys.platform == "darwin":
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-8"))
            return True
        else:
            process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-8"))
            return True
    except Exception:
        return False

def build_context_dump(root: Path = None, budget: int = None) -> str:
    """
    Собирает контекст проекта. budget — лимит токенов (грубая оценка ~3 символа/токен
    для смешанного ru/en markdown): при превышении секции последовательно сжимаются
    (автосуммаризация: заголовки/чек-листы/таблицы), низкоприоритетные убираются,
    ядро (статус + активная задача) усекается в крайнем случае.
    """
    base_agents = (Path(root) / "agents") if root else AGENTS_DIR

    # (приоритет, заголовок, файл) — чем выше, тем важнее оставить под бюджетом
    file_sections = [
        (100, "📊 СТАТУС ПРОЕКТА", base_agents / "STATUS.md"),
        (95, "📋 АКТИВНАЯ ЗАДАЧА", base_agents / "tasks" / "active_task.md"),
        (90, "📐 ПЛАН РЕАЛИЗАЦИИ (Plan-First)", None),  # подбирается ниже из plans/
        (80, "🗺️ КАРТА КОДОВОЙ БАЗЫ", base_agents / "architecture" / "CODEBASE_MAP.md"),
        (70, "📝 ПОСЛЕДНЯЯ СЕССИЯ", None),              # подбирается ниже из history/
        (50, "🎯 ТРЕБОВАНИЯ К ПРОДУКТУ (PRD)", base_agents / "product" / "PRD.md"),
        (45, "📏 ПРАВИЛА АГЕНТА", base_agents / "rules" / "AGENT_RULES.md"),
        (40, "📖 ГЛОССАРИЙ ТЕРМИНОВ", base_agents / "GLOSSARY.md"),
    ]

    sections = []  # [{"priority", "title", "label", "content"}]

    # активный план
    plans_dir = base_agents / "plans"
    plan_files = sorted(
        [f for f in plans_dir.glob("plan_*.md") if f.name != "README.md"],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    ) if plans_dir.is_dir() else []
    active_plan = None
    for pf in plan_files:
        try:
            txt = pf.read_text(encoding="utf-8", errors="replace")
            if "IN_PROGRESS" in txt or "APPROVED" in txt:
                active_plan = pf
                break
        except Exception:
            pass
    if active_plan is None and plan_files:
        active_plan = plan_files[0]

    # последняя сессия
    history_dir = base_agents / "history"
    history_files = sorted(
        [f for f in history_dir.glob("*.md") if f.name != "README.md"],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    ) if history_dir.is_dir() else []
    latest = history_files[0] if history_files else None

    for priority, title, path in file_sections:
        if title.startswith("📐"):
            path = active_plan
            label = f"plans/{active_plan.name}" if active_plan else ""
        elif title.startswith("📝"):
            path = latest
            label = f"history/{latest.name}" if latest else ""
        else:
            label = path.name if path else ""
        if path is None or not Path(path).is_file():
            continue
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not content:
            continue
        sections.append({
            "priority": priority,
            "title": title,
            "label": label,
            "content": content,
        })

    def _fit():
        """Рендер текущего набора секций и оценка; (дамп, оценка)."""
        d = _render_dump(sections, budget=budget)
        return d, estimate_tokens(d)

    dump, est = _fit()
    if budget is None or est <= budget:
        return dump

    def _done():
        return _render_dump(sections, budget=budget)

    # Этап 1: автосуммаризация — сжимаем секции, начиная с низкоприоритетных
    for sec in sorted(sections, key=lambda s: s["priority"]):
        sec["content"] = _compact(sec["content"])
        dump, est = _fit()
        if est <= budget:
            return _done()

    # Этап 2: убираем целиком низкоприоритетные (ядро: приоритет >= 95 — статус/задача)
    for sec in sorted(list(sections), key=lambda s: s["priority"]):
        if sec["priority"] >= 95:
            continue
        sections.remove(sec)
        dump, est = _fit()
        if est <= budget:
            return _done()

    # Этап 3: даже ядро не влезает — оставляем только самое важное
    for sec in sorted(list(sections), key=lambda s: s["priority"]):
        if len(sections) <= 1:
            break
        sections.remove(sec)
        dump, est = _fit()
        if est <= budget:
            return _done()

    # Этап 4: крайний случай — итеративно усекаем оставшуюся секцию под бюджет
    if sections:
        for _ in range(14):
            dump, est = _fit()
            if est <= budget:
                return _done()
            cur = sections[0]["content"]
            if len(cur) <= 80:
                break
            sections[0]["content"] = _truncate(cur, max(80, int(len(cur) * 0.7)))
    return _done()


def estimate_tokens(text: str) -> int:
    """Грубая оценка токенов для смешанного ru/en markdown (~3 символа на токен)."""
    return max(1, len(text or "") // 3)


def _compact(content: str, max_lines: int = 40, head: int = 4) -> str:
    """
    Автосуммаризация секции: сохраняет структуру (заголовки, чек-листы, таблицы,
    списки, выделенные статусы), отбрасывает «воду» прозы. Из шапки (первые строки)
    берутся только короткие — сплошной абзац-монстр в шапке не спасает.
    """
    lines = content.splitlines()
    structure = ("#", "-", "*", "|", ">", "[", "1.", "2.", "3.", "4.", "5.", "**")

    kept = [l for l in lines[:head] if l.strip() and len(l.strip()) < 200]
    for line in lines[head:]:
        s = line.strip()
        if not s:
            continue
        if s.startswith(structure) and line not in kept:
            kept.append(line)
        if len(kept) >= max_lines:
            break
    result = "\n".join(kept).rstrip()
    if len(result) < len(content):
        result += f"\n… [сжато под бюджет: {len(lines)} строк → {len(kept)}]"
    return result


def _truncate(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content
    cut = content[:max_chars]
    # обрезаем по последнему переводу строки, чтобы не резать посреди слова
    nl = cut.rfind("\n")
    if nl > max_chars // 2:
        cut = cut[:nl]
    return cut + f"\n… [обрезано {len(content) - len(cut)} символов под бюджет]"


def _render_dump(sections, budget=None) -> str:
    # Пометка должна быть фиксированной длины (без вставления числовой оценки):
    # иначе оценка в _fit() и итоговый рендер в _done() расходятся на размер числа.
    lines = ["# 🧠 PROJECT CONTEXT SNAPSHOT (Second Brain)"]
    if budget is not None:
        lines.append(f"> ⚙️ Сжато под бюджет: {budget} токенов (оценка ~3 символа/токен)")
    lines.append("> Этот снимок сгенерирован автоматически для передачи полного контекста проекта в AI чат.\n")
    for sec in sections:
        lines.append(f"## {sec['title']} (`{sec['label']}`)\n")
        lines.append("```markdown")
        lines.append(sec["content"])
        lines.append("```\n")
    return "\n".join(lines)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Собрать контекст проекта для веб-чатов")
    parser.add_argument("--budget", type=int, default=None,
                        help="Лимит токенов (грубая оценка): секции будут сжаты/отброшены под него")
    args = parser.parse_args(argv)

    print("\n📦 Сборка контекста проекта из каталога agents/...")
    dump = build_context_dump(budget=args.budget)
    dump_len = len(dump)
    dump_lines = dump.count("\n")

    # Сохраняем в файл для резервной копии
    dump_file = SCRIPT_DIR / "context_dump.md"
    dump_file.write_text(dump, encoding="utf-8")

    copied = copy_to_clipboard(dump)

    budget_note = f", бюджет: {args.budget} токенов (~{estimate_tokens(dump)} по оценке)" if args.budget else ""
    print(f"✓ Контекст успешно сформирован! (Строк: {dump_lines}, Символов: {dump_len}{budget_note})")
    print(f"✓ Сохранен в резервный файл: {dump_file.relative_to(PROJECT_ROOT) if PROJECT_ROOT in dump_file.parents else dump_file.name}")
    
    if copied:
        print("\n🎉 ТЕКСТ УСПЕШНО СКОПИРОВАН В БУФЕР ОБМЕНА!")
        print("👉 Просто откройте окно чата (ChatGPT / Claude / DeepSeek) и нажмите Ctrl + V!\n")
    else:
        print("\n💡 Скопируйте содержимое вручную из файла agents/tools/context_dump.md\n")

if __name__ == "__main__":
    main()
