#!/usr/bin/env python3
# links.py — вики-связи памяти [[...]] (PLAN-005, Этап 1).
#
# Извлекает ссылки вида [[BUG-001]], [[plan_003|план]], [[ADR-001#якорь]]
# из markdown-файлов памяти (agents/) и резолвит их по карте файлов:
#   - по basename файла (BUG_001.md, plan_003_executable_rules.md)
#   - по stem (имя без .md)
#   - по «чистому» ID: нормализация регистра и разделителей (-/_),
#     т.е. [[BUG-001]] находит файл BUG_001.md и наоборот
#
# Неразрешёнными считаются только цели-идентификаторы ([A-Za-z0-9_-]+
# с опциональным .md). «Плейсхолдеры» (точки, пробелы, [[...]]) — не ошибки.
#
# Всё читается на лету, без БД и git (fail-soft). Только stdlib.

import re
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

# [[цель]] | [[цель|подпись]] | [[цель#якорь]]
WIKI_RE = re.compile(r"\[\[([^\[\]\n]{1,120}?)\]\]")

# Разделители, которые нужно проигнорировать при резолюции (ID-нормализация)
_SEP_RE = re.compile(r"[\s\-_./]+")

MEMORY_SECTIONS = ("plans", "tasks", "history", "bugs_and_fixes",
                   "decisions", "walkthroughs")


# ---------------------------------------------------------------------------
# Карта файлов памяти
# ---------------------------------------------------------------------------

def _memory_files(root: Path):
    """Все .md памяти кроме README (секции agents/). Список путей."""
    agents = root / "agents"
    files = []
    for section in MEMORY_SECTIONS:
        d = agents / section
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*.md")):
            if f.name.lower() == "readme.md":
                continue
            files.append(f)
    return files


def build_index(root: Path = None) -> dict:
    """
    Индекс резолюции: ключ -> относительный путь (posix).
    Ключи: basename файла, stem, нормализованные формы обоих
    (регистр и -/_ неважны: bug001 <-> bug_001).
    """
    base = Path(root) if root else DEFAULT_ROOT
    index = {}
    for f in _memory_files(base):
        try:
            rel = f.relative_to(base).as_posix()
        except ValueError:
            rel = f.as_posix()
        for key in (f.name, f.stem):
            index[key] = rel
            index[_norm(key)] = rel
    return index


def _norm(value: str) -> str:
    """Нормализация для регистр/разделитель-инвариантного сравнения."""
    return _SEP_RE.sub("", (value or "")).lower()


def _is_placeholder(target: str) -> bool:
    """
    [[...]], [[bug#1]], [[файл с пробелом]] — плейсхолдеры/примеры в
    документации, не битые связи. Валидная цель — идентификатор.
    """
    t = (target or "").strip()
    if not t or t == "...":
        return True
    # валидная цель: идентификатор (+ опц. .md); всё остальное — пропуск.
    # короче 4 символов — тоже плейсхолдер ([[bug#1]] -> "bug" и т.п.),
    # реальные ID (BUG-001, PLAN-005, ADR-001) длиннее
    if not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.md)?", t):
        return True
    base = t[:-3] if t.lower().endswith(".md") else t
    return len(base) < 4


# ---------------------------------------------------------------------------
# Извлечение и резолюция
# ---------------------------------------------------------------------------

def _split_target(raw: str):
    """'plan_003|Мой план' -> ('plan_003', 'Мой план'); 'ADR-001#секция' -> ('ADR-001', None, 'секция')."""
    target = raw.strip()
    label = None
    if "|" in target:
        target, label = target.split("|", 1)
        target, label = target.strip(), label.strip()
    anchor = None
    if "#" in target:
        target, _, anchor = target.partition("#")
        target, anchor = target.strip(), anchor.strip()
    return target, label, anchor


def find_links(root: Path = None) -> list:
    """
    Все вики-связи памяти. Список dict:
    {src, line, raw, target, label, dst (rel-путь | None), placeholder: bool}
    """
    base = Path(root) if root else DEFAULT_ROOT
    index = build_index(base)
    results = []
    for f in _memory_files(base):
        try:
            rel = f.relative_to(base).as_posix()
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            for m in WIKI_RE.finditer(line):
                raw = m.group(1)
                target, label, _anchor = _split_target(raw)
                if _is_placeholder(target):
                    results.append({
                        "src": rel, "line": lineno, "raw": f"[[{raw}]]",
                        "target": target, "label": label,
                        "dst": None, "placeholder": True,
                    })
                    continue
                dst = _resolve(target, index)
                results.append({
                    "src": rel, "line": lineno, "raw": f"[[{raw}]]",
                    "target": target, "label": label,
                    "dst": dst, "placeholder": False,
                })
    return results


