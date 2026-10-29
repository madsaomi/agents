#!/usr/bin/env python3
"""
🧠 Second Brain Unified CLI (brain.py)
Единый инструмент управления экосистемой «Второго Мозга».

Команды:
    python agents/tools/brain.py status              - Показать дашборд проекта в терминале
    python agents/tools/brain.py plan <name>         - Создать новый PLAN-XXX (Plan-First)
    python agents/tools/brain.py bug <title>         - Создать новый BUG-XXX (Баг-репорт)
    python agents/tools/brain.py adr <title>         - Создать новый ADR-XXX (Архитектурное решение)
    python agents/tools/brain.py task <title>        - Создать карточку задачи TASK-XXX
    python agents/tools/brain.py dump                - Скопировать контекст в буфер обмена для AI-чатов
    python agents/tools/brain.py check [--fix]       - Проверить целостность (с авто-исправлением)
    python agents/tools/brain.py sync [--check]      - Сгенерировать конфиги AI-инструментов из CORE_RULES.md
    python agents/tools/brain.py search "<query>"    - Поиск по памяти (FTS5; --reindex — переиндексировать)
    python agents/tools/brain.py claim <task>        - Забрать задачу (лок для параллельных агентов; --worktree)
    python agents/tools/brain.py release <task>      - Освободить задачу (--worktree — удалить worktree)
    python agents/tools/brain.py claims              - Показать активные блокировки задач
    python agents/tools/brain.py dump [--budget N]   - Контекст в буфер обмена (N — лимит токенов)
    python agents/tools/brain.py presets             - Показать доступные пресеты стека
    python agents/tools/brain.py preset <имя>        - Применить пресет стека (django-drf, aiogram-bot, ...)
    python agents/tools/brain.py upgrade             - Обновить шаблоны, не затирая данные пользователя
    python agents/tools/brain.py stats [--json]      - Дашборд здоровья памяти (счётчики, битые ссылки, локи)
    python agents/tools/brain.py links <ID>          - Вики-связи [[...]]: исходящие, обратные, --unresolved
    python agents/tools/brain.py tour [--list]       - Интерактивный гид для нового пользователя
    python agents/tools/brain.py end                 - Завершить сессию и сформировать отчет
"""

import sys
import os
import re
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Поддержка UTF-8 в консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Цвета ANSI
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

SCRIPT_DIR = Path(__file__).resolve().parent

def _detect_project_root() -> Path:
    """
    Корень проекта: cwd, если в нём есть agents/ (запуск установленного пакета),
    иначе — расположение инструмента (dev-режим из репозитория шаблона).
    """
    cwd = Path.cwd()
    if (cwd / "agents").is_dir():
        return cwd
    return SCRIPT_DIR.parent

PROJECT_ROOT = _detect_project_root()
AGENTS_DIR = PROJECT_ROOT / "agents"
# Источник шаблонов/пресетов всегда рядом со скриптом (работает и в пакете)
PRESETS_SOURCE_DIR = SCRIPT_DIR.parent / "presets"

# Экраны интерактивного тура (PLAN-004): (заголовок, содержимое)
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
     "  Проверка:        python brain.py check [--fix]"),
    ("7/7 ✅ Готово!",
     "Начни с agents/STATUS.md и agents/tasks/active_task.md.\n"
     "Полный гайд: AGENTS.md · README.md · agents/AGENT_GUIDE.md\n"
     "Команда снова: python brain.py tour"),
]

# Импортируем существующие утилиты
sys.path.insert(0, str(SCRIPT_DIR))
from check_integrity import run_integrity_check
from dump_context import build_context_dump, copy_to_clipboard, estimate_tokens
from new_plan import create_plan, slugify
from end_session import end_session, extract_completed_tasks_from_active
from init_project import init_project
import search as memory_search
import locks as task_locks
import stats as memory_stats
import links as memory_links

# -----------------------------------------------------------------------------
# Вспомогательные функции нумерации
# -----------------------------------------------------------------------------

def get_next_number(directory: Path, prefix: str) -> int:
    """Определяет следующий порядковый номер для файлов PREFIX_XXX_*."""
    max_num = 0
    pattern = re.compile(rf"^{prefix}_?(\d{{3,}})_", re.IGNORECASE)
    for p in directory.glob(f"{prefix}*.md"):
        m = pattern.match(p.name)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    return max_num + 1

# -----------------------------------------------------------------------------
# Генераторы сущностей: BUG, ADR, TASK
# -----------------------------------------------------------------------------

def create_bug_report(title: str, component: str, agent: str) -> Path:
    bugs_dir = AGENTS_DIR / "bugs_and_fixes"
    template_file = AGENTS_DIR / "templates" / "template_bug_report.md"
    if not template_file.is_file():
        raise FileNotFoundError("Шаблон template_bug_report.md не найден!")

    next_num = get_next_number(bugs_dir, "BUG")
    num_str = f"{next_num:03d}"
    slug = slugify(title)
    filename = f"BUG_{num_str}_{slug}.md"
    target = bugs_dir / filename

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = template_file.read_text(encoding="utf-8", errors="replace")
    content = content.replace("# 🐛 Шаблон отчета об ошибке (Bug Report Template)", f"# 🐛 Баг-репорт: BUG-{num_str} — {title}")
    content = content.replace("BUG-XXX", f"BUG-{num_str}")
    content = content.replace("YYYY-MM-DD HH:MM", now_str)
    content = content.replace("[Имя агента и модель]", agent)
    content = content.replace("[Например: backend/main.py, static/js/app.js]", component or "Общий компонент")
    content = content.replace("[🟡 В ПРОЦЕССЕ / 🟢 РЕШЕНО]", "🟡 В ПРОЦЕССЕ")

    target.write_text(content, encoding="utf-8")
    return target

