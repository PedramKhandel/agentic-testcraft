"""Stage 6 — deterministic relationship graph.

Builds (and validates) a directed, labeled graph over the extracted knowledge
nodes using signals that are **explicit in the source book**:

* italic cross-references of the form ``_Entity Name_`` / ``_Entity Name_
  (page N)`` found inside a knowledge chunk's provenance span;
* the canonical name / alias index of the extracted knowledge;
* the *kind* of the referring and referenced entities (pattern / smell /
  goal / principle).

Relationship type is chosen with a small, documented heuristic per kind pair
(see ``_edge_kind``).  All edges are labelled ``explicit=True`` with
``confidence="certain"`` because they are asserted by an italic name in the
source; the surrounding sentence is scanned only to pick ``prevents`` vs
``may_cause`` for pattern->smell edges, and this choice is recorded in the
edge's ``rationale``.

No relationship is inferred without an explicit italic name.  Edges whose
target cannot be resolved to exactly one knowledge ID are dropped (never
guessed).  The resulting ``RelationshipRecord`` list is validated by
``validate-knowledge`` (Stage 4) and a NetworkX graph is serialised.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, cast

import networkx as nx  # type: ignore[import-untyped]
from rich.console import Console

from .config import load_settings
from .extract import _remap_smell_id
from .provenance import SourceRef, read_jsonl
from .schemas import RelationshipRecord

console = Console()

_ITALIC_RX = re.compile(r"_([^_]+)_\s*(?:\(page\s*\d+\))?\s*")

# chunk `kind` -> knowledge-record id prefix.
_CHUNK_KIND_TO_KIND = {
    "code": "smell",
    "behavior": "smell",
    "project": "smell",
    "pattern": "pattern",
    "goal": "goal",
    "principle": "principle",
}


def _norm_name(name: str) -> str:
    """Collapse to a matchable key: lowercase, alnum-only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _variants(key: str) -> tuple[str, ...]:
    """Matchable keys for a record name: exact, plural, and singular forms."""
    if key.endswith("s"):
        return key, key[:-1]
    return key, key + "s"


