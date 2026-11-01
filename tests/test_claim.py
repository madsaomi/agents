#!/usr/bin/env python3
"""
Тесты блокировок задач claim/release (PLAN-003, Этап 7.1).

Локи создаются только во временных каталогах — репозиторий не затрагивается.

Запуск:  python -m unittest discover -s tests -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "tools"))

import locks  # noqa: E402


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="brain_claim_test_"))
    (root / "agents" / "tasks").mkdir(parents=True)
    return root


class TestClaimRelease(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_claim_creates_lock_and_list_sees_it(self):
        ok, msg = locks.claim_task("TASK-003", agent="agent-a", root=self.root)
        self.assertTrue(ok, msg)
        self.assertIn("закреплена", msg)

        claims = locks.list_claims(root=self.root)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["task"], "TASK-003")
        self.assertEqual(claims[0]["agent"], "agent-a")
        # heartbeat свежий → активен, даже что процесс команды уже завершился
        self.assertEqual(claims[0]["status"], "active")

    def test_lock_file_is_json_with_metadata(self):
        locks.claim_task("TASK-001", agent="a", note="работаю", root=self.root)
        path = locks.locks_dir(self.root) / "TASK-001.lock"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("task", "agent", "pid", "created", "heartbeat", "note"):
            self.assertIn(key, data)
        self.assertEqual(data["note"], "работаю")

    def test_second_agent_rejected_with_owner_name(self):
        locks.claim_task("TASK-002", agent="agent-a", root=self.root)
        ok, msg = locks.claim_task("TASK-002", agent="agent-b", root=self.root)
        self.assertFalse(ok)
        self.assertIn("agent-a", msg, "Отказ должен называть владельца")
        self.assertIn("--force", msg, "Отказ должен подсказывать перехват")
        # лок остался за первым
        self.assertEqual(locks.list_claims(root=self.root)[0]["agent"], "agent-a")

    def test_same_agent_reclaim_updates_heartbeat(self):
        locks.claim_task("TASK-002", agent="agent-a", root=self.root)
        path = locks.locks_dir(self.root) / "TASK-002.lock"
        data = json.loads(path.read_text(encoding="utf-8"))
        old = (datetime.fromisoformat(data["heartbeat"]) - timedelta(minutes=10)).isoformat()
        data["heartbeat"] = old
        path.write_text(json.dumps(data), encoding="utf-8")

        ok, msg = locks.claim_task("TASK-002", agent="agent-a", root=self.root)
        self.assertTrue(ok)
        self.assertIn("heartbeat", msg.lower())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertNotEqual(data["heartbeat"], old, "Повторный claim не обновил heartbeat")

    def test_force_takes_over(self):
        locks.claim_task("TASK-002", agent="agent-a", root=self.root)
        ok, msg = locks.claim_task("TASK-002", agent="agent-b", force=True, root=self.root)
        self.assertTrue(ok, msg)
        self.assertIn("перехвачена", msg)
        self.assertEqual(locks.list_claims(root=self.root)[0]["agent"], "agent-b")

    def test_stale_lock_taken_without_force(self):
        """Протухший лок (heartbeat старше TTL + процесс мёртв) перехватывается сам."""
        locks.locks_dir(self.root).mkdir(parents=True, exist_ok=True)
        stale_time = (
            datetime.now() - timedelta(minutes=locks._ttl_seconds() // 60 + 5)
        ).isoformat(timespec="seconds")
        path = locks.locks_dir(self.root) / "TASK-009.lock"
        path.write_text(json.dumps({
            "task": "TASK-009",
            "agent": "dead-agent",
            "pid": 2 ** 30 + 999,   # заведомо несуществующий процесс
            "created": stale_time,
            "heartbeat": stale_time,
            "note": "",
            "worktree": "",
        }), encoding="utf-8")

        self.assertEqual(locks.list_claims(root=self.root)[0]["status"], "stale")
        ok, msg = locks.claim_task("TASK-009", agent="agent-new", root=self.root)
        self.assertTrue(ok, msg)
        self.assertIn("мёртвого", msg)
        self.assertEqual(locks.list_claims(root=self.root)[0]["agent"], "agent-new")

    def test_release_own_lock(self):
        locks.claim_task("TASK-004", agent="agent-a", root=self.root)
        ok, msg = locks.release_task("TASK-004", agent="agent-a", root=self.root)
        self.assertTrue(ok, msg)
        self.assertEqual(locks.list_claims(root=self.root), [])

    def test_release_foreign_lock_requires_force(self):
        locks.claim_task("TASK-005", agent="agent-a", root=self.root)
        ok, msg = locks.release_task("TASK-005", agent="agent-b", root=self.root)
        self.assertFalse(ok)
        self.assertIn("agent-a", msg)
        self.assertEqual(len(locks.list_claims(root=self.root)), 1)

        ok, msg = locks.release_task("TASK-005", agent="agent-b", force=True, root=self.root)
        self.assertTrue(ok, msg)
        self.assertEqual(locks.list_claims(root=self.root), [])

    def test_release_unlocked_is_idempotent(self):
        ok, msg = locks.release_task("TASK-404", agent="agent-a", root=self.root)
        self.assertTrue(ok)
        self.assertIn("не заблокирована", msg)

    def test_empty_task_id_rejected(self):
        self.assertFalse(locks.claim_task("", agent="a", root=self.root)[0])
        self.assertFalse(locks.release_task("", agent="a", root=self.root)[0])

    def test_task_id_sanitized_against_path_traversal(self):
        ok, _ = locks.claim_task("../../evil", agent="a", root=self.root)
        self.assertTrue(ok)
        files = list(locks.locks_dir(self.root).glob("*.lock"))
        self.assertEqual(len(files), 1)
        # имя файла не содержит сепараторов пути
        self.assertNotIn("..", files[0].name)
        self.assertNotIn("/", files[0].name)
        self.assertNotIn("\\", files[0].name)

    def test_concurrent_claim_only_one_wins(self):
        """Атомарность O_EXCL: из двух одинаковых claim выигрывает ровно один."""
        script = (
            "import sys; sys.path.insert(0, %r); import locks; "
            "ok, msg = locks.claim_task('TASK-007', agent=sys.argv[1], root=%r); "
            "print('OK' if ok else 'DENIED'); sys.exit(0 if ok else 1)"
        ) % (str(PROJECT_ROOT / "agents" / "tools"), str(self.root))
        procs = [
            subprocess.Popen([sys.executable, "-c", script, f"agent-{i}"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for i in range(3)
        ]
        results = [p.communicate()[0].strip().splitlines()[-1] for p in procs]
        self.assertEqual(results.count("OK"), 1, f"Должен выиграть ровно один: {results}")
        self.assertEqual(len(locks.list_claims(root=self.root)), 1)


@unittest.skipUnless(shutil.which("git"), "git недоступен")
class TestWorktree(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        # минимальный git-репозиторий во временном каталоге
        for cmd in (["git", "init", "-q"],
                    ["git", "config", "user.email", "test@example.com"],
                    ["git", "config", "user.name", "test"],
                    ["git", "config", "commit.gpgsign", "false"]):
            subprocess.run(cmd, cwd=str(self.root), capture_output=True, timeout=60)
        (self.root / "README.md").write_text("init\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(self.root), capture_output=True, timeout=60)
        r = subprocess.run(["git", "commit", "-q", "-m", "init"],
                           cwd=str(self.root), capture_output=True, timeout=60)
        if r.returncode != 0:
            self.skipTest(f"git commit не прошёл: {r.stderr}")

    def test_claim_creates_worktree_and_release_removes_it(self):
        ok, msg = locks.claim_task("TASK-010", agent="agent-a", worktree=True, root=self.root)
        self.assertTrue(ok, msg)

        claims = locks.list_claims(root=self.root)
        wt = claims[0]["worktree"]
        self.assertTrue(wt, "В локе не записан путь worktree")
        self.assertTrue(Path(wt).is_dir(), "Worktree не создан")
        # ветка задачи создана
        branches = subprocess.run(["git", "branch", "--list", "task/task-010"],
                                  cwd=str(self.root), capture_output=True, text=True, timeout=60)
        self.assertIn("task/task-010", branches.stdout)

        ok, msg = locks.release_task("TASK-010", agent="agent-a", remove_worktree=True, root=self.root)
        self.assertTrue(ok, msg)
        self.assertFalse(Path(wt).exists(), "Worktree не удалён при release")
        self.assertEqual(locks.list_claims(root=self.root), [])

    def test_claim_existing_path_fails_but_keeps_semantics(self):
        busy = self.root / "occupied"
        busy.mkdir()
        ok, msg = locks.claim_task("TASK-011", agent="agent-a",
                                   worktree=str(busy), root=self.root)
        self.assertFalse(ok, "Занятый путь не должен считаться успехом")
        self.assertIn("не является worktree", msg)


if __name__ == "__main__":
    unittest.main()
