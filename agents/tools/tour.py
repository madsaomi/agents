#!/usr/bin/env python3
"""
Интерактивный тур по Второму Мозгу (PLAN-004; вынесен из brain.py в PLAN-009).
Экраны и рендер для `python brain.py tour [--list]`.

Только stdlib.
"""

import sys

# Цвета ANSI (идиома модулей tools/)
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Экраны тура: (заголовок, содержимое)
TOUR_SCREENS = [
    ("🧠 Добро пожаловать во Второй Мозг!",
     "Этот шаблон превращает markdown-правила в исполняемую систему.\n"
     "Память проекта живёт в каталоге agents/, инструменты — в agents/tools/.\n"
     "Точка входа для агентов: AGENTS.md → agents/AGENT_GUIDE.md."),
    ("1/7 📚 Память: разделы agents/",
     "  plans/          — планы реализации (Plan-First)\n"
     "  tasks/          — активная задача, архив, локи claim\n"
     "  history/        — отчёты сессий (append-only, ничего не затирать)\n"
     "  bugs_and_fixes/ — баги и их решения\n"
     "  decisions/      — ADR (архитектурные решения)\n"
     "  walkthroughs/   — отчёты о сдаче этапов"),
    ("2/7 📐 Сначала план — потом код",
     "  python brain.py plan \"Название\"     — создать PLAN-XXX\n"
     "  Правка кода без плана блокируется хуком Plan-First (Claude Code),\n"
     "  а правило зафиксировано в agents/rules/CORE_RULES.md (п. 1)."),
    ("3/7 ⚙️ Единый источник правил",
     "  Правь ТОЛЬКО agents/rules/CORE_RULES.md, затем:\n"
     "  python brain.py sync          — перегенерировать CLAUDE.md, .cursorrules,\n"
     "                                  .windsurfrules, copilot, .cursor/rules\n"
     "  python brain.py sync --check  — проверить дрейф (ловится в CI)"),
    ("4/7 🔍 Поиск и контекст",
     "  python brain.py search \"jwt timeout\"   — FTS5-поиск по всей памяти\n"
     "  python brain.py stats [--json]          — дашборд здоровья памяти\n"
     "  python brain.py dump --budget 4000      — контекст в буфер под лимит токенов"),
    ("5/7 🤝 Параллельная работа агентов",
     "  python brain.py claim TASK-XXX [--worktree]  — забрать задачу (лок)\n"
     "  python brain.py claims                       — кто что держит\n"
     "  python brain.py release TASK-XXX             — освободить"),
    ("6/7 🔌 Расширения",
     "  MCP-инструменты: pip install \".[mcp]\" → python agents/mcp/brain_mcp.py\n"
     "  Пресеты стека:   python brain.py preset django-drf | fastapi | nextjs | aiogram-bot\n"
     "  Обновление:      python brain.py upgrade (не затирает ваши правки)\n"
     "  Проверка:        python brain.py check [--fix] · python brain.py doctor (окружение)"),
    ("7/7 ✅ Готово!",
     "Начни с agents/STATUS.md и agents/tasks/active_task.md.\n"
     "Эстафета: python brain.py handoff [--copy] · Архив задачи: python brain.py archive\n"
     "Полный гайд: AGENTS.md · README.md · agents/AGENT_GUIDE.md\n"
     "Команда снова: python brain.py tour"),
]


def render_screens(screens, interactive=False):
    """Печать экранов тура: все сразу (--list / не-TTY) или пошагово с input()."""
    if not interactive:
        for i, (title, body) in enumerate(screens, 1):
            bar = "═" * 58
            print(f"\n{BOLD}{CYAN}{bar}{RESET}")
            print(f"{BOLD}{title}{RESET}")
            print(f"{CYAN}{bar}{RESET}")
            print(body)
        print()
        return
    total = len(screens)
    for i, (title, body) in enumerate(screens, 1):
        print(f"\n{BOLD}{CYAN}{'═' * 58}{RESET}")
        print(f"{BOLD}{title}{RESET}  {CYAN}({i}/{total}){RESET}")
        print(f"{CYAN}{'═' * 58}{RESET}")
        print(body)
        if i < total:
            try:
                input(f"\n{CYAN}→ Enter — дальше, Ctrl+C — выход…{RESET}")
            except (EOFError, KeyboardInterrupt):
                print("\nТур прерван. Вернуться: python brain.py tour")
                break