def create_adr_record(title: str, agent: str) -> Path:
    adr_dir = AGENTS_DIR / "decisions"
    template_file = AGENTS_DIR / "templates" / "template_adr.md"
    if not template_file.is_file():
        raise FileNotFoundError("Шаблон template_adr.md не найден!")

    next_num = get_next_number(adr_dir, "ADR")
    num_str = f"{next_num:03d}"
    slug = slugify(title)
    filename = f"ADR_{num_str}_{slug}.md"
    target = adr_dir / filename

    now_str = datetime.now().strftime("%Y-%m-%d")
    content = template_file.read_text(encoding="utf-8", errors="replace")
    content = content.replace("# 🏛️ Шаблон архитектурного решения (ADR Template)", f"# 🏛️ Архитектурное решение: ADR-{num_str} — {title}")
    content = content.replace("ADR-XXX", f"ADR-{num_str}")
    content = content.replace("[Например: Выбор единого сервера FastAPI + aiogram вместо микросервисов]", title)
    content = content.replace("YYYY-MM-DD", now_str)
    content = content.replace("[Имена агентов]", agent)
    content = content.replace("[PROPOSED / ACCEPTED / DEPRECATED / SUPERSEDED]", "PROPOSED")

    target.write_text(content, encoding="utf-8")
    return target

def create_task_card(title: str, priority: str, agent: str) -> Path:
    tasks_dir = AGENTS_DIR / "tasks"
    template_file = AGENTS_DIR / "templates" / "template_task.md"
    if not template_file.is_file():
        raise FileNotFoundError("Шаблон template_task.md не найден!")

    next_num = get_next_number(tasks_dir, "task")
    num_str = f"{next_num:03d}"
    slug = slugify(title)
    filename = f"task_{num_str}_{slug}.md"
    target = tasks_dir / filename

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = template_file.read_text(encoding="utf-8", errors="replace")
    content = content.replace("# 📋 Шаблон карточки задачи (Task Template)", f"# 📋 Карточка задачи: TASK-{num_str} — {title}")
    content = content.replace("TASK-XXX", f"TASK-{num_str}")
    content = content.replace("[Краткое и емкое название задачи]", title)
    content = content.replace("[LOW / MEDIUM / HIGH / CRITICAL]", priority.upper())
    content = content.replace("[⚪ PLANNED / 🟡 IN_PROGRESS / 🟢 COMPLETED / 🔴 BLOCKED]", "⚪ PLANNED")
    content = content.replace("YYYY-MM-DD", now_str[:10])
    content = content.replace("[Имя агента]", agent)

    target.write_text(content, encoding="utf-8")
    return target

def create_walkthrough(title: str, plan_id: str, task_id: str, agent: str) -> Path:
    wt_dir = AGENTS_DIR / "walkthroughs"
    template_file = AGENTS_DIR / "templates" / "template_walkthrough.md"
    if not template_file.is_file():
        raise FileNotFoundError("Шаблон template_walkthrough.md не найден!")

    # Нумерация: WT_001, WT_002...
    max_num = 0
    pattern = re.compile(r"^WT_(\d{3,})_", re.IGNORECASE)
    for p in wt_dir.glob("WT_*.md"):
        m = pattern.match(p.name)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    next_num = max_num + 1
    num_str = f"{next_num:03d}"
    slug = slugify(title)
    filename = f"WT_{num_str}_{slug}.md"
    target = wt_dir / filename

    now_str = datetime.now().strftime("%Y-%m-%d")
    content = template_file.read_text(encoding="utf-8", errors="replace")
    content = content.replace("{{FEATURE_NAME}}", title)
    content = content.replace("{{DATE}}", now_str)
    content = content.replace("{{AGENT_NAME}}", agent)
    content = content.replace("PLAN-XXX", plan_id)
    content = content.replace("TASK-XXX", task_id)

    target.write_text(content, encoding="utf-8")
    return target

# -----------------------------------------------------------------------------
# Дашборд состояния проекта (brain status)
# -----------------------------------------------------------------------------

