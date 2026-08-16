"""Unit tests for semantic heading parsing and chunking (synthetic fixtures)."""
from __future__ import annotations

from agentic_testcraft.chunk import LineMap, slugify
from agentic_testcraft.structure import (
    _is_subsection,
    build_chunks,
    parse_headings,
)

# A pattern chapter that mirrors the real book's catalog table shape:
# an H5 chapter title, a "Patterns in This Chapter" catalog table, then H6
# entity definitions interleaved with subsection H6s (How It Works, etc.).
SYNTHETIC = """\
##### xUnit Basics Patterns

###### About This Chapter

Intro text.

###### Patterns in This Chapter

|Assertion Method . . . . . . . . . . . . . . . . . . . . . . . . . . . . 1|
|---|
|Conditional Test Logic . . . . . . . . . . . . . . . . . . . . . . . . . 2|

###### Assertion Method

Body of Assertion Method.

###### How It Works

We encode the expected outcome.

###### Conditional Test Logic

Body of Conditional Test Logic.

###### Symptoms

- it is hard
"""

NARRATIVE = """\
##### A Short Guide

Some prose.

###### How It Works

This is a subsection, not an entity.
"""

FILE_SHA = "a" * 64


def make_linemap(text: str) -> LineMap:
    """Build a line map as if every clean line == source line 1:1."""
    lines = text.split("\n")
    return LineMap(entries=[{"clean_line": i, "source_lines": [i], "transformations": []} for i in range(1, len(lines) + 1)])


def test_slugify_stable():
    assert slugify("Obscure Test") == "obscure-test"
    assert slugify("Test-Driven Development") == "test-driven-development"
    assert slugify("  A & B?  ") == "a-b"


def test_parse_headings_levels():
    hs = parse_headings(SYNTHETIC.split("\n"))
    levels = [(h.level, h.text) for h in hs]
    assert (5, "xUnit Basics Patterns") in levels
    assert (6, "Assertion Method") in levels
    assert (6, "How It Works") in levels


def test_subsection_detection():
    assert _is_subsection("How It Works") is True
    assert _is_subsection("Variation: Test Stub") is True
    assert _is_subsection("Example: Foo") is True
    assert _is_subsection("Assertion Method") is False
    assert _is_subsection("Patterns in This Chapter") is True


def test_build_chunks_creates_entities_not_subsections():
    lines = SYNTHETIC.split("\n")
    lm = make_linemap("\n".join(lines))
    chunks, problems = build_chunks(lines, lm, FILE_SHA)
    titles = [c.title for c in chunks]
    kinds = {c.id for c in chunks}
    # Catalog-driven: one entity per catalog entry anchored at an H6.
    assert "pattern:assertion-method" in kinds
    assert "pattern:conditional-test-logic" in kinds
    assert "Assertion Method" in titles
    assert "Conditional Test Logic" in titles
    # Subsections and the catalog heading itself are NOT entities.
    assert not any(c.title == "How It Works" for c in chunks)
    assert not any(c.title == "Symptoms" for c in chunks)
    assert not any(c.title == "Patterns in This Chapter" for c in chunks)
    assert problems == []


def test_build_chunks_records_subsections():
    lines = SYNTHETIC.split("\n")
    lm = make_linemap("\n".join(lines))
    chunks, _ = build_chunks(lines, lm, FILE_SHA)
    am = next(c for c in chunks if c.title == "Assertion Method")
    assert "How It Works" in am.subsections
    assert "Conditional Test Logic" not in am.subsections


def test_build_chunks_provenance_line_ranges():
    lines = SYNTHETIC.split("\n")
    lm = make_linemap("\n".join(lines))
    chunks, _ = build_chunks(lines, lm, FILE_SHA)
    am = next(c for c in chunks if c.title == "Assertion Method")
    assert am.source_start_line is not None
    assert am.source_end_line is not None
    assert am.source_end_line >= am.source_start_line


def test_build_chunks_record_has_source_ref():
    lines = SYNTHETIC.split("\n")
    lm = make_linemap("\n".join(lines))
    chunks, _ = build_chunks(lines, lm, FILE_SHA)
    rec = chunks[0].to_record(FILE_SHA)
    assert rec["source_refs"][0]["file_sha256"] == FILE_SHA
    assert rec["source_refs"][0]["markdown_start_line"] is not None


def test_no_duplicate_ids():
    lines = SYNTHETIC.split("\n")
    lm = make_linemap("\n".join(lines))
    chunks, problems = build_chunks(lines, lm, FILE_SHA)
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))
    assert problems == []


def test_narrative_chapter_collapses_to_single_chunk():
    lines = NARRATIVE.split("\n")
    lm = make_linemap("\n".join(lines))
    chunks, problems = build_chunks(lines, lm, FILE_SHA)
    assert len(chunks) == 1
    assert chunks[0].title == "A Short Guide"
    assert chunks[0].id == "narrative:a-short-guide"
    # A subsection H6 is absorbed into the chapter span, not a separate entity.
    assert not any(c.title == "How It Works" for c in chunks)
    assert problems == []


CATALOG_WITH_MISSING = """\
##### xUnit Basics Patterns

###### Patterns in This Chapter

|Assertion Method . . . . . . . . . . . . . . . . . . . . . . . . . . . . 1|
|---|
|Missing Entity . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3|

###### Assertion Method

Body.

"""


def test_unmatched_catalog_entry_is_reported_not_emitted():
    lines = CATALOG_WITH_MISSING.split("\n")
    lm = make_linemap("\n".join(lines))
    chunks, problems = build_chunks(lines, lm, FILE_SHA)
    titles = [c.title for c in chunks]
    assert "Assertion Method" in titles
    assert "Missing Entity" not in titles
    assert any("Missing Entity" in p for p in problems)
