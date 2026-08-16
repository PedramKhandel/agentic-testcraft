"""Unit tests for the deterministic relationship graph (Stage 6)."""
from __future__ import annotations

from agentic_testcraft.graph import (
    _edge_kind,
    _resolve,
    build_name_index,
    build_relationships,
    parse_cross_refs,
)

FILE_SHA = "a" * 64


def _ref():
    return {
        "source_id": "book",
        "file_sha256": FILE_SHA,
        "markdown_start_line": 1,
        "markdown_end_line": 4,
    }


def _know(kind: str, slug: str, name: str, aliases=None):
    return {"id": f"{kind}:{slug}", "name": name, "aliases": aliases or []}


def test_build_name_index_keys_and_aliases():
    idx = build_name_index([_know("pattern", "foo", "Foo Pattern")])
    # exact, plural, and singular forms all resolve
    assert idx["foopattern"] == {"pattern:foo"}
    assert idx["foopatterns"] == {"pattern:foo"}


def test_resolve_single_match():
    idx = build_name_index([_know("smell", "bar", "Bar Smell")])
    assert _resolve("Bar Smell", idx) == {"smell:bar"}
    # plural form of the name also resolves
    assert _resolve("Bar Smells", idx) == {"smell:bar"}


def test_resolve_ambiguous_returns_multiple():
    idx = build_name_index([_know("smell", "bar", "Bar"), _know("smell", "baz", "Bar")])
    assert _resolve("Bar", idx) == {"smell:bar", "smell:baz"}


def test_parse_cross_refs_strips_page_note():
    assert parse_cross_refs("_Foo_ and _Bar_ (page 12)") == ["Foo", "Bar"]


def test_edge_kind():
    assert _edge_kind("smell", "pattern", "x") == "refactors_to"
    assert _edge_kind("pattern", "smell", "tests may lead to bugs") == "may_cause"
    assert _edge_kind("pattern", "smell", "prevents buggy tests") == "prevents"
    assert _edge_kind("pattern", "pattern", "x") == "used_with"
    assert _edge_kind("goal", "pattern", "x") == "supports"
    assert _edge_kind("principle", "smell", "x") == "supports"
    assert _edge_kind("pattern", "goal", "x") is None  # unmodelled pair


def test_build_relationships_emits_edges():
    knowledge = [
        _know("pattern", "foo", "Foo Pattern"),
        _know("smell", "bar", "Bar Smell"),
    ]
    chunks = [
        {
            "id": "pattern:foo", "kind": "pattern",
            "clean_start_line": 1, "clean_end_line": 3,
            "source_refs": [_ref()],
        },
    ]
    book_lines = ["###### Foo Pattern", "", "_Bar Smell_ is related to Foo Pattern."]
    edges = build_relationships(knowledge, chunks, book_lines)
    assert len(edges) == 1
    e = edges[0]
    assert e["from_id"] == "pattern:foo"
    assert e["to_id"] == "smell:bar"
    assert e["relationship"] == "may_cause"
    assert e["explicit"] is True
    assert e["origin"] == "book"
    assert e["source_refs"][0]["file_sha256"] == FILE_SHA


def test_build_relationships_remaps_smell_chunk_id():
    knowledge = [
        _know("smell", "bar", "Bar Smell"),
        _know("pattern", "foo", "Foo Pattern"),
    ]
    # a CODE-smell chunk referencing a pattern -> smell->pattern edge
    chunks = [
        {
            "id": "code:bar", "kind": "code",
            "clean_start_line": 1, "clean_end_line": 3,
            "source_refs": [_ref()],
        },
    ]
    book_lines = ["###### Bar", "", "Solved by _Foo Pattern_."]
    edges = build_relationships(knowledge, chunks, book_lines)
    assert len(edges) == 1
    assert edges[0]["from_id"] == "smell:bar"  # remapped from code:bar
    assert edges[0]["relationship"] == "refactors_to"


def test_build_relationships_drops_self_and_unresolved():
    knowledge = [_know("pattern", "foo", "Foo Pattern")]
    chunks = [
        {
            "id": "pattern:foo", "kind": "pattern",
            "clean_start_line": 1, "clean_end_line": 2,
            "source_refs": [_ref()],
        },
    ]
    # self-reference ("Foo Pattern") and unknown name ("ZZZ Zzz") both dropped
    book_lines = ["###### Foo Pattern", "_Foo Pattern_ and _ZZZ Zzz_"]
    edges = build_relationships(knowledge, chunks, book_lines)
    assert edges == []


def test_build_relationships_drops_ambiguous():
    knowledge = [
        _know("smell", "bar", "Bar"),
        _know("smell", "baz", "Bar"),  # same name -> ambiguous
    ]
    chunks = [
        {
            "id": "smell:bar", "kind": "smell",
            "clean_start_line": 1, "clean_end_line": 2,
            "source_refs": [_ref()],
        }
    ]
    book_lines = ["###### Bar", "refs _Bar_"]
    edges = build_relationships(knowledge, chunks, book_lines)
    assert edges == []  # ambiguous resolution is not guessed
