"""Semantic structure parsing and chunking of the cleaned book.

The Markdown conversion flattens headings (chapters are ``H5``, every entry and
subsection is ``H6``).  This module reconstructs semantic units **by concept**:

* ``H5`` lines delineate major chapters.
* ``H6`` lines delineate individual patterns / smells / goals / principles and
  their subsections (``How It Works``, ``Symptoms``, …).

Entity detection is **catalog-driven** for pattern & smell chapters: each such
chapter opens with a ``Patterns in This Chapter`` / ``Smells in This Chapter``
table that lists every entity; we anchor one chunk per catalog entry at its
first ``H6`` occurrence.  This prevents false entities (subsections, figure
labels, repeated cross-references) and deduplicates automatically.

Every chunk keeps a clean-line range and, via the provenance line map, the
original Markdown line range.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from .chunk import Chunk, LineMap, slugify
from .config import load_settings
from .provenance import now_iso

console = Console()

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")

# Catalog table row: "Name . . . . . .  page" inside a markdown table cell.
ROW_RE = re.compile(r"^\s*(.*?)\s*\.[\s.]*?(\d+)\s*$")

# Page numbers / figure labels that appear as standalone bold lines.
PAGE_LABEL_RE = re.compile(r"^\*\*\d+\*\*$")

CHAPTER_KINDS: dict[str, tuple[str, str]] = {
    "Goals of Test Automation": ("goal_chapter", "goal"),
    "Principles of Test Automation": ("principle_chapter", "principle"),
    "Code Smells": ("smell_chapter", "smell"),
    "Behavior Smells": ("smell_chapter", "smell"),
    "Project Smells": ("smell_chapter", "smell"),
    "Test Strategy Patterns": ("pattern_chapter", "pattern"),
    "xUnit Basics Patterns": ("pattern_chapter", "pattern"),
    "Fixture Setup Patterns": ("pattern_chapter", "pattern"),
    "Fixture Teardown Patterns": ("pattern_chapter", "pattern"),
    "Test Double Patterns": ("pattern_chapter", "pattern"),
    "Test Organization Patterns": ("pattern_chapter", "pattern"),
    "Database Patterns": ("pattern_chapter", "pattern"),
    "Design-for-Testability Patterns": ("pattern_chapter", "pattern"),
    "Value Patterns": ("pattern_chapter", "pattern"),
}

SMELL_CATEGORIES = {
    "Code Smells": "code",
    "Behavior Smells": "behavior",
    "Project Smells": "project",
}

REFERENCE_CHAPTERS = frozenset(
    {
        "Contents", "Visual Summary of the Pattern Language", "Foreword", "Preface",
        "Acknowledgments", "Introduction", "Refactoring a Test", "A Brief Tour",
        "Test Smells", "Philosophy of Test Automation", "Test Automation Strategy",
        "xUnit Basics", "Transient Fixture Management", "Persistent Fixture Management",
        "Using Test Doubles", "Organizing Our Tests", "Testing with Databases",
        "A Roadmap to Effective Test Automation", "Test Refactorings",
        "xUnit Terminology", "xUnit Family Members", "Tools", "Goals and Principles",
        "Smells, Aliases, and Causes", "Patterns, Aliases, and Variations",
        "Glossary", "References", "Index",
        "THE ADDISON-WESLEY SIGNATURE SERIES", "TITLES IN THE SERIES",
    }
)

SUBSECTION_PREFIXES: tuple[str, ...] = ("Variation:", "Example:", "How to")
SUBSECTION_KEYWORDS: frozenset[str] = frozenset(
    {
        "About This Chapter", "The Principles", "The Goals", "The Smells", "The Patterns",
        "How It Works", "Why We Do This", "Implementation Notes", "Variations",
        "When to Use It", "When to Use", "Also known as", "Also known as:",
        "Problem", "Context", "Forces", "Solution", "Motivating Example",
        "Refactoring Notes", "Symptoms", "Impact", "Causes", "Solution Patterns",
        "Further Reading", "Result", "Back Door", "Smells in This Chapter",
        "Patterns in This Chapter", "Key Pertinent Forces",
        "Continued...", "What Is a Fixture?", "What's Next?", "About the Name",
    }
)

SUBSECTION_PREFIX_WORDS: tuple[str, ...] = (
    "How it works", "Why we do", "Implementation", "Variations", "When to",
    "Also known", "Motivating", "Refactoring", "Solution patterns",
)


@dataclass
class Heading:
    level: int
    text: str
    clean_line: int


def parse_headings(lines: list[str]) -> list[Heading]:
    headings: list[Heading] = []
    for i, ln in enumerate(lines, start=1):
        m = HEADING_RE.match(ln)
        if not m:
            continue
        headings.append(Heading(level=len(m.group(1)), text=m.group(2).strip(), clean_line=i))
    return headings


def _normalise_name(text: str) -> str:
    s = " ".join(text.strip().strip("*_").split())
    # Normalise smart/curly apostrophes so keyword matching is robust to OCR
    # variants (e.g. "What's Next?" vs "What's Next?").
    s = s.replace("’", "'").replace("‘", "'")
    return s.strip(":* ")


def _is_subsection(text: str) -> bool:
    norm = _normalise_name(text)
    if norm in SUBSECTION_KEYWORDS:
        return True
    if any(norm.startswith(p) for p in SUBSECTION_PREFIXES):
        return True
    return any(norm.lower().startswith(p.lower()) for p in SUBSECTION_PREFIX_WORDS)


@dataclass
class CatalogEntry:
    name: str
    category: str | None
    h6_line: int | None = None


def _parse_chapter_catalog(lines: list[str], start_idx: int) -> list[CatalogEntry]:
    """Parse a `Patterns/Smiles in This Chapter` table starting near ``start_idx``.

    Returns ordered entries with names and optional group category.  Group
    headers (``_Category_``) set the category for subsequent rows.
    """
    entries: list[CatalogEntry] = []
    category: str | None = None
    i = start_idx
    # advance to the first table row (a line starting with '|')
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        i += 1
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        raw = lines[i].strip().strip("|").strip()
        if raw.startswith("---"):
            i += 1
            continue
        # group header: _Category_
        if raw.startswith("_") and raw.endswith("_") and len(raw) > 2:
            category = raw.strip("_")
            i += 1
            continue
        m = ROW_RE.match(raw)
        if m:
            entries.append(CatalogEntry(name=_normalise_name(m.group(1)), category=category, h6_line=None))
        i += 1
    return entries


def _classify_chapter(title: str) -> tuple[str, str]:
    if title in CHAPTER_KINDS:
        kind, entity = CHAPTER_KINDS[title]
        if entity == "smell":
            entity = SMELL_CATEGORIES.get(title, "smell")
        return kind, entity
    if title in REFERENCE_CHAPTERS:
        return "reference", "reference"
    return "narrative", "narrative"


def _collect_subsections(section_h6: list[Heading], start: int, end: int) -> list[str]:
    return [
        _normalise_name(h.text)
        for h in section_h6
        if start < h.clean_line <= end and _is_subsection(h.text)
    ]


def _entity_chunks(
    chapter_title: str, chapter_kind: str, entity_kind: str,
    section_h6: list[Heading], cleaned_lines: list[str], line_map: LineMap,
    file_sha256: str, c_start: int, c_end: int,
) -> tuple[list[Chunk], list[str]]:
    """Build entity chunks for an entity-bearing chapter.

    Returns ``(chunks, unmatched_names)``.  For smell/pattern chapters the
    catalogue is the source of truth: exactly one chunk per catalogue entry
    that is anchored at a real ``H6`` heading.  Catalogue entries with no
    matching heading are reported (unmatched) rather than emitted as
    whole-chapter noise.
    """
    out: list[Chunk] = []
    unmatched: list[str] = []
    anchors = [h for h in section_h6 if not _is_subsection(h.text)]
    anchor_lines = [h.clean_line for h in anchors]
    text_by_line = {h.clean_line: _normalise_name(h.text) for h in anchors}

    if chapter_kind in ("smell_chapter", "pattern_chapter"):
        catalog = _collect_catalog(section_h6, cleaned_lines)
        used: set[int] = set()
        matched: list[tuple[int, str, str | None]] = []  # (line, name, category)
        for ce in catalog:
            target = _normalise_name(ce.name)
            match_line = next(
                (ln for ln in anchor_lines if ln not in used and text_by_line.get(ln) == target),
                None,
            )
            if match_line is None:
                unmatched.append(ce.name)
                continue
            used.add(match_line)
            matched.append((match_line, ce.name, ce.category))
        matched.sort(key=lambda m: m[0])
        for i, (line, name, category) in enumerate(matched):
            end_line = matched[i + 1][0] - 1 if i + 1 < len(matched) else c_end
            src_start, src_end = line_map.source_range_for(line, end_line)
            out.append(
                Chunk(
                    id=f"{entity_kind}:{slugify(name)}",
                    kind=entity_kind,
                    chapter_kind=chapter_kind,
                    chapter_title=chapter_title,
                    title=name,
                    category=category or SMELL_CATEGORIES.get(chapter_title, ""),
                    clean_start_line=line,
                    clean_end_line=end_line,
                    source_start_line=src_start,
                    source_end_line=src_end,
                    subsections=_collect_subsections(section_h6, line, end_line),
                )
            )
    else:
        # goal / principle chapters: real entities are the "Goal:" / "Principle:"
        # headings.  Other H6s are descriptive intros ("Tests Should ..."),
        # navigational labels ("Chapter N", "What's Next?") and must not become
        # entities.
        prefix = "goal:" if entity_kind == "goal" else "principle:"
        entity_anchors = [
            h
            for h in section_h6
            if not _is_subsection(h.text)
            and _normalise_name(h.text).lower().startswith(prefix)
        ]
        seen: set[str] = set()
        for idx, h in enumerate(entity_anchors):
            raw = h.text
            name = _normalise_name(raw.split(":", 1)[-1]) if ":" in raw else _normalise_name(raw)
            slug = slugify(name)
            if slug in seen:
                continue
            seen.add(slug)
            end_line = entity_anchors[idx + 1].clean_line - 1 if idx + 1 < len(entity_anchors) else c_end
            src_start, src_end = line_map.source_range_for(h.clean_line, end_line)
            out.append(
                Chunk(
                    id=f"{entity_kind}:{slug}",
                    kind=entity_kind,
                    chapter_kind=chapter_kind,
                    chapter_title=chapter_title,
                    title=name,
                    category=SMELL_CATEGORIES.get(chapter_title, ""),
                    clean_start_line=h.clean_line,
                    clean_end_line=end_line,
                    source_start_line=src_start,
                    source_end_line=src_end,
                    subsections=_collect_subsections(section_h6, h.clean_line, end_line),
                )
            )
    return out, unmatched


def _collect_catalog(section_h6: list[Heading], cleaned_lines: list[str]) -> list[CatalogEntry]:
    cat_h6 = next(
        (h for h in section_h6 if h.text in ("Patterns in This Chapter", "Smells in This Chapter")),
        None,
    )
    if cat_h6 is None:
        return []
    return _parse_chapter_catalog(cleaned_lines, cat_h6.clean_line - 1)


def _source_sha256(report_path: Path) -> str:
    """Read the markdown source sha256 from the Stage-2 source report."""
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            for entry in report.get("files", []):
                if entry.get("filename", "").endswith(".md"):
                    sha = entry.get("sha256", "unknown")
                    return str(sha) if sha is not None else "unknown"
        except Exception:
            pass
    return "unknown"


def build_chunks(
    cleaned_lines: list[str], line_map: LineMap, file_sha256: str
) -> tuple[list[Chunk], list[str]]:
    """Split the cleaned book into semantic chunks.

    Returns ``(chunks, completeness_problems)``.  Entity-bearing chapters
    (goals, principles, smells, patterns) delegate to ``_entity_chunks``;
    reference / narrative / front-matter chapters collapse to a single
    chapter-scale chunk.  Chunk IDs are deduplicated globally; any
    duplicate (across catalog matches or chapter spans) is reported and the
    later occurrence is dropped.
    """
    headings = parse_headings(cleaned_lines)
    chapters = [h for h in headings if h.level == 5]
    chapter_ranges: list[tuple[Heading, int, int]] = []
    for idx, ch in enumerate(chapters):
        start = ch.clean_line
        end = chapters[idx + 1].clean_line - 1 if idx + 1 < len(chapters) else len(cleaned_lines)
        chapter_ranges.append((ch, start, end))

    h6_by_chap: dict[int, list[Heading]] = {
        c_start: [h for h in headings if c_start <= h.clean_line <= c_end and h.level == 6]
        for _, c_start, c_end in chapter_ranges
    }
    # Every entity name that actually has a definition heading anywhere in the
    # book; a catalogue entry whose name is an H6 elsewhere is a cross-reference,
    # not a genuine miss.
    global_entity_names: set[str] = {
        _normalise_name(h.text)
        for h in headings
        if h.level == 6 and not _is_subsection(h.text)
    }

    chunks: list[Chunk] = []
    problems: list[str] = []
    seen_ids: set[str] = set()

    for ch, c_start, c_end in chapter_ranges:
        chapter_title = ch.text
        chapter_kind, entity_kind = _classify_chapter(chapter_title)
        section_h6 = h6_by_chap[c_start]

        if chapter_kind in ("goal_chapter", "principle_chapter",
                            "smell_chapter", "pattern_chapter"):
            ch_chunks, unmatched = _entity_chunks(
                chapter_title, chapter_kind, entity_kind,
                section_h6, cleaned_lines, line_map, file_sha256, c_start, c_end,
            )
            for name in unmatched:
                # only a true completeness problem if the name is never an H6
                if name not in global_entity_names:
                    problems.append(
                        f"unmatched catalog entry: {chapter_title} :: {name}"
                    )
        else:
            # reference / narrative / front matter -> one chapter-scale chunk
            src_start, src_end = line_map.source_range_for(c_start, c_end)
            ch_chunks = [
                Chunk(
                    id=f"{entity_kind}:{slugify(chapter_title) or 'chapter'}",
                    kind=entity_kind,
                    chapter_kind=chapter_kind,
                    chapter_title=chapter_title,
                    title=chapter_title,
                    category=SMELL_CATEGORIES.get(chapter_title, ""),
                    clean_start_line=c_start,
                    clean_end_line=c_end,
                    source_start_line=src_start,
                    source_end_line=src_end,
                    subsections=[],
                )
            ]

        for c in ch_chunks:
            if c.id in seen_ids:
                problems.append(f"duplicate chunk id: {c.id} (chapter {chapter_title})")
                continue
            seen_ids.add(c.id)
            chunks.append(c)

    return chunks, problems


def run_split() -> None:
    """Stage 3 entry point: chunk the cleaned book and emit manifest + report."""
    from collections import Counter

    settings = load_settings()
    settings.ensure_dirs()
    p = settings.paths
    cleaned_path = p.work_dir / "book.cleaned.md"
    line_map_path = p.work_dir / "line-map.jsonl"
    manifest_path = p.work_dir / "chunk-manifest.jsonl"
    structure_path = p.work_dir / "structure.json"

    cleaned_lines = cleaned_path.read_text(encoding="utf-8").split("\n")
    line_map = LineMap.load(line_map_path)
    file_sha256 = _source_sha256(p.work_dir / "source-report.json")

    chunks, problems = build_chunks(cleaned_lines, line_map, file_sha256)

    records = [json.dumps(c.to_record(file_sha256), ensure_ascii=False) for c in chunks]
    manifest_path.write_text(
        ("\n".join(records) + "\n") if records else "", encoding="utf-8"
    )

    report = {
        "generated_at": now_iso(),
        "file_sha256": file_sha256,
        "chunk_count": len(chunks),
        "by_kind": dict(Counter(c.kind for c in chunks)),
        "by_chapter_kind": dict(Counter(c.chapter_kind for c in chunks)),
        "completeness_problems": problems,
    }
    structure_path.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )

    console.print(
        "[green]chunked[/green] [bold]"
        f"{len(chunks)}[/bold] chunks ({report['by_kind']}); "
        f"{len(problems)} completeness problem(s) -> {manifest_path.name}"
    )

