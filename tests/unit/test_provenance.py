"""Tests for provenance helpers and validation."""
from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from agentic_testcraft.provenance import (
    OriginLiteral,
    Provenance,
    SourceRef,
    ensure_book_provenance,
    now_iso,
    sha256_text,
    sha256_file,
)


def test_sha256_text_is_deterministic():
    a = sha256_text("hello")
    b = sha256_text("hello")
    assert a == b == hashlib.sha256(b"hello").hexdigest()
    assert a != sha256_text("world")


def test_source_ref_book_requires_lines():
    with pytest.raises(ValueError):
        SourceRef(source_id="book", file_sha256="x", markdown_start_line=None)


def test_source_ref_pdf_may_be_none():
    ref = SourceRef(
        source_id="book",
        file_sha256="a" * 64,
        markdown_start_line=1,
        markdown_end_line=10,
    )
    assert ref.pdf_page_start is None


def test_provenance_rejects_unknown_origin():
    with pytest.raises(ValidationError):
        Provenance(origin="not-a-real-origin")


def test_book_provenance_enforced():
    prov = Provenance(origin="book", source_refs=[])
    with pytest.raises(ValueError):
        ensure_book_provenance(prov)


def test_non_book_provenance_needs_no_refs():
    prov = Provenance(origin="inference", source_refs=[])
    ensure_book_provenance(prov)  # should not raise


def test_now_iso_is_iso8601():
    ts = now_iso()
    assert "T" in ts and ts.endswith(("+00:00", "Z")) or ts.endswith("00:00")
