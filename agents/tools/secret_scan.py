#!/usr/bin/env python3
# secretscan: off  (файл сам содержит паттерны токенов — сканировать себя бессмысленно)
"""
Second Brain Secret Scanner (PLAN-004, Этап 1).
Ищет секреты (токены, ключи, пароли) в git-трекаемых файлах проекта.

Только stdlib. Используется:
  - секцией 11 в check_integrity (запускается в CI и в git pre-commit хуке);
  - напрямую: python agents/tools/secret_scan.py [--root PATH]

Защита от ложных срабатываний:
  - плейсхолдеры не считаются секретами: ${ENV}, {VAR}, <...>, your_..., xxx,
    changeme, placeholder, dummy, fake, redacted, значения из os.environ/getenv;
  - allowlist: .env.example, каталоги tests/, .git, __pycache__, .brain_index.db;
  - бинарники и файлы > 1 МБ пропускаются;
  - маркер `secretscan: off` в любом месте файла отключает проверку файла.
"""

import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parent.parent

# ---------------------------------------------------------------------------
# Паттерны конкретных токенов (высокая точность — только явные префиксы)
# ---------------------------------------------------------------------------
TOKEN_PATTERNS = [
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Stripe secret key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
]

# Generic-присваивания: password=..., api_key: "..." — мягче, с маской плейсхолдеров
GENERIC_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\b"
    r"\s*[:=]\s*[\"']?([^\s\"'`,;]{8,})"
)

# Значения-плейсхолдеры: не секреты
PLACEHOLDER_RES = [
    re.compile(r"^\$\{[A-Za-z0-9_]+\}$"),           # ${DATABASE_URL}
    re.compile(r"^\{[A-Za-z0-9_]+\}$"),              # {DATABASE_URL}
    re.compile(r"^\{\{.*\}\}$"),                     # {{TEMPLATE}}
    re.compile(r"^\$\{?[A-Z0-9_]+\}?\s*$"),          # $API_KEY
    # слова-маркеры: только целиком или с разделителем (иначе "AKIA..." матчится как "a...")
    re.compile(r"(?i)^(?:your|my|the|some|an?|new|change|dummy|fake|redacted|placeholder|"
               r"example|sample|changeme|not[_-]?set|none|null|n/?a|xxx+|todo|fixme)"
               r"(?:[_\-\s].*)?$"),
    re.compile(r"^<[^>]*>$"),
]
PLACEHOLDER_SUBSTRINGS = (
    "${", "<", "...", "environ", "getenv", "process.env", "your_",
    "example", "placeholder", "changeme", "insert_", "put_your",
)

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache"}
SKIP_FILES = {".env.example", ".env.sample", ".env.template"}
SKIP_SUFFIXES = {".db", ".sqlite", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
                 ".zip", ".gz", ".whl", ".exe", ".dll", ".so", ".pyc", ".lock"}
MAX_FILE_BYTES = 1_000_000
OFF_MARKER = "secretscan: off"


def _is_placeholder(value: str) -> bool:
    v = (value or "").strip().strip("\"'`")
    if len(v) < 8:
        return True
    low = v.lower()
    if any(s in low for s in PLACEHOLDER_SUBSTRINGS):
        return True
    return any(rx.match(v) for rx in PLACEHOLDER_RES)


def scan_files(paths, root: Path = None):
    """
    Сканирует переданные файлы. Возвращает список находок:
    [{file: <относительный путь>, line: <номер>, kind: <что найдено>, snippet: <маска>}]
    """
    base = Path(root) if root else DEFAULT_ROOT
    findings = []
    for path in paths:
        p = Path(path)
        if not p.is_file():
            continue
        if p.name.lower() in SKIP_FILES or p.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            continue  # бинарник или недоступен
        if OFF_MARKER in text:
            continue
        try:
            rel = p.resolve().relative_to(Path(base).resolve()).as_posix()
        except ValueError:
            rel = p.as_posix()
        # skip каталогов tests/ (фикстуры с намеренными фейковыми секретами)
        if rel.startswith("tests/") or "/tests/" in rel:
            continue

        seen_lines = set()
        for lineno, line in enumerate(text.splitlines(), 1):
            for kind, rx in TOKEN_PATTERNS:
                m = rx.search(line)
                if m and not _is_placeholder(m.group(0)):
                    findings.append({"file": rel, "line": lineno, "kind": kind,
                                     "snippet": _mask(m.group(0))})
                    seen_lines.add(lineno)
                    break
            else:
                gm = GENERIC_RE.search(line)
                if gm and lineno not in seen_lines and not _is_placeholder(gm.group(2)):
                    findings.append({"file": rel, "line": lineno,
                                     "kind": f"Generic secret ({gm.group(1)})",
                                     "snippet": _mask(gm.group(2))})
    return findings


def _mask(value: str) -> str:
    v = value.strip()
    if len(v) <= 10:
        return v[:4] + "***"
    return v[:6] + "…" + v[-4:]


def list_project_files(root: Path = None):
    """
    Git-трекаемые + неигнорируемые untracked файлы (как раз они попадают в
    ближайший коммит — основной сценарий утечки); если git недоступен —
    обход дерева (fail-soft).
    """
    base = Path(root) if root else DEFAULT_ROOT
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=str(base), capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0 and out.stdout.strip():
            return [base / line for line in out.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    files = []
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(base).parts):
            continue
        files.append(p)
    return files


def scan_project(root: Path = None):
    """Сканирует весь проект (git-трекаемые файлы). Список находок."""
    base = Path(root) if root else DEFAULT_ROOT
    return scan_files(list_project_files(root=base), root=base)


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="🔍 Поиск секретов в файлах проекта")
    parser.add_argument("--root", default=None, help="Корень проекта (по умолчанию — текущий)")
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else DEFAULT_ROOT
    findings = scan_project(root=root)
    if not findings:
        print("✅ Секретов не найдено.")
        return 0
    print(f"❌ Найдено потенциальных секретов: {len(findings)}")
    for f in findings:
        print(f"   {f['file']}:{f['line']}  {f['kind']}  ({f['snippet']})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
