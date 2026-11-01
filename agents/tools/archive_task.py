#!/usr/bin/env python3
"""
Архивация активной задачи (PLAN-010): `brain archive [--force]`.

Цикл: валидация чек-листа → запись карточки в tasks/archive/task_NNN_completed.md
→ сброс active_task.md в заглушку. Порядок операций гарантирует, что карточка
не потеряется (архив пишется ДО сброса активной задачи). История и существующие
архивные файлы никогда не перезаписываются (anti-pattern №2).

Только stdlib. archive_active_task() принимает root — тестируемо (урок BUG-002).
"""

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

ARCHIVE_FILE_RE = re.compile(r"^task_(\d+)_completed\.md$", re.IGNORECASE)
OPEN_ITEM_RE = re.compile(r"^\s*[-*]\s+\[ \]\s+\S", re.MULTILINE)
TASK_ID_RE = re.compile(r"TASK-(\d+)")

STUB_TEMPLATE = """# 📋 Активная задача: (не выбрана)

**Статус:** ⚪ Ожидает выбора — см. [backlog.md](backlog.md)  
**Дата:** {date}  
**Исполнитель:** —  

---

Возьми задачу из бэклога и заполни этот файл по образцу
`agents/templates/template_task.md` (Plan-First: сначала план в `agents/plans/`).
"""


def _read(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _is_stub(text: str) -> bool:
    return "не выбрана" in text.lower()


def _next_archive_number(archive_dir: Path) -> int:
    """max(существующие номера) + 1 — для карточек без TASK-ID в заголовке."""
    max_n = 0
    if archive_dir.is_dir():
        for f in archive_dir.iterdir():
            m = ARCHIVE_FILE_RE.match(f.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def archive_active_task(root=None, force: bool = False):
    """Архивировать активную задачу. Возвращает (ok, сообщение)."""
    target_root = Path(root) if root else DEFAULT_ROOT
    agents = target_root / "agents"
    active = agents / "tasks" / "active_task.md"

    text = _read(active) if active.is_file() else None
    if text is None:
        return False, "active_task.md не найден — архивировать нечего."
    if _is_stub(text):
        return False, "Активная задача не выбрана (заглушка) — архивировать нечего."

    open_items = OPEN_ITEM_RE.findall(text)
    if open_items and not force:
        return False, (f"В active_task.md остались открытые пункты ({len(open_items)}). "
                       f"Закрой их или запусти с --force.")

    archive_dir = agents / "tasks" / "archive"
    try:
        archive_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return False, f"Не удалось создать каталог архива: {e}"

    m = TASK_ID_RE.search(text[:400])  # номер из заголовка карточки (TASK-XXX)
    if m:
        number = int(m.group(1))
    else:
        number = _next_archive_number(archive_dir)
    dest = archive_dir / f"task_{number:03d}_completed.md"
    if dest.exists():
        return False, f"{dest.name} уже существует — архив не перезаписываю (anti-pattern №2)."

    try:
        dest.write_text(text, encoding="utf-8")
    except OSError as e:
        return False, f"Не удалось записать {dest.name}: {e}"

    # Архив записан — только теперь сбрасываем active_task
    try:
        active.write_text(STUB_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d")),
                          encoding="utf-8")
    except OSError as e:
        return False, f"Архив записан ({dest.name}), но сбросить active_task не удалось: {e}"

    return True, f"Задача перенесена в tasks/archive/{dest.name}, active_task.md сброшена."


def main() -> int:
    parser = argparse.ArgumentParser(description="🗄️ Архивация завершённой задачи")
    parser.add_argument("--root", default=None, help="Корень проекта")
    parser.add_argument("--force", action="store_true", help="Архивировать даже при незакрытых пунктах")
    args = parser.parse_args()
    ok, msg = archive_active_task(root=Path(args.root) if args.root else None, force=args.force)
    print(("✅ " if ok else "❌ ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
