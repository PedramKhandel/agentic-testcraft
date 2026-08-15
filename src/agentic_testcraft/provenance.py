"""Provenance tracking for source-derived knowledge.

Every book-derived principle, smell, pattern, or rule must carry a
:class:`SourceRef` pointing back to the immutable source book.  This module
provides the data structures and deterministic helpers used across the whole
pipeline (inspection -> cleaning -> chunking -> extraction -> synthesis).

Security note: nothing here reads secrets.  SHA-256 hashes are computed for
integrity only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, model_validator

# The only origins the pipeline recognises.  ``book`` records MUST carry full
# provenance; other origins carry the evidence classification they claim.
ORIGIN_BOOK = "book"
ORIGIN_MODERN_OFFICIAL = "modern_official"
ORIGIN_MODERN_RESEARCH = "modern_research"
ORIGIN_INFERENCE = "inference"
ORIGIN_PROJECT_CONVENTION = "project_convention"
VALID_ORIGINS = (
    ORIGIN_BOOK,
    ORIGIN_MODERN_OFFICIAL,
    ORIGIN_MODERN_RESEARCH,
    ORIGIN_INFERENCE,
    ORIGIN_PROJECT_CONVENTION,
)

from typing import Literal

OriginLiteral = Literal[
    "book",
    "modern_official",
    "modern_research",
    "inference",
    "project_convention",
]


def sha256_file(path: Path) -> str:
    """Deterministic SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """SHA-256 of a UTF-8 encoded string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SourceRef(BaseModel):
    """Pointer back to an immutable source range.

    ``pdf_page_*`` may be ``None`` when a reliable page mapping is unavailable,
    but ``markdown_start_line`` and ``markdown_end_line`` are mandatory for
    book-derived knowledge.
    """

    source_id: str = "book"
    file_sha256: str
    markdown_start_line: int
    markdown_end_line: int
    pdf_page_start: int | None = None
    pdf_page_end: int | None = None

    @field_validator("markdown_start_line", "markdown_end_line", "pdf_page_start", "pdf_page_end")
    @classmethod
    def lines_must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("line/page values must be positive")
        return v

    @model_validator(mode="after")
    def _range_order(self) -> "SourceRef":
        if self.markdown_start_line > self.markdown_end_line:
            raise ValueError("markdown_start_line cannot exceed markdown_end_line")
        if self.pdf_page_start is not None and self.pdf_page_end is not None:
            if self.pdf_page_start > self.pdf_page_end:
                raise ValueError("pdf_page_start cannot exceed pdf_page_end")
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class Provenance(BaseModel):
    """Wraps a list of source refs with an origin and a confidence tag."""

    origin: str = ORIGIN_BOOK
    source_refs: list[SourceRef] = Field(default_factory=list)
    confidence: Annotated[
        str,
        Field(
            default="default",
            description="Evidence strength for book-derived claims.",
        ),
    ] = "default"
    extraction_model: str | None = None
    extraction_date: str | None = None

    @field_validator("origin")
    @classmethod
    def validate_origin(cls, v: str) -> str:
        if v not in VALID_ORIGINS:
            raise ValueError(f"origin must be one of {VALID_ORIGINS}, got {v!r}")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        valid = {"default", "preference", "warning", "exception", "context_dependent", "historical", "certain"}
        if v not in valid:
            raise ValueError(f"confidence must be one of {valid}, got {v!r}")
        return v


def ensure_book_provenance(provenance: Provenance) -> None:
    """Raise if a book-origin record lacks full source refs."""
    if provenance.origin != ORIGIN_BOOK:
        return
    if not provenance.source_refs:
        raise ValueError("book-origin records must have at least one source_ref")
    for ref in provenance.source_refs:
        if not ref.file_sha256:
            raise ValueError("book-origin source_ref must carry a file_sha256")
        if ref.markdown_start_line is None or ref.markdown_end_line is None:
            raise ValueError("book-origin source_ref must carry markdown line range")


def now_iso() -> str:
    """UTC timestamp in ISO-8601 (second resolution, no nanoseconds)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_jsonl(path: Path, records: list[Any]) -> None:
    """Write a list of pydantic/dict records as JSONL (one JSON object per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            if isinstance(rec, BaseModel):
                payload = rec.model_dump(exclude_none=True)
            else:
                payload = rec
            fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
