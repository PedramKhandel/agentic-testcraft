"""Unit tests for the native-agent extractor (Stage 5)."""
from __future__ import annotations

import pytest

from agentic_testcraft.extract import (
    NativeAgentExtractor,
    OpenAIExtractor,
    _bullets,
    _clean_text,
    _first_sentence,
    _remap_smell_id,
    _segments,
)

FILE_SHA = "a" * 64


def _ref(line_start: int = 1, line_end: int = 10) -> dict:
    return {
        "source_id": "book",
        "file_sha256": FILE_SHA,
        "markdown_start_line": line_start,
        "markdown_end_line": line_end,
    }


PATTERN_CHUNK = {
    "id": "pattern:assertion-method",
    "kind": "pattern",
    "chapter_kind": "pattern_chapter",
    "chapter_title": "xUnit Basics Patterns",
    "title": "Assertion Method",
    "category": "",
    "clean_start_line": 1,
    "clean_end_line": 12,
    "source_refs": [_ref(1, 12)],
    "subsections": [],
    "aliases": [],
}

PATTERN_TEXT = [
    "###### Assertion Method",
    "",
    "_How do we make tests self-checking?_",
    "**Assertion Method**",
    "**We call a utility method to evaluate the outcome.**",
    "",
    "###### How It Works",
    "We encode the expected outcome as assertions.",
    "",
    "###### Why We Do This",
    "Because verbose conditional logic is hard to read.",
    "",
]


SMELL_CHUNK = {
    "id": "code:obscure-test",
    "kind": "code",
    "chapter_kind": "smell_chapter",
    "chapter_title": "Code Smells",
    "title": "Obscure Test",
    "category": "code",
    "clean_start_line": 1,
    "clean_end_line": 12,
    "source_refs": [_ref(1, 12)],
    "subsections": [],
    "aliases": [],
}

SMELL_TEXT = [
    "###### Obscure Test",
    "",
    "###### It is difficult to understand the test at a glance.",
    "Automated tests should serve two purposes.",
    "",
    "###### Symptoms",
    "- hard to read",
    "- verbose",
    "",
    "###### Impact",
    "- bugs slip through",
    "",
]


GOAL_CHUNK = {
    "id": "goal:tests-as-specification",
    "kind": "goal",
    "chapter_kind": "goal_chapter",
    "chapter_title": "Goals of Test Automation",
    "title": "Tests as Specification",
    "category": "",
    "clean_start_line": 1,
    "clean_end_line": 3,
    "source_refs": [_ref(1, 3)],
    "subsections": [],
    "aliases": [],
}

GOAL_TEXT = [
    "###### Goal: Tests as Specification",
    "",
    "If we are doing test-driven development, the tests capture behaviour.",
    "",
]


PRINCIPLE_CHUNK = {
    "id": "principle:write-the-tests-first",
    "kind": "principle",
    "chapter_kind": "principle_chapter",
    "chapter_title": "Principles of Test Automation",
    "title": "Write the Tests First",
    "category": "",
    "clean_start_line": 1,
    "clean_end_line": 3,
    "source_refs": [_ref(1, 3)],
    "subsections": [],
    "aliases": [],
}

PRINCIPLE_TEXT = [
    "###### Principle: Write the Tests First",
    "",
    "Test-driven development saves debugging effort.",
    "",
]


def test_segment_parser_flushes_trailing_intro():
    segs = _segments(GOAL_TEXT)
    intros = [body for h, body in segs if h is None]
    assert len(intros) == 1
    assert "test-driven development" in _clean_text(intros[0])


def test_segment_parser_captures_subsections():
    segs = _segments(PATTERN_TEXT)
    headings = [h for h, _ in segs if h is not None]
    assert "How It Works" in headings
    assert "Why We Do This" in headings


def test_clean_text_joins_and_collapses_ws():
    assert _clean_text(["  a  b  ", "", "  c"]) == "a b c"


def test_first_sentence():
    assert _first_sentence("We encode tests. More.") == "We encode tests."


def test_bullets_extracts_dashes():
    assert _bullets(["- first", "- second", ""]) == ["first", "second"]


def test_bullets_falls_back_to_paragraph():
    assert _bullets(["just text"]) == ["just text"]


def test_remap_smell_id():
    assert _remap_smell_id("code:obscure-test") == "smell:obscure-test"
    assert _remap_smell_id("behavior:x") == "smell:x"
    assert _remap_smell_id("pattern:foo") == "pattern:foo"


def test_native_extraction_pattern():
    ext = NativeAgentExtractor()
    recs, errors = ext.extract([PATTERN_CHUNK], PATTERN_TEXT)
    assert errors == []
    rec = recs[0]
    assert rec["id"] == "pattern:assertion-method"
    assert rec["problem"] == "How do we make tests self-checking?"
    assert rec["intent"] == "We call a utility method to evaluate the outcome."
    assert "We encode the expected outcome" in rec["solution"]


def test_native_extraction_smell_remaps_id_and_bullets():
    ext = NativeAgentExtractor()
    recs, errors = ext.extract([SMELL_CHUNK], SMELL_TEXT)
    assert errors == []
    rec = recs[0]
    assert rec["id"] == "smell:obscure-test"
    assert rec["summary"] == "It is difficult to understand the test at a glance"
    assert rec["symptoms"] == ["hard to read", "verbose"]
    assert rec["impact"] == ["bugs slip through"]


def test_native_extraction_goal_has_paragraph_summary():
    ext = NativeAgentExtractor()
    recs, errors = ext.extract([GOAL_CHUNK], GOAL_TEXT)
    assert errors == []
    assert recs[0]["summary"].startswith("If we are doing test-driven development")


def test_native_extraction_principle_statement():
    ext = NativeAgentExtractor()
    recs, errors = ext.extract([PRINCIPLE_CHUNK], PRINCIPLE_TEXT)
    assert errors == []
    assert recs[0]["statement"].startswith("Test-driven development saves")


def test_native_extraction_skips_reference_chunks():
    ext = NativeAgentExtractor()
    ref_chunk = {
        "id": "reference:contents", "kind": "reference",
        "chapter_kind": "reference", "chapter_title": "Contents",
        "title": "Contents", "category": "",
        "clean_start_line": 1, "clean_end_line": 2,
        "source_refs": [_ref(1, 2)], "subsections": [], "aliases": [],
    }
    recs, errors = ext.extract([ref_chunk], ["###### Contents", "", "toc"])
    assert recs == []
    assert errors == []


def test_openai_provider_requires_key():
    with pytest.raises(SystemExit):
        OpenAIExtractor()


def test_validate_knowledge_cli_accepts_no_credentials():
    # importing the LLM stubs must not require credentials at import time
    from agentic_testcraft.extract import AnthropicExtractor, GoogleExtractor

    for cls in (AnthropicExtractor, GoogleExtractor):
        with pytest.raises(SystemExit):
            cls()
