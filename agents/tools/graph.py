#!/usr/bin/env python3
"""
Second Brain Graph (PLAN-012 / TASK-011): mermaid-визуализация вики-связей.
Узлы — записи памяти, сплошные рёбра — разрешённые [[связи]], пунктирные —
битые (цель не резолвится, рисуется фантомный узел ⚠️).

Переиспользует публичный API links.py (find_links / build_index) — резолюция
не дублируется. Лимит узлов — по степени связности (--max, default 40).

Использование:
    python agents/tools/graph.py [--json] [--max N] [--root PATH]
    python brain.py graph [--json] [--max N]     # через диспетчер

Только stdlib. collect_graph() принимает root — тестируемо (урок BUG-002).
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

MAX_NODES_DEFAULT = 40
MAX_PHANTOMS = 10

SECTION_EMOJI = {
    "plans": "📐",
    "bugs_and_fixes": "🐛",
    "decisions": "🏛️",
    "tasks": "📋",
    "history": "📝",
    "walkthroughs": "🚀",
    "rules": "📜",
}
FALLBACK_EMOJI = "📄"


def _parse_section(rel: str) -> str:
    """Раздел памяти из rel-пути links.py: 'agents/<раздел>/<файл>' → '<раздел>'."""
    parts = rel.split("/")
    if parts and parts[0] == "agents":
        parts = parts[1:]
    return parts[0] if len(parts) > 1 else ""


def collect_graph(root=None) -> dict:
    """Собрать узлы/рёбра/битые связи. rel-пути — относительно agents/ (как в links.py)."""
    target_root = Path(root) if root else DEFAULT_ROOT
    import links as memory_links

    index = memory_links.build_index(target_root)
    all_links = memory_links.find_links(target_root)

    nodes = {}
    for rel in sorted(set(index.values())):
        stem = Path(rel).stem
        nodes[rel] = {"label": stem, "section": _parse_section(rel)}

    edge_counter = Counter()
    unresolved = []
    for link in all_links:
        if link["placeholder"]:
            continue
        src, dst = link["src"], link["dst"]
        if dst is None:
            unresolved.append({"src": src, "target": link["target"]})
        elif src != dst:  # self-ссылки в графе — шум
            edge_counter[(src, dst)] += 1

    edges = [{"src": s, "dst": d, "count": n} for (s, d), n in sorted(edge_counter.items())]
    return {
        "root": str(target_root),
        "nodes": nodes,
        "edges": edges,
        "unresolved": unresolved,
        "summary": {"nodes": len(nodes), "edges": len(edges), "unresolved": len(unresolved)},
    }


def _degree(graph: dict) -> Counter:
    """Степень узла: входящие + исходящие + источники битых связей."""
    deg = Counter()
    for e in graph["edges"]:
        deg[e["src"]] += 1
        deg[e["dst"]] += 1
    for u in graph["unresolved"]:
        deg[u["src"]] += 1
    return deg


def _node_label(node: dict) -> str:
    emoji = SECTION_EMOJI.get(node.get("section", ""), FALLBACK_EMOJI)
    return f"{emoji} {node['label']}"


def render_mermaid(graph: dict, max_nodes: int = MAX_NODES_DEFAULT) -> str:
    """Mermaid-блок: топ-N узлов по степени, рёбра -->, битые -.-> на фантомы."""
    degree = _degree(graph)
    nodes = graph["nodes"]
    shown = sorted(nodes, key=lambda rel: (-degree.get(rel, 0), rel))[:max(1, max_nodes)]
    shown_set = set(shown)

    ids = {rel: f"m{i}" for i, rel in enumerate(shown)}
    lines = ["graph TD"]
    for rel in shown:
        lines.append(f'    {ids[rel]}["{_node_label(nodes[rel])}"]')

    for e in graph["edges"]:
        if e["src"] in shown_set and e["dst"] in shown_set:
            arrow = "-->" if e["count"] == 1 else f"-- {e['count']}x -->"
            lines.append(f"    {ids[e['src']]} {arrow} {ids[e['dst']]}")

    # Битые связи: пунктир на фантомный узел (цель не резолвится)
    phantoms = {}
    phantom_lines = []
    for u in graph["unresolved"][:MAX_PHANTOMS]:
        if u["src"] not in shown_set:
            continue
        pid = phantoms.setdefault(u["target"], f"p{len(phantoms)}")
        phantom_lines.append(f'    {ids[u["src"]]} -.-> {pid}["⚠️ {u["target"]}"]')
    lines.extend(phantom_lines)

    hidden = len(nodes) - len(shown)
    if hidden > 0:
        lines.append(f"    %% …и ещё {hidden} узлов вне лимита --max {max_nodes}")
    return "```mermaid\n" + "\n".join(lines) + "\n```"


def format_summary(graph: dict, max_nodes: int = MAX_NODES_DEFAULT) -> str:
    s = graph["summary"]
    return (f"📊 Узлов: {s['nodes']}, рёбер: {s['edges']}, битых связей: {s['unresolved']} "
            f"(показано узлов: {min(s['nodes'], max_nodes)}). Вставь блок в любой mermaid-рендер.")


def main() -> int:
    parser = argparse.ArgumentParser(description="🕸️ Mermaid-граф вики-связей памяти")
    parser.add_argument("--json", action="store_true", help="Вывести собранный граф в JSON")
    parser.add_argument("--max", type=int, default=MAX_NODES_DEFAULT,
                        help=f"Лимит узлов (по степени связности, default {MAX_NODES_DEFAULT})")
    parser.add_argument("--root", default=None, help="Корень проекта")
    args = parser.parse_args()
    graph = collect_graph(root=Path(args.root) if args.root else None)
    if args.json:
        print(json.dumps(graph, ensure_ascii=False, indent=2))
    else:
        print(render_mermaid(graph, max_nodes=args.max))
        print(format_summary(graph, max_nodes=args.max))
    return 0


if __name__ == "__main__":
    sys.exit(main())
