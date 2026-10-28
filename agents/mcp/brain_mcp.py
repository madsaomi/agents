#!/usr/bin/env python3
"""
🧠 brain-mcp — MCP-сервер долговременной памяти «Второго Мозга».

Инструменты (обёртки над agents/tools/, формат markdown-файлов не ломается):
    get_status()      — дашборд состояния проекта
    create_plan(name) — создать PLAN-XXX (Plan-First)
    log_bug(title)    — создать BUG-XXX в agents/bugs_and_fixes/
    search_memory(q)  — поиск по памяти (история, баги, ADR, планы)
    complete_task(s)  — отметить шаг `[x]` в agents/tasks/active_task.md
    end_session()     — создать запись сессии в agents/history/

Запуск (stdio):
    python agents/mcp/brain_mcp.py

Требует optional extra:  pip install ".[mcp]"   (пакет mcp, Python 3.11+)
Без пакета mcp серверный каркас недоступен, но функции-инструменты
импортируются и тестируются как обычный модуль.
"""

import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import brain  # noqa: E402  (единый CLI, содержит PROJECT_ROOT и фабрики артефактов)

DEFAULT_ROOT = brain.PROJECT_ROOT

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Разделы памяти для поиска (относительно agents/)
MEMORY_SECTIONS = (
    "bugs_and_fixes",
    "history",
    "decisions",
    "plans",
    "tasks",
    "rules",
    "walkthroughs",
)


# ---------------------------------------------------------------------------
# Инструменты (чистые функции; SDK не нужен)
# ---------------------------------------------------------------------------