def show_status():
    status_file = AGENTS_DIR / "STATUS.md"
    active_file = AGENTS_DIR / "tasks" / "active_task.md"

    proj_name = "Не инициализирован"
    stack = "Не указан"
    last_upd = "Неизвестно"
    curr_agent = "Не указан"

    if status_file.is_file():
        text = status_file.read_text(encoding="utf-8", errors="replace")
        m_name = re.search(r"\*\*Проект:\*\*\s*(.+)", text)
        if m_name: proj_name = m_name.group(1).strip()
        m_stack = re.search(r"\*\*Технологический стек:\*\*\s*(.+)", text)
        if m_stack: stack = m_stack.group(1).strip()
        m_upd = re.search(r"\*\*Последнее обновление:\*\*\s*(.+)", text)
        if m_upd: last_upd = m_upd.group(1).strip()
        m_ag = re.search(r"\*\*Ответственный агент:\*\*\s*(.+)", text)
        if m_ag: curr_agent = m_ag.group(1).strip()

    # Анализ активной задачи
    active_task_title = "Нет активной задачи"
    total_steps = 0
    done_steps = 0
    if active_file.is_file():
        act_text = active_file.read_text(encoding="utf-8", errors="replace")
        m_title = re.search(r"^#\s*📋\s*Активная задача:\s*(.+)$", act_text, re.MULTILINE)
        if m_title: active_task_title = m_title.group(1).strip()
        all_boxes = re.findall(r"^\s*[-*]\s*\[([ xX])\]", act_text, re.MULTILINE)
        total_steps = len(all_boxes)
        done_steps = sum(1 for b in all_boxes if b.lower() == 'x')

    pct = int((done_steps / total_steps * 100)) if total_steps > 0 else 0
    bar_len = 20
    filled = int(bar_len * pct / 100)
    progress_bar = f"[{'█' * filled}{'░' * (bar_len - filled)}] {pct}% ({done_steps}/{total_steps})"

    # Подсчет артефактов
    plans_count = len([f for f in (AGENTS_DIR / "plans").glob("plan_*.md") if f.name != "README.md"])
    bugs_count = len([f for f in (AGENTS_DIR / "bugs_and_fixes").glob("BUG_*.md") if f.name != "README.md"])
    adrs_count = len([f for f in (AGENTS_DIR / "decisions").glob("ADR_*.md") if f.name != "README.md"])
    sessions_count = len([f for f in (AGENTS_DIR / "history").glob("*.md") if f.name != "README.md"])
    walkthroughs_count = len([f for f in (AGENTS_DIR / "walkthroughs").glob("*.md") if f.name != "README.md"])
    tasks_count = len([f for f in (AGENTS_DIR / "tasks").glob("task_*.md")])

    # Проверка плейсхолдеров
    placeholder_warn = False
    for pf in [AGENTS_DIR / "STATUS.md", AGENTS_DIR / "architecture" / "CODEBASE_MAP.md", AGENTS_DIR / "GLOSSARY.md"]:
        if pf.is_file():
            txt = pf.read_text(encoding="utf-8", errors="replace")
            if re.search(r"\{\{[A-Z_]+\}\}", txt):
                placeholder_warn = True
                break

    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║               🧠 SECOND BRAIN PROJECT DASHBOARD                      ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════╝{RESET}")

    print(f"\n{BOLD}📌 Проект:{RESET}       {BOLD}{GREEN}{proj_name}{RESET}")
    print(f"{BOLD}🛠️ Стек:{RESET}         {stack}")
    print(f"{BOLD}🕒 Обновлено:{RESET}    {last_upd}")
    print(f"{BOLD}👤 Агент:{RESET}        {curr_agent}")

    if placeholder_warn:
        print(f"\n{BOLD}{YELLOW}⚠️  Проект не инициализирован! Запустите: python agents/tools/brain.py init{RESET}")

    print(f"\n{BOLD}{BLUE}──────────────────────────────────────────────────────────────────────{RESET}")
    print(f"{BOLD}📋 Активная задача:{RESET} {YELLOW}{active_task_title}{RESET}")
    print(f"{BOLD}📊 Прогресс шагов:{RESET}  {GREEN if pct == 100 else CYAN}{progress_bar}{RESET}")

    print(f"\n{BOLD}{BLUE}──────────────────────────────────────────────────────────────────────{RESET}")
    print(f"{BOLD}📚 База знаний и артефакты:{RESET}")
    print(f"  • 📐 Планов реализации (plans/):        {BOLD}{plans_count}{RESET}")
    print(f"  • 🐛 Зафиксированных багов (bugs/):     {BOLD}{bugs_count}{RESET}")
    print(f"  • 🏛️ Архитектурных решений (ADR):      {BOLD}{adrs_count}{RESET}")
    print(f"  • 📝 Записей сессий (history/):          {BOLD}{sessions_count}{RESET}")
    print(f"  • 📋 Карточек задач (tasks/):            {BOLD}{tasks_count}{RESET}")
    print(f"  • 🚶 Walkthrough-отчётов:               {BOLD}{walkthroughs_count}{RESET}")
    print(f"{BOLD}{BLUE}──────────────────────────────────────────────────────────────────────{RESET}\n")

# -----------------------------------------------------------------------------
# sync: генерация конфигов AI-инструментов из единого канона правил
# -----------------------------------------------------------------------------

