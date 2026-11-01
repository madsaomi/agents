#!/usr/bin/env python3
"""
Second Brain Task Locks (claim/release) — координация параллельных агентов.

Позволяет нескольким агентам/сессиям работать над разными задачами одного
проекта без конфликтов: задача «забирается» агентом (claim), другие получают
вежливый отказ с именем владельца, освобождается командой release.

Лок — JSON-файл agents/tasks/.locks/<TASK_ID>.lock (в .gitignore, локальное
состояние). Создание атомарно (O_CREAT|O_EXCL). «Жизнь» лока определяется не
только PID: команда claim завершается сразу после вызова, поэтому активность
держится на heartbeat — повторный claim тем же агентом обновляет метку времени,
и лок активен пока возраст < BRAIN_LOCK_TTL_MINUTES (по умолчанию 45 минут).
Протухший лок (владелец мёртв и heartbeat старше TTL) перехватывается без force.

Использование:
    python agents/tools/locks.py list
    python agents/tools/locks.py claim TASK-003 --agent "MiMo" --note "..."
    python agents/tools/locks.py claim TASK-003 --agent "MiMo"   # повторно = обновить heartbeat
    python agents/tools/locks.py release TASK-003 --agent "MiMo"

Интеграция: python brain.py claim|release|claims (тот же код).
"""

import argparse
import ctypes
import json
import os
import re
import subprocess
import sys
import time
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


def locks_dir(root: Path = None) -> Path:
    return (Path(root) if root else DEFAULT_ROOT) / "agents" / "tasks" / ".locks"


def _lock_file(task_id: str, root: Path = None) -> Path:
    # без точек и сепараторов: ID вида TASK-003, всё прочее → '_'
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", task_id.strip())
    return locks_dir(root) / f"{safe}.lock"


def _pid_alive(pid) -> bool:
    """
    Жив ли процесс владельца лока.
    True/False/None (неизвестно — нет данных или нет доступа).
    На Windows os.kill(pid, 0) опасен (TerminateProcess) — используем ctypes.
    """
    if not pid:
        return None
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    if sys.platform == "win32":
        try:
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32  # noqa: SLF001
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False  # процесса нет (или нет доступа — считаем свободным)
            code = ctypes.c_ulong()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            kernel32.CloseHandle(handle)
            if not ok:
                return None
            return code.value == STILL_ACTIVE
        except Exception:
            return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # существует, но принадлежит другому пользователю
    except Exception:
        return None


