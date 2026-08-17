"""Unit tests for Stage 8 modernization records."""
from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from agentic_testcraft.modernize import MODERN_RECORDS, REVIEW_DATE, _rec
from agentic_testcraft.schemas import ModernizationRecord

_PREFIXES = ("pattern:", "smell:", "goal:", "principle:")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def test_records_unique_and_valid():
    ids = [r["id"] for r in MODERN_RECORDS]
    assert len(ids) == len(set(ids))
    for r in MODERN_RECORDS:
        assert r["id"].startswith("modern:"), r["id"]
        assert _SLUG_RE.match(r["id"][len("modern:"):]), r["id"]
        ModernizationRecord(**r)


def test_review_date_is_isodate_and_current():
    for r in MODERN_RECORDS:
        assert r["review_date"] == REVIEW_DATE
    assert REVIEW_DATE == "2026-08-17"


def test_official_sources_are_absolute_urls():
    for r in MODERN_RECORDS:
        assert r["official_sources"], f"{r['id']}: must cite at least one source"
        for u in r["official_sources"]:
            assert u.startswith("https://"), f"{r['id']}: non-https source {u}"


def test_affected_knowledge_ids_well_formed():
    for r in MODERN_RECORDS:
        assert r["affected_knowledge_ids"], f"{r['id']}: must reference knowledge"
        for kid in r["affected_knowledge_ids"]:
            assert kid.split(":", 1)[0] in {"pattern", "smell", "goal", "principle"}, kid
            slug = kid.split(":", 1)[1]
            assert _SLUG_RE.match(slug), kid


def test_each_record_has_positions_and_status():
    for r in MODERN_RECORDS:
        assert r["book_position"].strip()
        assert r["modern_position"].strip()
        assert r["status"] in {"unchanged", "clarified", "expanded",
                               "narrowed", "superseded", "historical"}


def test_url_validator_rejects_non_urls():
    with pytest.raises(ValidationError, match="absolute URLs"):
        _rec(
            id="modern:bad", topic="bad", book_position="b", modern_position="m",
            status="clarified", rationale="r",
            sources=["not-a-url"], affected=["pattern:test-method"],
        )


def test_date_validator_rejects_bad_format():
    record = {
        "id": "modern:bad-date", "topic": "bad", "book_position": "b",
        "modern_position": "m", "status": "clarified", "rationale": "r",
        "official_sources": ["https://example.org"],
        "affected_knowledge_ids": ["pattern:test-method"],
        "review_date": "17-08-2026",
    }
    with pytest.raises(ValidationError, match="YYYY-MM-DD"):
        ModernizationRecord(**record)