SYNC_CORE = AGENTS_DIR / "rules" / "CORE_RULES.md"
SYNC_TEMPLATES_DIR = AGENTS_DIR / "templates" / "sync"
# (шаблон-обёртка, целевой файл)
SYNC_SPECS = [
    (SYNC_TEMPLATES_DIR / "CLAUDE.md.tpl", PROJECT_ROOT / "CLAUDE.md"),
    (SYNC_TEMPLATES_DIR / ".cursorrules.tpl", PROJECT_ROOT / ".cursorrules"),
    (SYNC_TEMPLATES_DIR / ".windsurfrules.tpl", PROJECT_ROOT / ".windsurfrules"),
    (SYNC_TEMPLATES_DIR / "copilot-instructions.md.tpl", PROJECT_ROOT / ".github" / "copilot-instructions.md"),
    (SYNC_TEMPLATES_DIR / "second-brain.mdc.tpl", PROJECT_ROOT / ".cursor" / "rules" / "second-brain.mdc"),
    (SYNC_TEMPLATES_DIR / "hooks.json.tpl", PROJECT_ROOT / ".codex" / "hooks.json"),
    (SYNC_TEMPLATES_DIR / "opencode.jsonc.tpl", PROJECT_ROOT / "opencode.jsonc"),
]
# Зеркалирование скиллов между экосистемами (канон → зеркало), без подстановки {{CORE_RULES}}
# Codex читает скиллы из .agents/skills/<name>/SKILL.md, OpenCode — из .opencode/skills/<name>/SKILL.md
SYNC_MIRRORS = [
    (PROJECT_ROOT / ".claude" / "skills" / "second-brain" / "SKILL.md",
     AGENTS_DIR.parent / ".agents" / "skills" / "second_brain" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "adr-writer" / "SKILL.md",
     AGENTS_DIR.parent / ".agents" / "skills" / "adr-writer" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "bug-triage" / "SKILL.md",
     AGENTS_DIR.parent / ".agents" / "skills" / "bug-triage" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "release-checklist" / "SKILL.md",
     AGENTS_DIR.parent / ".agents" / "skills" / "release-checklist" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "session-handoff" / "SKILL.md",
     AGENTS_DIR.parent / ".agents" / "skills" / "session-handoff" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "second-brain" / "SKILL.md",
     AGENTS_DIR.parent / ".opencode" / "skills" / "second-brain" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "adr-writer" / "SKILL.md",
     AGENTS_DIR.parent / ".opencode" / "skills" / "adr-writer" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "bug-triage" / "SKILL.md",
     AGENTS_DIR.parent / ".opencode" / "skills" / "bug-triage" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "release-checklist" / "SKILL.md",
     AGENTS_DIR.parent / ".opencode" / "skills" / "release-checklist" / "SKILL.md"),
    (PROJECT_ROOT / ".claude" / "skills" / "session-handoff" / "SKILL.md",
     AGENTS_DIR.parent / ".opencode" / "skills" / "session-handoff" / "SKILL.md"),
]


# Трансформы Claude -> OpenCode: команды и агенты (тело промпта общее, $ARGUMENTS общий)
def _opencode_transform_specs():
    specs = []
    for src_dir, kind in (("commands", "command"), ("agents", "agent")):
        for src in sorted((PROJECT_ROOT / ".claude" / src_dir).glob("*.md")):
            specs.append((src, PROJECT_ROOT / ".opencode" / src_dir / src.name, kind))
    return specs


def transform_opencode_md(text: str, kind: str) -> str:
    """
    Трансформа frontmatter Claude-агента/команды в формат OpenCode V2.
    command: остаётся description (тело не трогаем — $ARGUMENTS общий с Claude).
    agent: description + mode: subagent; read-only набор инструментов -> permissions: deny edit/shell.
    Поля name/tools/model/argument-hint/allowed-tools выбрасываются (V2 deprecated/невалидно).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text  # без frontmatter — отдаём как есть
    try:
        end = 1 + lines[1:].index("---")
    except ValueError:
        return text
    fm, body = lines[1:end], "\n".join(lines[end + 1:])

    fm_lines = [l for l in fm if l.strip()]
    desc = [l for l in fm_lines if l.strip().startswith("description:")]
    out = ["---"] + desc

    if kind == "agent":
        out.append("mode: subagent")
        tools_raw = next((l.split(":", 1)[1].strip() for l in fm_lines
                          if l.strip().startswith("tools:")), "")
        toolset = {t.strip() for t in tools_raw.split(",") if t.strip()}
        can_edit = bool({"Write", "Edit", "NotebookEdit"} & toolset)
        can_shell = "Bash" in toolset
        if not can_edit or not can_shell:
            out.append("permissions:")
            if not can_edit:
                out += ["  - action: edit", '    resource: "*"', "    effect: deny"]
            if not can_shell:
                out += ["  - action: shell", '    resource: "*"', "    effect: deny"]

    out += ["---", "", body.strip(), ""]
    return "\n".join(out)


SYNC_TRANSFORMS = _opencode_transform_specs()


def _read_norm(path: Path) -> str:
    """Читает файл с нормализацией переводов строк (CRLF -> LF)."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _write_preserve_eol(path: Path, text: str):
    """Записывает файл, сохраняя стиль переводов строк существующего файла."""
    eol = "\n"
    if path.exists() and b"\r\n" in path.read_bytes():
        eol = "\r\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", eol))


def render_sync_configs():
    """Возвращает список (шаблон-источник, цель, отрендеренное содержимое)."""
    core = _read_norm(SYNC_CORE)
    rendered = []
    for tpl, target in SYNC_SPECS:
        body = _read_norm(tpl)
        rendered.append((tpl, target, body.replace("{{CORE_RULES}}", core)))
    for src, target in SYNC_MIRRORS:
        rendered.append((src, target, _read_norm(src)))
    for src, target, kind in SYNC_TRANSFORMS:
        rendered.append((src, target, transform_opencode_md(_read_norm(src), kind)))
    return rendered