def _read_lock(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _ttl_seconds() -> int:
    """TTL активности лока: BRAIN_LOCK_TTL_MINUTES (по умолчанию 45 минут)."""
    try:
        minutes = int(os.environ.get("BRAIN_LOCK_TTL_MINUTES", "45"))
    except ValueError:
        minutes = 45
    return max(1, minutes) * 60


def _age_seconds(info: dict):
    """Возраст последней активности лока (heartbeat или created) в секундах."""
    stamp = info.get("heartbeat") or info.get("created")
    if not stamp:
        return None
    try:
        created = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    return max(0.0, time.time() - created.timestamp())


def _lock_status(info: dict):
    """
    'active'  — процесс жив ИЛИ heartbeat свежий (< TTL): владелец работает;
    'stale'   — процесс мёртв и heartbeat протух: перехватывается без force;
    'unknown' — данных недостаточно (нет PID/времени).
    """
    alive = _pid_alive(info.get("pid"))
    age = _age_seconds(info)
    if alive is True:
        return "active"
    if age is not None:
        return "active" if age <= _ttl_seconds() else "stale"
    if alive is False:
        return "stale"
    return "unknown"


def claim_task(task_id: str, agent: str = "", note: str = "", force: bool = False,
               worktree: str = None, root: Path = None):
    """
    Забирает задачу на себя. Возвращает (ok: bool, message: str).
    Атомарно: лок создаётся через O_CREAT|O_EXCL — две параллельные сессии
    не смогут забрать одну задачу одновременно.
    """
    task_id = (task_id or "").strip()
    if not task_id:
        return False, "❌ Не указан ID задачи (например TASK-003)."
    agent = (agent or "").strip() or _default_agent()

    d = locks_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    path = _lock_file(task_id, root)

    now = datetime.now().isoformat(timespec="seconds")
    info = {
        "task": task_id,
        "agent": agent,
        "pid": os.getpid(),
        "created": now,
        "heartbeat": now,
        "note": (note or "").strip(),
        "worktree": "",   # путь запишется ниже, после фактического создания worktree
        "branch": "",
    }
    take_over_note = ""

    # атомарная попытка создания
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    except FileExistsError:
        current = _read_lock(path)
        status = _lock_status(current)
        same_owner = current.get("agent") == agent and status != "stale"
        if same_owner and not force:
            # повторный claim тем же агентом = обновление heartbeat (удержание лока)
            current["heartbeat"] = now
            current["pid"] = os.getpid()
            if note:
                current["note"] = note.strip()
            path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
            return True, (f"ℹ️ Задача {task_id} уже закреплена за тобой ({agent}), "
                          f"heartbeat обновлён (TTL {_ttl_seconds() // 60} мин). Продолжай работу.")
        if status == "active" and not force:
            return False, (
                f"🔒 Задача {task_id} занята агентом «{current.get('agent', '?')}» "
                f"(PID {current.get('pid', '?')}, с {current.get('created', '?')})."
                f"\n   Дождись release или перехвати явно: brain.py claim {task_id} --force"
            )
        if status == "unknown" and not force:
            return False, (
                f"🔒 Задача {task_id} заблокирована агентом «{current.get('agent', '?')}» "
                f"(PID {current.get('pid', '?')}) — статус процесса неизвестен."
                f"\n   Перехват: brain.py claim {task_id} --force"
            )
        # stale (владелец протух) или force — перехватываем
        info["note"] = info["note"] or current.get("note", "")
        if current.get("worktree") and not worktree:
            info["worktree"] = current["worktree"]   # worktree переходит вместе с задачей
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(path))
        take_over_note = (
            "перехвачена у мёртвого процесса" if status == "stale"
            else f"перехвачена у «{current.get('agent', '?')}» (--force)"
        )

    # общий путь: привязываем worktree (если просили и его ещё нет)
    wt_path = info.get("worktree") or ""
    wt_branch = info.get("branch") or ""
    if worktree and not wt_path:
        ok_wt, wt_path_new, wt_info = _git_worktree_add(worktree, task_id, root)
        if not ok_wt:
            return False, (
                f"🔒 Задача {task_id} забрана ({agent}), но worktree не создан:\n   {wt_info}\n"
                f"   Лок снят не был — освободи: brain.py release {task_id}"
            )
        wt_path, wt_branch = wt_path_new, wt_info
        info["worktree"], info["branch"] = wt_path, wt_branch
        path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    if take_over_note:
        msg = f"✅ Задача {task_id} {take_over_note}: {agent} (PID {os.getpid()})"
    else:
        msg = f"✅ Задача {task_id} закреплена: {agent} (PID {os.getpid()})"
    if note:
        msg += f"\n   Заметка: {note}"
    if wt_path:
        msg += f"\n   Worktree: {wt_path}" + (f" (ветка {wt_branch})" if wt_branch else "")
    return True, msg


def release_task(task_id: str, agent: str = "", force: bool = False,
                 remove_worktree: bool = False, root: Path = None):
    """
    Освобождает задачу. Свой лок снимает всегда, чужой — только с force
    (или если владелец-процесс мёртв).
    Возвращает (ok: bool, message: str).
    """
    task_id = (task_id or "").strip()
    if not task_id:
        return False, "❌ Не указан ID задачи."
    agent = (agent or "").strip() or _default_agent()

    path = _lock_file(task_id, root)
    if not path.is_file():
        return True, f"ℹ️ Задача {task_id} не заблокирована — освобождать нечего."

    info = _read_lock(path)
    status = _lock_status(info)
    owner = info.get("agent", "?")
    if owner != agent and status == "active" and not force:
        return False, (
            f"🔒 Задача {task_id} принадлежит «{owner}» (PID {info.get('pid', '?')}) — "
            f"снять лок может владелец или --force."
        )

    # worktree удаляем только явно и только если он чистый (безопасно)
    wt_note = ""
    wt_path = info.get("worktree") or ""
    if remove_worktree and wt_path:
        ok_wt, wt_note = _git_worktree_remove(wt_path, force, root)
        if not ok_wt:
            return False, (
                f"⚠️ Лок {task_id} НЕ снят: worktree не удаляется:\n   {wt_note}\n"
                f"   Разберись вручную или повтори с --force."
            )

    path.unlink()
    # подчищаем пустой каталог
    try:
        locks_dir(root).rmdir()
    except OSError:
        pass

    msg = f"✅ Задача {task_id} освобождена ({agent}"
    if owner != agent:
        msg += f", лок снят у «{owner}»" if force else ""
    msg += ")"
    if wt_note:
        msg += f"\n   {wt_note}"
    return True, msg


