"""Data model and helpers for semantic chunks of the source book."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SLUG_RX = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Stable, reversible-ish slug for an entity name."""
    s = name.strip().lower()
    s = " ".join(s.split())
    return SLUG_RX.sub("-", s).strip("-") or "untitled"


def strip_prefix(text: str, prefix: str) -> str:
    return text[len(prefix):].strip() if text.startswith(prefix) else text


@dataclass
class LineMap:
    """Maps 1-based clean line numbers to 1-based source (original) line lists."""

    entries: list[dict[str, Any]] = field(default_factory=list)
    _by_clean: dict[int, list[int]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for entry in self.entries:
            self._by_clean[int(entry["clean_line"])] = list(entry["source_lines"])

    @classmethod
    def load(cls, path: Path) -> LineMap:
        lm = cls()
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                entry = json.loads(line)
                lm.entries.append(entry)
                lm._by_clean[int(entry["clean_line"])] = list(entry["source_lines"])
        return lm

    @property
    def clean_line_count(self) -> int:
        return len(self._by_clean)

    def source_range_for(self, clean_start: int, clean_end: int) -> tuple[int | None, int | None]:
        """Return (min, max) original source line for a clean line span."""
        srcs: list[int] = []
        for c in range(int(clean_start), int(clean_end) + 1):
            srcs.extend(self._by_clean.get(c, []))
        if not srcs:
            return None, None
        return min(srcs), max(srcs)


@dataclass
class Chunk:
    id: str
    kind: str
    chapter_kind: str
    chapter_title: str
    title: str
    category: str = ""
    clean_start_line: int = 0
    clean_end_line: int = 0
    source_start_line: int | None = None
    source_end_line: int | None = None
    pdf_page_start: int | None = None
    pdf_page_end: int | None = None
    subsections: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

    def to_record(self, file_sha256: str) -> dict[str, Any]:
        ref: dict[str, Any] = {"source_id": "book", "file_sha256": file_sha256}
        if self.source_start_line:
            ref["markdown_start_line"] = self.source_start_line
        if self.source_end_line:
            ref["markdown_end_line"] = self.source_end_line
        return {
            "id": self.id,
            "kind": self.kind,
            "chapter_kind": self.chapter_kind,
            "chapter_title": self.chapter_title,
            "title": self.title,
            "category": self.category,
            "clean_start_line": self.clean_start_line,
            "clean_end_line": self.clean_end_line,
            "source_refs": [ref],
            "subsections": list(self.subsections),
            "aliases": list(self.aliases),
        }
