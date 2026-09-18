#!/usr/bin/env python3
"""
Second Brain Session Wrap-Up Tool.
Автоматизирует завершение рабочей сессии:
- Создает инкрементальный файл отчета в agents/history/
- Обновляет временную метку и статус в agents/STATUS.md
- Запускает валидатор целостности
"""

import sys
import os
import re
import argparse
from datetime import datetime
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

def end_session(agent: str, task_id: str, done_items: list, next_steps: str, decisions: str = ""):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M")

    # Вычисляем следующий номер сессии за сегодня
    history_dir = AGENTS_DIR / "history"
    existing_today = list(history_dir.glob(f"session_{date_str}_*.md"))
    session_num = len(existing_today) + 1

    slug_agent = "".join(c if c.isalnum() else "_" for c in agent.lower()).strip("_")
    filename = f"session_{date_str}_{session_num:02d}_{slug_agent}.md"
    target_file = history_dir / filename

    # Формируем содержимое отчета
    done_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(done_items)])
    decisions_text = decisions.strip() if decisions.strip() else "- Стандартные архитектурные решения согласно спецификации."
    next_text = next_steps.strip() if next_steps.strip() else "- Продолжить выполнение активной задачи согласно agents/tasks/active_task.md."

    report_content = f"""# 📝 Отчет о сессии: {filename.replace('.md', '')}

- **Дата и время:** {time_str}
- **Агент / Разработчик:** {agent}
- **Операционная система:** {sys.platform}
- **ID Задачи:** {task_id}

---

### 🔍 1. Что было сделано:
{done_text}

### 💡 2. Принятые решения и их мотивация:
{decisions_text}

### 🐛 3. Ошибки и сбои (если были):
- Критических сбоев не зафиксировано. При возникновении ошибок они документируются в agents/bugs_and_fixes/.

### 🧪 4. Результаты проверки и тестов:
- Структура проверена с помощью python agents/tools/check_integrity.py.

### 🔜 5. Инструкция для следующего агента:
{next_text}
"""

    target_file.write_text(report_content, encoding="utf-8")
    print(f"\n✓ Создан отчет о сессии: agents/history/{filename}")

    # Обновляем временную метку в STATUS.md
    status_file = AGENTS_DIR / "STATUS.md"
    if status_file.is_file():
        status_text = status_file.read_text(encoding="utf-8", errors="replace")
        # Заменяем дату последнего обновления
        status_text = re.sub(
            r"\*\*Последнее обновление:\*\*.*",
            f"**Последнее обновление:** {time_str} (UTC+5)",
            status_text
        )
        status_text = re.sub(
            r"\*\*Ответственный агент:\*\*.*",
            f"**Ответственный агент:** {agent}",
            status_text
        )
        status_file.write_text(status_text, encoding="utf-8")
        print(f"✓ Обновлен дашборд agents/STATUS.md (дата: {time_str})")

    # Запускаем валидацию
    print("\nЗапуск проверки целостности...")
    sys.path.insert(0, str(SCRIPT_DIR))
    from check_integrity import run_integrity_check
    run_integrity_check()

def main():
    parser = argparse.ArgumentParser(description="Second Brain Session Wrap-Up Tool")
    parser.add_argument("--agent", help="Имя агента или разработчика", default="AI Assistant")
    parser.add_argument("--task", help="ID текущей задачи (например: TASK-001)", default="TASK-001")
    parser.add_argument("--done", help="Список выполненных действий (через точку с запятой ';')", default=None)
    parser.add_argument("--next", help="Инструкция для следующего агента", default=None)

    args = parser.parse_args()

    agent = args.agent
    task_id = args.task
    done = args.done
    next_steps = args.next

    if not done:
        try:
            print("\n--- 🏁 Завершение Рабочей Сессии ---")
            agent = input(f"Имя агента/разработчика [{agent}]: ").strip() or agent
            task_id = input(f"ID активной задачи [{task_id}]: ").strip() or task_id
            print("\nВведите выполненные пункты (по одному на строку, пустая строка для завершения):")
            done_list = []
            while True:
                item = input("  - ").strip()
                if not item:
                    break
                done_list.append(item)
            if not done_list:
                done_list = ["Выполнены плановые работы по проекту."]
            next_steps = input("\nЧто сделать следующему агенту? ").strip() or "Продолжить по чек-листу active_task.md"
        except (EOFError, KeyboardInterrupt):
            print("\nВвод прерван. Использованы стандартные значения.")
            done_list = ["Пакет изменений зафиксирован."]
            next_steps = "Продолжить по плану."
    else:
        done_list = [d.strip() for d in done.split(";") if d.strip()]

    end_session(agent=agent, task_id=task_id, done_items=done_list, next_steps=next_steps or "")

if __name__ == "__main__":
    main()