def sync_tools(check: bool = False) -> int:
    """
    Генерирует конфиги AI-инструментов из agents/rules/CORE_RULES.md.
    check=True — только проверка дрейфа (exit 1 при расхождении), без записи.
    """
    if not SYNC_CORE.is_file():
        print(f"❌ Канон правил не найден: {SYNC_CORE.relative_to(PROJECT_ROOT)}")
        return 1

    drifted, written, missing = [], [], []
    for _tpl, target, content in render_sync_configs():
        rel = target.relative_to(PROJECT_ROOT)
        if not target.is_file():
            missing.append(rel)
            current = None
        else:
            current = _read_norm(target)
        if current == content:
            continue
        drifted.append(rel)
        if not check:
            _write_preserve_eol(target, content)
            written.append(rel)

    if check:
        if drifted:
            print(f"{RED}❌ sync --check: конфиги разошлись с каноном:{RESET}")
            for rel in drifted:
                print(f"   • {rel}")
            print(f"   Запусти: {GREEN}python brain.py sync{RESET}")
            return 1
        print(f"{GREEN}✅ sync --check: все {len(SYNC_SPECS)} конфигов, {len(SYNC_MIRRORS)} зеркало "
              f"и {len(SYNC_TRANSFORMS)} трансформ соответствуют канону.{RESET}")
        return 0

    if not drifted:
        print(f"{GREEN}✅ Файлы уже актуальны ({len(SYNC_SPECS)} конфигов + {len(SYNC_MIRRORS)} зеркало "
              f"+ {len(SYNC_TRANSFORMS)} трансформ), дрейф не обнаружен.{RESET}")
        return 0
    for rel in written:
        print(f"  ✓ Сгенерирован: {rel}")
    print(f"{GREEN}🎉 Синхронизировано файлов: {len(written)}. Источник: agents/rules/CORE_RULES.md + .claude/{RESET}")
    return 0

# -----------------------------------------------------------------------------
# Пресеты стека и обновление шаблонов
# -----------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lock_path(root: Path = None) -> Path:
    return (Path(root) if root else AGENTS_DIR) / ".preset_lock.json"