def build_name_index(records: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Map every matchable name/alias key to the set of knowledge IDs it resolves to."""
    index: dict[str, set[str]] = {}
    for rec in records:
        rid = rec.get("id", "")
        if not rid:
            continue
        names = [rec.get("name", "")]
        names.extend(rec.get("aliases", []))
        for name in names:
            if not name:
                continue
            base = _norm_name(name)
            for v in _variants(base):
                index.setdefault(v, set()).add(rid)
    return index


def _resolve(span_text: str, index: dict[str, set[str]]) -> set[str]:
    """Return the set of knowledge IDs a candidate cross-reference resolves to."""
    key = _norm_name(span_text)
    hits: set[str] = set()
    for v in _variants(key):
        hits |= index.get(v, set())
    return hits


def parse_cross_refs(text: str) -> list[str]:
    """Return italic cross-reference spans (without the trailing page note)."""
    return [m.group(1).strip() for m in _ITALIC_RX.finditer(text)]


def _edge_kind(from_kind: str | None, to_kind: str | None, sentence: str) -> str | None:
    """Choose a relationship type from the kind pair + sentence context.

    Returns ``None`` if the pair is not modelled (edge dropped).
    """
    fk, tk = from_kind, to_kind
    # smell -> pattern: the smell is addressed by the pattern (solution pattern).
    if fk == "smell" and tk == "pattern":
        return "refactors_to"
    # pattern -> smell: may cause / may prevent depending on context.
    if fk == "pattern" and tk == "smell":
        if re.search(r"\b(prevent|avoid|reduce|eliminate|removes?|prevents)\b", sentence):
            return "prevents"
        return "may_cause"
    # pattern <-> pattern: used together (otherwise unrelated mention).
    if fk == "pattern" and tk == "pattern":
        return "used_with"
    # principle / goal -> anything they reference: they support it.
    if fk in ("goal", "principle") and tk is not None:
        return "supports"
    # pattern -> principle: the principle motivates the pattern.
    if fk == "pattern" and tk == "principle":
        return "supports"
    return None


def _sentence_for(text: str, span_start: int) -> str:
    """Best-effort sentence containing the character offset of a cross-ref."""
    start = max(0, text.rfind(" ", 0, max(0, span_start - 120)))
    end = text.find(".", span_start) + 1
    if end <= 0:
        end = text.find("\n", span_start)
    if end <= 0:
        end = span_start + 120
    return text[start:end]


def build_relationships(
    knowledge_records: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    book_lines: list[str],
) -> list[dict[str, Any]]:
    """Build explicit, source-traced relationship records from cross-references."""
    index = build_name_index(knowledge_records)
    # knowledge id -> knowledge kind (id prefix, post smell-id remap)
    kind_index = {r["id"]: r["id"].split(":", 1)[0] for r in knowledge_records}
    seen: set[tuple[str, str, str]] = set()
    edges: list[dict[str, Any]] = []

    # chunk text span keyed by chunk id
    chunk_text = {
        c["id"]: "".join(book_lines[c["clean_start_line"] - 1 : c["clean_end_line"]])
        for c in chunks
        if c.get("source_refs")
    }

    for ref in chunks:
        rid = ref["id"]
        from_id = _remap_smell_id(rid)  # chunk id may use a smell-category prefix
        text = chunk_text.get(rid, "")
        if not text:
            continue
        from_kind = _CHUNK_KIND_TO_KIND.get(ref["kind"])
        for m in _ITALIC_RX.finditer(text):
            span_text = m.group(1).strip()
            if not span_text:
                continue
            targets = _resolve(span_text, index) - {from_id}
            if len(targets) != 1:
                continue  # ambiguous or unresolved: do not guess
            to_id = next(iter(targets))
            to_kind = kind_index.get(to_id)
            rel = _edge_kind(from_kind, to_kind, _sentence_for(text, m.start()))
            if rel is None:
                continue
            key = (from_id, rel, to_id)
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                RelationshipRecord(
                    from_id=from_id,
                    relationship=cast(Any, rel),
                    to_id=to_id,
                    strength=None,
                    rationale=(
                        f"source-explicit italic cross-reference '{span_text}' "
                        f"mentions {to_id} in the {from_kind or 'entity'} chunk {rid}"
                    ),
                    source_refs=_source_refs_from(ref),
                    origin="book",
                    confidence="certain",
                    explicit=True,
                ).model_dump(exclude_none=True)
            )
    return edges


def _source_refs_from(chunk: dict[str, Any]) -> list[SourceRef]:
    return [SourceRef(**ref) for ref in chunk.get("source_refs", [])]


def build_graph(edges: list[dict[str, Any]], nodes: set[str]) -> nx.DiGraph:
    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n)
    for e in edges:
        g.add_edge(e["from_id"], e["to_id"], relationship=e["relationship"], rationales=[e.get("rationale", "")])
    return g


def _graph_stats(g: nx.DiGraph) -> dict[str, Any]:
    by_type: dict[str, int] = defaultdict(int)
    for _, _, d in g.edges(data=True):
        by_type[d.get("relationship", "unknown")] += 1
    isolated = sorted(n for n in g.nodes if g.degree(n) == 0)
    return {
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
        "density": float(nx.density(g)) if g.number_of_nodes() > 0 else 0.0,
        "relationship_counts": dict(by_type),
        "isolated_node_count": len(isolated),
        "strongly_connected_components": nx.number_strongly_connected_components(g),
        "self_loops": int(nx.number_of_selfloops(g)),
    }


def run_build_graph() -> None:
    """Stage 6 entry point: build, validate and serialise the relationship graph."""
    settings = load_settings()
    p = settings.paths
    book_lines = (p.work_dir / "book.cleaned.md").read_text(encoding="utf-8").split("\n")

    knowledge: list[dict[str, Any]] = []
    for jf in sorted(p.knowledge_book_dir.glob("*.jsonl")):
        knowledge.extend(read_jsonl(jf))
    chunks = read_jsonl(p.work_dir / "chunk-manifest.jsonl")

    edges = build_relationships(knowledge, chunks, book_lines)
    nodes = {r["id"] for r in knowledge}

    # graph checks (10.3)
    problems: list[str] = []
    for e in edges:
        if e["from_id"] == e["to_id"]:
            problems.append(f"self-edge: {e['from_id']}")
        if e["from_id"] not in nodes:
            problems.append(f"missing from_id: {e['from_id']}")
        if e["to_id"] not in nodes:
            problems.append(f"missing to_id: {e['to_id']}")
    if problems:
        console.print(f"[red]{len(problems)} graph check problem(s):[/red]")
        for p2 in problems:
            console.print(f"  - {p2}")
        raise SystemExit(1)

    g = build_graph(edges, nodes)
    stats = _graph_stats(g)

    # write relationships.jsonl
    rel_path = p.knowledge_graph_dir / "relationships.jsonl"
    rel_path.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in edges),
        encoding="utf-8",
    )
    # write graph.json (node/edge lists + stats)
    graph_json = {
        "stats": stats,
        "nodes": [{"id": n} for n in sorted(nodes)],
        "edges": [
            {"from_id": a, "to_id": b, "relationship": d.get("relationship", "")}
            for a, b, d in g.edges(data=True)
        ],
    }
    graph_path = p.knowledge_graph_dir / "graph.json"
    graph_path.write_text(json.dumps(graph_json, indent=2, sort_keys=True), encoding="utf-8")

    console.print(
        f"[green]graph built[/green]: {stats['edges']} edges across "
        f"{stats['nodes']} nodes ({stats['relationship_counts']}; "
        f"{stats['isolated_node_count']} isolated) -> {graph_path.name}"
    )