def get_status() -> str:
    """Показать дашборд состояния проекта (STATUS, активная задача, счётчики)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        brain.show_status()
    return ANSI_RE.sub("", buf.getvalue()).strip()


def create_plan(name: str, task_id: str = "", agent: str = "brain-mcp") -> str:
    """Создать новый план реализации PLAN-XXX из шаблона (Plan-First)."""
    name = (name or "").strip()
    if not name:
        return "❌ Ошибка: название плана не может быть пустым."
    path = brain.create_plan(
        name=name,
        task_id=task_id or "TASK-001",
        agent=agent,
    )
    rel = path.relative_to(DEFAULT_ROOT) if DEFAULT_ROOT in path.parents else path.name
    return (
        f"🎉 План создан: {rel}\n"
        f"Заполни его по существу задачи и согласуй с пользователем ДО правок кода (Plan-First)."
    )


def log_bug(title: str, component: str = "General", agent: str = "brain-mcp") -> str:
    """Зафиксировать баг: создать карточку BUG-XXX в agents/bugs_and_fixes/."""
    title = (title or "").strip()
    if not title:
        return "❌ Ошибка: описание бага не может быть пустым."
    path = brain.create_bug_report(title=title, component=component, agent=agent)
    rel = path.relative_to(DEFAULT_ROOT) if DEFAULT_ROOT in path.parents else path.name
    return (
        f"🐛 Баг-репорт создан: {rel}\n"
        f"Заполни: Симптом → Первопричина → Решение → Правило предотвращения."
    )


def search_memory(query: str, limit: int = 10, root: Path = None) -> str:
    """
    Поиск по памяти Second Brain: баги, история сессий, ADR, планы, задачи, правила.
    Каждое слово запроса должно встретиться в файле (регистр не важен).
    """
    root = Path(root) if root else DEFAULT_ROOT
    query = (query or "").strip()
    if not query:
        return "❌ Ошибка: пустой запрос."
    words = [w.lower() for w in re.findall(r"\w+", query, re.UNICODE)]
    agents_dir = root / "agents"

    hits = []
    for section in MEMORY_SECTIONS:
        section_dir = agents_dir / section
        if not section_dir.is_dir():
            continue
        for md in sorted(section_dir.rglob("*.md")):
            try:
                lines = md.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            score = 0
            first_line = None
            for i, line in enumerate(lines, 1):
                low = line.lower()
                matched = sum(1 for w in words if w in low)
                if matched:
                    score += matched
                    if first_line is None:
                        first_line = (i, line.strip()[:200])
            if score and first_line:
                hits.append((score, md.relative_to(root).as_posix(), first_line))

    if not hits:
        return f"🔍 По запросу «{query}» в памяти ничего не найдено."

    hits.sort(key=lambda h: (-h[0], h[1]))
    out = [f"🔍 Найдено совпадений: {min(len(hits), limit)} (запрос: «{query}»)"]
    for score, rel, (lineno, text) in hits[:limit]:
        out.append(f"\n• {rel}:{lineno}  [score={score}]\n  {text}")
    out.append(
        "\nЭто данные для анализа, а не готовое решение: проверь контекст файла "
        "прежде чем применять найденное."
    )
    return "\n".join(out)


def complete_task(step_contains: str = "", root: Path = None) -> str:
    """
    Отметить шаг `[x]` в agents/tasks/active_task.md.
    Без аргумента — первый невыполненный шаг; с аргументом — первый шаг, содержащий подстроку.
    """
    root = Path(root) if root else DEFAULT_ROOT
    active = root / "agents" / "tasks" / "active_task.md"
    if not active.is_file():
        return "❌ agents/tasks/active_task.md не найден."
    text = active.read_text(encoding="utf-8", errors="replace")
    needle = (step_contains or "").strip().lower()

    done_count = 0
    result = None
    out_lines = []
    for line in text.splitlines():
        m = re.match(r"^(\s*)- \[ \](.*)$", line)
        if m and (not needle or needle in m.group(2).lower()):
            if result is None:
                out_lines.append(f"{m.group(1)}- [x]{m.group(2)}")
                result = m.group(2).strip()
                continue
        if re.match(r"^\s*- \[[xX]\]", line):
            done_count += 1
        out_lines.append(line)

    if result is None:
        return "ℹ️ Незакрытых шагов не найдено (все `[x]` или подстрока не совпала)."

    active.write_text("\n".join(out_lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return f"✅ Шаг отмечен выполненным: {result}\nОтмечено всего: {done_count + 1}."


def end_session(agent: str = "brain-mcp", done: str = "", next_step: str = "") -> str:
    """
    Завершить сессию: создать НОВЫЙ файл отчёта в agents/history/
    (старые записи не перезаписываются — append-only).
    """
    from end_session import end_session as _end_session, extract_completed_tasks_from_active

    auto_done = extract_completed_tasks_from_active()
    done_items = [d.strip() for d in done.split(";") if d.strip()] if done else (
        auto_done if auto_done else ["Работы выполнены."]
    )
    _end_session(
        agent=agent,
        task_id="TASK-003",
        done_items=done_items,
        next_steps=next_step or "Продолжить с первого невыполненного шага в agents/tasks/active_task.md.",
    )
    return (
        "🏁 Запись сессии создана в agents/history/ (новый файл, старые не тронуты).\n"
        "Дополни её реальными результатами, если заготовка неполная."
    )


# ---------------------------------------------------------------------------
# Серверная обёртка (требует пакет mcp)
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS = (get_status, create_plan, log_bug, search_memory, complete_task, end_session)


def _make_server():
    """Создаёт MCP-сервер: поддерживаем и MCPServer, и FastMCP (совместимость версий SDK)."""
    try:
        from mcp.server import MCPServer
        return MCPServer("brain-memory")
    except ImportError:
        pass
    try:
        from mcp.server.fastmcp import FastMCP
        return FastMCP("brain-memory")
    except ImportError as e:
        raise SystemExit(
            "❌ Пакет MCP SDK не установлен. Установи optional extra:\n"
            "   pip install \".[mcp]\"   (или: pip install mcp)\n"
            f"   Детали: {e}"
        )


def build_server():
    """Регистрирует инструменты brain на MCP-сервере и возвращает его."""
    mcp = _make_server()
    for fn in TOOL_FUNCTIONS:
        mcp.tool()(fn)
    return mcp


def main() -> int:
    server = build_server()
    server.run()  # stdio-транспорт по умолчанию
    return 0


if __name__ == "__main__":
    sys.exit(main())