def _resolve(target: str, index: dict):
    """
    Резолв цели по карте. Путь или None.
    1) точное совпадение basename/stem; 2) нормализованное (регистр, -/_);
    3) префикс по ID: [[BUG-001]] -> файл BUG_001_subagent_....md
       (однозначный префикс; при нескольких кандидатах — самый короткий stem).
    """
    if target in index:
        return index[target]
    stem = target[:-3] if target.lower().endswith(".md") else target
    if stem in index:
        return index[stem]
    n = _norm(target)
    if n in index:
        return index[n]
    n_stem = _norm(stem)
    if n_stem in index:
        return index[n_stem]
    # Префиксный поиск по ID среди нормализованных stem
    if n_stem:
        candidates = {key: path for key, path in index.items()
                      if not _SEP_RE.search(key) and key.startswith(n_stem)
                      and key != n_stem}
        if candidates:
            paths = sorted(set(candidates.values()),
                           key=lambda p: len(Path(p).stem))
            return paths[0]
    return None


def links_for(root: Path = None, query: str = "") -> dict:
    """
    Связи для запроса (ID, имя файла или stem). Показывает:
    исходящие, входящие (обратные ссылки), неразрешённые цели
    (только валидные идентификаторы — плейсхолдеры не считаются).
    """
    base = Path(root) if root else DEFAULT_ROOT
    all_links = find_links(base)

    # Файл-цель запроса (может быть относительным путём)
    index = build_index(base)
    q = (query or "").strip()
    dst_q = _resolve(q, index)
    if dst_q is None and q:
        # запрос сам по себе — путь к файлу памяти?
        cand = (base / q)
        if cand.is_file():
            try:
                dst_q = cand.relative_to(base).as_posix()
            except ValueError:
                dst_q = cand.as_posix()

    outgoing, incoming, unresolved = [], [], []
    for link in all_links:
        if link["placeholder"]:
            continue
        if dst_q is not None:
            if link["src"] == dst_q:
                outgoing.append(link)
            if link["dst"] == dst_q:
                incoming.append(link)
        if link["dst"] is None:
            unresolved.append(link)
    return {
        "query": q,
        "file": dst_q,
        "outgoing": outgoing,
        "incoming": incoming,
        "unresolved": unresolved,
        "total": sum(1 for l in all_links if not l["placeholder"]),
        "placeholders": sum(1 for l in all_links if l["placeholder"]),
    }


def unresolved_links(root: Path = None) -> list:
    """Все битые [[связи]] памяти (валидные цели без файла)."""
    return [l for l in find_links(root)
            if not l["placeholder"] and l["dst"] is None]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _show(title: str, items: list):
    print(f"\n{title} ({len(items)}):")
    if not items:
        print("   —")
        return
    for l in items:
        if l["dst"]:
            print(f"   {l['src']}:{l['line']}  {l['raw']} → {l['dst']}")
        else:
            print(f"   {l['src']}:{l['line']}  {l['raw']} ⚠️ не разрешено")


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="🔗 Вики-связи памяти [[...]] и обратные ссылки")
    parser.add_argument("query", nargs="?", default="",
                        help="ID/имя записи (напр. BUG-001, plan_003)")
    parser.add_argument("--unresolved", action="store_true",
                        help="Показать все битые [[связи]] памяти")
    parser.add_argument("--root", default=None, help="Корень проекта")
    args = parser.parse_args(argv)

    base = Path(args.root) if args.root else DEFAULT_ROOT
    exit_code = 0

    # Режим 1: --unresolved (битые связи всей памяти)
    if args.unresolved:
        broken = unresolved_links(base)
        if broken:
            print(f"❌ Битые [[связи]]: {len(broken)}")
            for l in broken:
                print(f"   {l['src']}:{l['line']}  {l['raw']}")
            exit_code = 1
        else:
            print("✅ Битых [[связей]] нет.")

    # Режим 2: запрос по записи
    if args.query:
        r = links_for(base, args.query)
        if r["file"] is None:
            if not args.unresolved:
                print(f"❓ Запись не найдена: {r['query']!r} "
                      f"(попробуй --unresolved или уточни ID)")
            # битые связи с такой целью — опечатки в ссылках
            hits = [l for l in r["unresolved"]
                    if _norm(l["target"]) == _norm(r["query"])]
            if hits:
                print("   Но есть битые связи с такой целью:")
                for l in hits:
                    print(f"   {l['src']}:{l['line']}  {l['raw']}")
            exit_code = 1 if not args.unresolved else exit_code
        else:
            if args.unresolved:
                print()
            print(f"🔗 Связи для {r['file']}:")
            _show("➡️ Исходящие", r["outgoing"])
            _show("⬅️ Обратные ссылки (backlinks)", r["incoming"])
            _show("⚠️ Неразрешённые (из этих файлов)", r["unresolved"])

    # Режим 3: без аргументов — краткая сводка
    if not args.query and not args.unresolved:
        r = links_for(base, "")
        print(f"🔗 Связи памяти: {r['total']} разрешённых, "
              f"{r['placeholders']} плейсхолдеров, "
              f"{len(r['unresolved'])} битых.")
        print("   Использование: python brain.py links <ID> | --unresolved")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
