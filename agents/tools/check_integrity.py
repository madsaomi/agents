#!/usr/bin/env python3
"""
Second Brain & Project Integrity Checker.
Универсальный скрипт проверки целостности структуры 'agents/' и проектной документации.
Не требует сторонних зависимостей (только стандартная библиотека Python).
"""

import sys
import os
import re
from pathlib import Path

# Обеспечиваем поддержку UTF-8 в консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Цвета для вывода в терминал
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Авто-определение каталогов: ищет папку agents/ рядом со скриптом или в родительском каталоге
SCRIPT_DIR = Path(__file__).resolve().parent
AGENTS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AGENTS_DIR.parent

def log_check(name: str, passed: bool, details: str = "", is_warning: bool = False):
    if passed:
        status = f"{GREEN}[OK]{RESET}"
    elif is_warning:
        status = f"{YELLOW}[WARN]{RESET}"
    else:
        status = f"{RED}[FAIL]{RESET}"
        
    print(f"  {status} {name}")
    if details and not passed:
        color = YELLOW if is_warning else RED
        print(f"       {color}--> {details}{RESET}")

def run_integrity_check():
    print(f"\n{BOLD}{CYAN}===================================================={RESET}")
    print(f"{BOLD}{CYAN}   🧠 Second Brain & Project Integrity Checker       {RESET}")
    print(f"{BOLD}{CYAN}===================================================={RESET}\n")

    errors_count = 0
    warnings_count = 0

    # 1. Проверка структуры каталогов agents/
    print(f"{BOLD}1. Проверка структуры каталогов 'agents/':{RESET}")
    required_subdirs = [
        "architecture", "bugs_and_fixes", "decisions", "deployment",
        "history", "plans", "registry", "rules", "runbooks",
        "tasks", "templates", "testing", "tools", "walkthroughs"
    ]
    for subdir in required_subdirs:
        path = AGENTS_DIR / subdir
        exists = path.is_dir()
        if not exists:
            errors_count += 1
        log_check(f"Каталог agents/{subdir}", exists, "Директория отсутствует!")

    # 2. Проверка ключевых манифестов документации
    print(f"\n{BOLD}2. Проверка ключевых манифестов и регламентов:{RESET}")
    required_manifests = [
        AGENTS_DIR / "AGENT_GUIDE.md",
        AGENTS_DIR / "STATUS.md",
        AGENTS_DIR / "GLOSSARY.md",
        AGENTS_DIR / "rules" / "AGENT_RULES.md",
        AGENTS_DIR / "rules" / "ANTI_PATTERNS.md",
        AGENTS_DIR / "rules" / "CODING_STANDARDS.md",
        AGENTS_DIR / "rules" / "ONBOARDING_PROTOCOL.md",
    ]
    for mf in required_manifests:
        exists = mf.is_file() and mf.stat().st_size > 50
        if not exists:
            errors_count += 1
        rel_path = mf.relative_to(PROJECT_ROOT) if PROJECT_ROOT in mf.parents else mf.name
        log_check(f"Манифест {rel_path}", exists, "Файл отсутствует или пуст")

    # Проверка корневого AGENTS.md
    root_agents_md = PROJECT_ROOT / "AGENTS.md"
    root_exists = root_agents_md.is_file()
    if not root_exists:
        warnings_count += 1
        log_check("Корневой AGENTS.md в корне проекта", False, "Рекомендуется создать AGENTS.md в корне для IDE/AI", is_warning=True)
    else:
        log_check("Корневой AGENTS.md в корне проекта", True)

    # 3. Проверка шаблонов (templates/)
    print(f"\n{BOLD}3. Проверка бланков шаблонов (agents/templates/):{RESET}")
    required_templates = [
        "template_session_log.md",
        "template_bug_report.md",
        "template_task.md",
        "template_adr.md",
        "template_component_spec.md"
    ]
    for tpl in required_templates:
        p = AGENTS_DIR / "templates" / tpl
        exists = p.is_file() and p.stat().st_size > 50
        if not exists:
            errors_count += 1
        log_check(f"Шаблон {tpl}", exists, "Шаблон отсутствует!")

    # 4. Проверка управления задачами (tasks/)
    print(f"\n{BOLD}4. Проверка подсистемы задач (agents/tasks/):{RESET}")
    active_task = AGENTS_DIR / "tasks" / "active_task.md"
    backlog = AGENTS_DIR / "tasks" / "backlog.md"
    
    has_active = active_task.is_file() and active_task.stat().st_size > 50
    if not has_active:
        errors_count += 1
    log_check("Активная задача (active_task.md)", has_active, "Файл active_task.md отсутствует!")

    has_backlog = backlog.is_file() and backlog.stat().st_size > 50
    if not has_backlog:
        errors_count += 1
    log_check("Бэклог задач (backlog.md)", has_backlog, "Файл backlog.md отсутствует!")

    # 5. Проверка непрерывной истории (history/)
    print(f"\n{BOLD}5. Проверка журнала истории (agents/history/):{RESET}")
    history_files = [f for f in (AGENTS_DIR / "history").glob("*.md") if f.name != "README.md"]
    has_history = len(history_files) > 0
    if not has_history:
        warnings_count += 1
        log_check("Наличие записей сессий в history/", False, "В папке history/ нет ни одной записи сессии", is_warning=True)
    else:
        log_check(f"Записей сессий в history/: {len(history_files)}", True)

    # 6. Проверка на незаполненные плейсхолдеры
    print(f"\n{BOLD}6. Проверка инициализации проекта (наличие плейсхолдеров):{RESET}")
    status_file = AGENTS_DIR / "STATUS.md"
    if status_file.is_file():
        content = status_file.read_text(encoding="utf-8", errors="replace")
        placeholders_found = re.findall(r"\{\{([A-Z_]+)\}\}", content)
        if placeholders_found:
            warnings_count += 1
            log_check(
                "Персонализация проекта", 
                False, 
                f"Обнаружены незаполненные плейсхолдеры в STATUS.md: {set(placeholders_found)}. Запустите: python agents/tools/init_project.py",
                is_warning=True
            )
        else:
            log_check("Персонализация проекта (плейсхолдеры заполнены)", True)

    # Итоговый вывод
    print(f"\n{BOLD}{CYAN}===================================================={RESET}")
    if errors_count == 0:
        if warnings_count > 0:
            print(f"{BOLD}{YELLOW}  ⚠️ ВТОРОЙ МОЗГ РАБОТОСПОСОБЕН! (Ошибок: 0, Предупреждений: {warnings_count}) {RESET}")
        else:
            print(f"{BOLD}{GREEN}  🎉 ИТОГ: ВСЕ СИСТЕМЫ И ВТОРОЙ МОЗГ В 100% ПОРЯДКЕ! {RESET}")
        print(f"{BOLD}{CYAN}===================================================={RESET}\n")
        return 0
    else:
        print(f"{BOLD}{RED}  ❌ ИТОГ: НАЙДЕНО КРИТИЧЕСКИХ ОШИБОК: {errors_count} (Предупреждений: {warnings_count}) {RESET}")
        print(f"{BOLD}{CYAN}===================================================={RESET}\n")
        return 1

if __name__ == "__main__":
    code = run_integrity_check()
    sys.exit(code)