def _load_lock(root: Path = None) -> dict:
    lock = _lock_path(root)
    if lock.is_file():
        try:
            return json.loads(lock.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def _save_lock(lock: dict, root: Path = None):
    _lock_path(root).write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")


def list_presets() -> list:
    """Возвращает имена доступных пресетов (каталоги с preset.json)."""
    if not PRESETS_SOURCE_DIR.is_dir():
        return []
    return sorted(
        p.parent.name for p in PRESETS_SOURCE_DIR.glob("*/preset.json")
    )


def apply_preset(name: str, force: bool = False, root: Path = None) -> int:
    """
    Применяет пресет стека: копирует файлы по манифесту preset.json.
    force=False — существующие пользовательские файлы НЕ затираются.
    root — целевой проект (по умолчанию PROJECT_ROOT); нужен для тестируемости.
    Возвращает количество применённых файлов.
    """
    target_root = Path(root) if root else PROJECT_ROOT
    preset_dir = PRESETS_SOURCE_DIR / name
    manifest_path = preset_dir / "preset.json"
    if not manifest_path.is_file():
        print(f"❌ Пресет «{name}» не найден. Доступные: {', '.join(list_presets()) or 'нет'}")
        return 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lock = _load_lock(target_root / "agents")
    applied, kept = 0, 0

    for entry in manifest.get("files", []):
        src = preset_dir / entry["src"]
        if not src.is_file():
            print(f"  ⚠️  В пресете нет файла: {entry['src']}")
            continue
        dst = target_root / entry["dst"]
        if dst.exists() and not force:
            # Существующий файл не трогаем: это либо правки пользователя, либо уже
            # установленный шаблон (его обновит только brain upgrade по lock-хешу)
            kept += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        lock[entry["dst"]] = {"preset": name, "src": entry["src"], "sha256": _sha256(dst)}
        applied += 1
        print(f"  ✓ {entry['dst']}")

    _save_lock(lock, target_root / "agents")
    print(
        f"{GREEN}Пресет «{manifest.get('description', name)}»: "
        f"применено {applied}, сохранено пользовательских {kept}.{RESET}"
    )
    return applied


def upgrade_tool(root: Path = None) -> int:
    """
    Обновление шаблонов без затирания данных пользователя (brain upgrade).
    1) Синхронизирует сгенерированные конфиги (sync).
    2) Перекопирует шаблонные файлы, которые пользователь не менял
       (проверка по sha256 в agents/.preset_lock.json), обновляет lock.
    3) Ничего не делает с историей, планами, задачами, багами и правками пользователя.
    root — целевой проект (по умолчанию PROJECT_ROOT); для тестируемости.
    """
    target_root = Path(root) if root else PROJECT_ROOT
    print(f"{BOLD}⬆️  Second Brain upgrade{RESET}\n")

    print(f"{BOLD}1. Синхронизация конфигов AI-инструментов:{RESET}")
    sync_code = sync_tools(check=False) if target_root == PROJECT_ROOT else 0

    print(f"\n{BOLD}2. Обновление пресетных файлов (нетронутые пользователем):{RESET}")
    lock = _load_lock(target_root / "agents")
    updated, kept = [], []
    for dst_rel, meta in list(lock.items()):
        dst = target_root / dst_rel
        preset_dir = PRESETS_SOURCE_DIR / meta.get("preset", "")
        src = preset_dir / meta.get("src", "")  # точный источник из манифеста (в lock при установке)
        if not src.is_file():
            # fallback для старых lock-записей без src: ищем по имени файла внутри пресета
            candidates = list(preset_dir.rglob(Path(dst_rel).name)) + list(preset_dir.rglob(Path(dst_rel).name.lstrip(".")))
            src = candidates[0] if candidates else src
        if not src.is_file():
            continue
        if not dst.exists():
            shutil.copyfile(src, dst)
            updated.append(dst_rel)
        elif _sha256(dst) == meta.get("sha256"):
            shutil.copyfile(src, dst)  # пользователь не менял — безопасно обновить
            updated.append(dst_rel)
        else:
            kept.append(dst_rel)  # есть правки пользователя — не трогаем
    for rel in updated:
        lock[rel]["sha256"] = _sha256(target_root / rel)
    if updated:
        _save_lock(lock, target_root / "agents")
    print(f"  Обновлено: {len(updated)} · сохранены правки пользователя: {len(kept)}")
    for rel in kept:
        print(f"    ✋ {rel} (изменён вручную — оставлен как есть)")

    if target_root == PROJECT_ROOT:
        print(f"\n{BOLD}3. Целостность:{RESET}")
        run_integrity_check(fix=True)
    print(
        f"\n{GREEN}✅ Upgrade завершён. История/планы/задачи/баги не затронуты.{RESET}\n"
        f"Если нужно принять сохранённые правки шаблонов вручную — сравни файлы по списку ✋."
    )
    return sync_code

# -----------------------------------------------------------------------------
# Главный диспетчер
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="🧠 Second Brain Unified Management CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

    # status
    subparsers.add_parser("status", help="Показать дашборд состояния проекта")

    # plan
    plan_parser = subparsers.add_parser("plan", help="Создать новый план реализации (Plan-First)")
    plan_parser.add_argument("name", nargs="?", help="Название плана или фичи", default=None)
    plan_parser.add_argument("--task", help="ID связанной задачи", default="TASK-001")
    plan_parser.add_argument("--agent", help="Имя ответственного агента", default="AI Assistant")

    # bug
    bug_parser = subparsers.add_parser("bug", help="Зафиксировать баг-репорт в базе знаний")
    bug_parser.add_argument("title", nargs="?", help="Краткое описание ошибки", default=None)
    bug_parser.add_argument("--component", help="Компонент системы", default="Core")
    bug_parser.add_argument("--agent", help="Имя автора", default="AI Assistant")

    # adr
    adr_parser = subparsers.add_parser("adr", help="Зафиксировать архитектурное решение (ADR)")
    adr_parser.add_argument("title", nargs="?", help="Суть архитектурного решения", default=None)
    adr_parser.add_argument("--agent", help="Имя автора", default="AI Assistant")

    # task
    task_parser = subparsers.add_parser("task", help="Создать карточку задачи")
    task_parser.add_argument("title", nargs="?", help="Название задачи", default=None)
    task_parser.add_argument("--priority", help="Приоритет (HIGH/MEDIUM/LOW)", default="MEDIUM")
    task_parser.add_argument("--agent", help="Исполнитель", default="AI Assistant")

    # dump
    dump_parser = subparsers.add_parser("dump", help="Собрать контекст проекта в буфер обмена для AI-чатов")
    dump_parser.add_argument("--budget", type=int, default=None,
                             help="Лимит токенов: сжать контекст под него (автосуммаризация + отсечение низкоприоритетного)")

    # check
    check_parser = subparsers.add_parser("check", help="Запустить валидатор целостности Второго Мозга")
    check_parser.add_argument("--fix", action="store_true", help="Автоматически восстановить отсутствующие каталоги")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Сгенерировать конфиги AI-инструментов из agents/rules/CORE_RULES.md")
    sync_parser.add_argument("--check", action="store_true", help="Только проверить дрейф конфигов (exit 1 при расхождении)")

    # search
    search_parser = subparsers.add_parser("search", help="Поиск по долговременной памяти (SQLite FTS5)")
    search_parser.add_argument("query", nargs="?", help='Поисковый запрос (слова или "фраза")')
    search_parser.add_argument("--reindex", action="store_true", help="Переиндексировать память и выйти")
    search_parser.add_argument("--limit", type=int, default=10, help="Максимум результатов (по умолчанию 10)")
    search_parser.add_argument("--tag", action="append", default=[], metavar="TAG",
                               help="Фильтр по тегу frontmatter (можно несколько — И-логика)")
    search_parser.add_argument("--since", default=None, metavar="DATE",
                               help="Только записи не раньше даты (YYYY-MM-DD | YYYY-MM)")

    # claim / release / claims — блокировки задач для параллельных агентов
    claim_parser = subparsers.add_parser("claim", help="Забрать задачу (лок для параллельной работы агентов)")
    claim_parser.add_argument("task", help="ID задачи (напр. TASK-003)")
    claim_parser.add_argument("--agent", default="", help="Имя агента (по умолчанию — USER)")
    claim_parser.add_argument("--note", default="", help="Заметка о работе")
    claim_parser.add_argument("--force", action="store_true", help="Перехватить чужую/мёртвую блокировку")
    claim_parser.add_argument("--worktree", nargs="?", const=True, default=None,
                              help="Создать git worktree для задачи (опционально — путь)")

    release_parser = subparsers.add_parser("release", help="Освободить задачу")
    release_parser.add_argument("task", help="ID задачи (напр. TASK-003)")
    release_parser.add_argument("--agent", default="", help="Имя агента")
    release_parser.add_argument("--force", action="store_true", help="Снять чужую блокировку")
    release_parser.add_argument("--worktree", action="store_true", help="Удалить worktree задачи (если чистый)")

    subparsers.add_parser("claims", help="Показать активные блокировки задач")

    # stats / tour (PLAN-004)
    stats_parser = subparsers.add_parser("stats", help="Дашборд здоровья памяти")
    stats_parser.add_argument("--json", action="store_true", help="JSON-вывод для машинного чтения")
    stats_parser.add_argument("--stale-days", type=int, default=memory_stats.STALE_DAYS,
                              help="Порог устаревания записей в днях")
    tour_parser = subparsers.add_parser("tour", help="Интерактивный гид для нового пользователя")
    tour_parser.add_argument("--list", action="store_true", help="Печатать все экраны сразу (без интерактива)")

    # links (PLAN-005)
    links_parser = subparsers.add_parser("links", help="Вики-связи [[...]]: исходящие, обратные ссылки")
    links_parser.add_argument("query", nargs="?", default="", help="ID/имя записи (напр. BUG-001)")
    links_parser.add_argument("--unresolved", action="store_true", help="Все битые [[связи]] памяти")

    # presets / preset
    subparsers.add_parser("presets", help="Показать доступные пресеты стека")
    preset_parser = subparsers.add_parser("preset", help="Применить пресет стека (django-drf, aiogram-bot, fastapi, nextjs)")
    preset_parser.add_argument("name", help="Имя пресета (см. brain.py presets)")
    preset_parser.add_argument("--force", action="store_true", help="Перезаписать даже изменённые пользователем файлы")

    # upgrade
    subparsers.add_parser("upgrade", help="Обновить шаблоны и конфиги, не затирая данные пользователя")

    # end
    end_parser = subparsers.add_parser("end", help="Завершить сессию и обновить историю")
    end_parser.add_argument("--agent", help="Имя агента", default="AI Assistant")
    end_parser.add_argument("--task", help="ID задачи", default="TASK-001")
    end_parser.add_argument("--done", help="Выполненные действия (через ';')", default=None)
    end_parser.add_argument("--next", help="Инструкция для следующего агента", default=None)

    # init
    init_parser = subparsers.add_parser("init", help="Инициализировать проект (заполнить плейсхолдеры)")
    init_parser.add_argument("--name", help="Название проекта", default=None)
    init_parser.add_argument("--desc", help="Описание проекта", default=None)
    init_parser.add_argument("--stack", help="Технологический стек", default=None)
    init_parser.add_argument("--agent", help="Имя агента", default="AI Assistant")
    init_parser.add_argument("--preset", help="Сразу применить пресет стека (django-drf, aiogram-bot, fastapi, nextjs)", default=None)

    # walkthrough
    wt_parser = subparsers.add_parser("walkthrough", help="Создать Walkthrough-отчёт о демонстрации")
    wt_parser.add_argument("title", nargs="?", help="Название фичи / демо", default=None)
    wt_parser.add_argument("--plan", help="ID связанного плана", default="PLAN-001")
    wt_parser.add_argument("--task", help="ID связанной задачи", default="TASK-001")
    wt_parser.add_argument("--agent", help="Имя агента", default="AI Assistant")

    args = parser.parse_args()

    if not args.command or args.command == "status":
        show_status()
        return

    if args.command == "plan":
        name = args.name
        if not name:
            name = input("Введите название плана / фичи: ").strip()
        if not name:
            print("❌ Название не может быть пустым.")
            return
        p = create_plan(name=name, task_id=args.task, agent=args.agent)
        rel = p.relative_to(PROJECT_ROOT) if PROJECT_ROOT in p.parents else p.name
        print(f"🎉 План создан: {GREEN}{rel}{RESET}")

    elif args.command == "bug":
        title = args.title
        if not title:
            title = input("Введите краткое описание бага: ").strip()
        if not title:
            print("❌ Описание не может быть пустым.")
            return
        p = create_bug_report(title=title, component=args.component, agent=args.agent)
        rel = p.relative_to(PROJECT_ROOT) if PROJECT_ROOT in p.parents else p.name
        print(f"🐛 Баг-репорт создан: {YELLOW}{rel}{RESET}")

    elif args.command == "adr":
        title = args.title
        if not title:
            title = input("Введите название архитектурного решения: ").strip()
        if not title:
            print("❌ Название не может быть пустым.")
            return
        p = create_adr_record(title=title, agent=args.agent)
        rel = p.relative_to(PROJECT_ROOT) if PROJECT_ROOT in p.parents else p.name
        print(f"🏛️ ADR создан: {BLUE}{rel}{RESET}")

    elif args.command == "task":
        title = args.title
        if not title:
            title = input("Введите название задачи: ").strip()
        if not title:
            print("❌ Название не может быть пустым.")
            return
        p = create_task_card(title=title, priority=args.priority, agent=args.agent)
        rel = p.relative_to(PROJECT_ROOT) if PROJECT_ROOT in p.parents else p.name
        print(f"📋 Карточка задачи создана: {MAGENTA}{rel}{RESET}")

    elif args.command == "dump":
        dump = build_context_dump(root=PROJECT_ROOT, budget=args.budget)
        dump_file = SCRIPT_DIR / "context_dump.md"
        dump_file.write_text(dump, encoding="utf-8")
        copied = copy_to_clipboard(dump)
        est = estimate_tokens(dump)
        if args.budget:
            print(f"✓ Контекст сформирован под бюджет {args.budget} токенов "
                  f"(оценка ~{est}, символов {len(dump)}).")
        else:
            print(f"✓ Контекст сформирован ({len(dump)} символов, ~{est} токенов). "
                  f"Лимит: --budget N")
        if copied:
            print(f"{GREEN}🎉 Контекст скопирован в буфер обмена! Нажмите Ctrl+V в чате AI.{RESET}")
        else:
            print("Сохранено в agents/tools/context_dump.md")

    elif args.command == "check":
        run_integrity_check(fix=args.fix)

    elif args.command == "sync":
        sys.exit(sync_tools(check=args.check))

    elif args.command == "search":
        if args.reindex:
            count = memory_search.index_memory(root=PROJECT_ROOT)
            print(f"✅ Переиндексировано: {count} документов → {memory_search.INDEX_FILE.name}")
            sys.exit(0)
        if not args.query:
            print("❌ Укажи запрос: python brain.py search \"jwt timeout\"")
            sys.exit(1)
        try:
            results = memory_search.search_memory(
                args.query, limit=args.limit, root=PROJECT_ROOT,
                tags=args.tag, since=args.since,
            )
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)
        shown = args.query
        filt = []
        if args.tag:
            filt.append("теги=" + ",".join(args.tag))
        if args.since:
            filt.append(f"с {args.since}")
        if filt:
            shown += " [" + ", ".join(filt) + "]"
        print(memory_search.format_results(shown, results))
        sys.exit(0)

    elif args.command == "claim":
        ok, msg = task_locks.claim_task(
            args.task, agent=args.agent, note=args.note, force=args.force,
            worktree=args.worktree, root=PROJECT_ROOT,
        )
        print(msg)
        sys.exit(0 if ok else 1)

    elif args.command == "release":
        ok, msg = task_locks.release_task(
            args.task, agent=args.agent, force=args.force,
            remove_worktree=args.worktree, root=PROJECT_ROOT,
        )
        print(msg)
        sys.exit(0 if ok else 1)

    elif args.command == "claims":
        claims = task_locks.list_claims(root=PROJECT_ROOT)
        if not claims:
            print("Свободно: активных блокировок задач нет.")
        else:
            print(f"{BOLD}🔒 Активные блокировки задач ({len(claims)}):{RESET}")
            for c in claims:
                mark = {"active": f"{GREEN}🟢{RESET}", "stale": f"{RED}💀{RESET}",
                        "unknown": f"{YELLOW}❓{RESET}"}.get(c.get("status"), "❓")
                line = (f"  {mark} {c.get('task', '?'):<14} {c.get('agent', '?'):<16} "
                        f"PID {c.get('pid', '?')} с {c.get('created', '?')}")
                if c.get("worktree"):
                    line += f"\n       worktree: {c['worktree']}"
                if c.get("note"):
                    line += f"\n       заметка: {c['note']}"
                print(line)
            print(f"\n{GREEN}🟢{RESET} жив · {RED}💀{RESET} владелец мёртв (перехватится) · {YELLOW}❓{RESET} статус неизвестен")

    elif args.command == "stats":
        stats = memory_stats.collect_stats(root=PROJECT_ROOT, stale_days=args.stale_days)
        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            print(memory_stats.format_stats(stats))
        sys.exit(0)

    elif args.command == "tour":
        screens = TOUR_SCREENS
        if args.list or not sys.stdin.isatty():
            for i, (title, body) in enumerate(screens, 1):
                bar = "═" * 58
                print(f"\n{BOLD}{CYAN}{bar}{RESET}")
                print(f"{BOLD}{title}{RESET}")
                print(f"{CYAN}{bar}{RESET}")
                print(body)
            print()
        else:
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
        sys.exit(0)

    elif args.command == "links":
        code = memory_links.main(
            ([args.query] if args.query else []) + (["--unresolved"] if args.unresolved else [])
        )
        sys.exit(code)

    elif args.command == "presets":
        presets = list_presets()
        if not presets:
            print("Пресеты не найдены в agents/presets/.")
        else:
            print(f"{BOLD}Доступные пресеты стека:{RESET}")
            for name in presets:
                desc = ""
                manifest = PRESETS_SOURCE_DIR / name / "preset.json"
                if manifest.is_file():
                    try:
                        desc = json.loads(manifest.read_text(encoding="utf-8")).get("description", "")
                    except (OSError, ValueError):
                        pass
                print(f"  • {GREEN}{name:<14}{RESET} {desc}")
            print(f"\nПрименение: {BOLD}python brain.py preset <имя>{RESET}")

    elif args.command == "preset":
        apply_preset(args.name, force=args.force)

    elif args.command == "upgrade":
        sys.exit(upgrade_tool())

    elif args.command == "end":
        auto_done = extract_completed_tasks_from_active()
        done_items = [d.strip() for d in args.done.split(";")] if args.done else (auto_done if auto_done else ["Работы выполнены."])
        next_step = args.next or "Продолжить по плану."
        end_session(agent=args.agent, task_id=args.task, done_items=done_items, next_steps=next_step)

    elif args.command == "init":
        name = args.name
        if not name:
            try:
                default_name = PROJECT_ROOT.name if PROJECT_ROOT.name else "My Project"
                name = input(f"Название проекта [{default_name}]: ").strip() or default_name
                desc = input("Описание проекта: ").strip() or "Проект в разработке"
                stack = input("Технологический стек [Python]: ").strip() or "Python"
                agent = input(f"Имя агента [{args.agent}]: ").strip() or args.agent
            except (EOFError, KeyboardInterrupt):
                print("\nВвод прерван.")
                return
        else:
            desc = args.desc or "Проект в разработке"
            stack = args.stack or "Python"
            agent = args.agent
        init_project(name=name, desc=desc, stack=stack, agent=agent)
        if args.preset:
            print()
            apply_preset(args.preset)

    elif args.command == "walkthrough":
        title = args.title
        if not title:
            title = input("Введите название фичи / демо: ").strip()
        if not title:
            print("❌ Название не может быть пустым.")
            return
        p = create_walkthrough(title=title, plan_id=args.plan, task_id=args.task, agent=args.agent)
        rel = p.relative_to(PROJECT_ROOT) if PROJECT_ROOT in p.parents else p.name
        print(f"🚀 Walkthrough-отчёт создан: {GREEN}{rel}{RESET}")

if __name__ == "__main__":
    main()