def list_claims(root: Path = None):
    """Возвращает список активных локов (dict-строки)."""
    d = locks_dir(root)
    if not d.is_dir():
        return []
    claims = []
    for f in sorted(d.glob("*.lock")):
        info = _read_lock(f)
        info["status"] = _lock_status(info)
        info["file"] = f.name
        claims.append(info)
    return claims


def _default_agent() -> str:
    """Имя агента: из переменных окружения или логина системы."""
    for var in ("BRAIN_AGENT", "USER", "USERNAME", "LOGNAME"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return "agent"


def _git(args, root: Path = None):
    return subprocess.run(
        ["git"] + args,
        cwd=str(Path(root) if root else DEFAULT_ROOT),
        capture_output=True, text=True, timeout=60,
    )


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:40] or "task"


def _git_worktree_add(worktree: str, task_id: str, root: Path = None):
    """
    Создаёт git worktree для задачи. worktree — путь, None/"" /True — тогда
    путь и ветка выводятся из ID задачи.
    Возвращает (ok, путь ИЛИ None, ветка-или-текст-ошибки).
    """
    base = Path(root) if root else DEFAULT_ROOT
    explicit = isinstance(worktree, str) and bool(worktree.strip())
    if explicit:
        wt = Path(worktree).expanduser()
    else:
        repo = base.resolve().name
        wt = base.resolve().parent / f"{repo}-{_slug(task_id)}"
    branch = f"task/{_slug(task_id)}"

    if wt.resolve() == base.resolve():
        return False, None, "worktree не может совпадать с основным каталогом"
    if wt.exists():
        # уже существующий каталог — проверим, что это worktree этого репо
        r = _git(["worktree", "list", "--porcelain"], root)
        if r.returncode == 0 and str(wt.resolve()) in r.stdout:
            return True, str(wt), branch
        return False, None, f"путь существует, но не является worktree: {wt}"
    try:
        r = _git(["worktree", "add", str(wt), "-b", branch], root)
    except Exception as e:
        return False, None, str(e)
    if r.returncode != 0:
        return False, None, (r.stderr or r.stdout or "git worktree add failed").strip()
    return True, str(wt), branch


def _git_worktree_remove(worktree: str, force: bool, root: Path = None):
    """Удаляет worktree. Без force — только если рабочее дерево чистое."""
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(worktree)
    try:
        r = _git(args, root)
    except Exception as e:
        return False, str(e)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout or "git worktree remove failed").strip()
    return True, f"worktree удалён: {worktree}"


def main() -> int:
    parser = argparse.ArgumentParser(description="🔒 Claim/Release блокировки задач (мультиагентность)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="Показать активные блокировки")

    c = sub.add_parser("claim", help="Забрать задачу")
    c.add_argument("task", help="ID задачи (TASK-XXX)")
    c.add_argument("--agent", default="", help="Имя агента (по умолчанию — USER)")
    c.add_argument("--note", default="", help="Заметка о работе")
    c.add_argument("--force", action="store_true", help="Перехватить чужую блокировку")
    c.add_argument("--worktree", nargs="?", const=True, default=None,
                   help="Создать git worktree для задачи (опционально — путь)")

    r = sub.add_parser("release", help="Освободить задачу")
    r.add_argument("task", help="ID задачи (TASK-XXX)")
    r.add_argument("--agent", default="", help="Имя агента")
    r.add_argument("--force", action="store_true", help="Снять чужую блокировку")
    r.add_argument("--worktree", action="store_true", help="Удалить worktree задачи (если чистый)")

    args = parser.parse_args()
    if args.command == "list":
        claims = list_claims()
        if not claims:
            print("Свободно: активных блокировок нет.")
            return 0
        print(f"🔒 Активные блокировки ({len(claims)}):")
        for c in claims:
            mark = {"active": "🟢", "stale": "💀", "unknown": "❓"}[c.get("status", "unknown")]
            line = f"  {mark} {c.get('task', '?'):<14} {c.get('agent', '?'):<16} PID {c.get('pid', '?')} с {c.get('created', '?')}"
            if c.get("worktree"):
                line += f"\n       worktree: {c['worktree']}"
            if c.get("note"):
                line += f"\n       заметка: {c['note']}"
            print(line)
        print("\n🟢 жив · 💀 владелец мёртв (перехватится автоматически) · ❓ статус неизвестен")
        return 0

    if args.command == "claim":
        ok, msg = claim_task(
            args.task, agent=args.agent, note=args.note, force=args.force,
            worktree=args.worktree,
        )
        print(msg)
        return 0 if ok else 1

    if args.command == "release":
        ok, msg = release_task(
            args.task, agent=args.agent, force=args.force,
            remove_worktree=args.worktree,
        )
        print(msg)
        return 0 if ok else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
