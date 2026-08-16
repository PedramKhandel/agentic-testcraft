"""Deterministic, provenance-preserving Markdown cleaner for the source book.

The input Markdown is an OCR/conversion product: it contains site watermarks,
page-header lines, HTML comments around figures, ``<sup>``/``<br>`` markup,
struck-through hyphens, and f-ligature word splits (e.g. "specifi cation").

This module converts it to a stable, clean representation **without destroying
semantic content** and with strict line-level provenance.

Design
------
* Every transformation is a named, pure rule with unit tests on synthetic
  snippets (see ``tests/unit/test_clean.py``).
* The cleaner processes input line-by-line.  Each output clean line records the
  1-based source line numbers it was derived from plus the list of
  transformations applied.  Removing a line simply omits it from the output
  (and increments that rule's removal count).
* No rule relies on 1:1 line correspondence; the provenance map is explicit
  per line.

Security: this module only reads/writes local files; it never performs network
access and never logs secret material.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from .config import Settings, load_settings
from .provenance import now_iso

console = Console()

# A single line after partial processing: original source line number(s) +
# current text + transformations applied so far.
@dataclass
class Line:
    source_lines: list[int]
    text: str
    transformations: list[str] = field(default_factory=list)

    def copy_with(self, text: str, *tf: str) -> "Line":
        return Line(
            source_lines=list(self.source_lines),
            text=text,
            transformations=list(self.transformations) + list(tf),
        )


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #

RE_SUP = re.compile(r"<sup>(.*?)</sup>")
RE_STRIKETHROUGH = re.compile(r"~~([A-Za-z\u2014-])~~")
# A struck hyphen+letter between two words, e.g. "people ~~-o~~ riented".
RE_STRIKETHROUGH_HYPHEN_LETTER = re.compile(r"\s*~~-([A-Za-z])~~\s*")
RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
RE_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
# f-ligature splits.  Only fi/fl are joined: ff/er/st/ds/ft are genuine word
# boundaries (e.g. "sniff test", "number of") and must NOT be joined.
RE_FL = re.compile(r"([a-z]{2,})fl ([a-z]{2,})")
RE_FI = re.compile(r"([a-z]{2,})fi ([a-z]{2,})")
# Heading emphasis, e.g. "###### **Name**" or "###### _Name_" -> "###### Name"
RE_HEADING_BOLD = re.compile(r"^(#{1,6})\s+(\*{2}|_{1,2})(.+?)(\*{2}|_{1,2})\s*$")
# Page headers inserted by the conversion: "Chapter N  <Title>"
RE_PAGE_HEADER = re.compile(r"^(Chapter|Part)\s+\d+\s.+$")


def _unwrap_sup(line: Line) -> Line:
    if "<sup>" in line.text and "</sup>" in line.text:
        return line.copy_with(RE_SUP.sub(lambda m: " " + m.group(1), line.text), "unwrap_sup")
    return line


def _remove_strikethrough_artifacts(line: Line) -> Line:
    """Restore struck-through single chars/hyphens (PDF artifacts).

    ``~~-~~`` / ``~~\u2014~~`` and struck single letters like ``~~I~~`` are
    conversion artefacts of struck typographic marks; the single char is
    restored and the markers removed.

    A struck hyphen+letter that sat between two words (e.g.
    ``people ~~-o~~ riented``) is rejoined as ``people-oriented``.

    Genuine multi-word strikethrough (``~~Key to ...~~``) is left in place.
    """
    if "~~" not in line.text:
        return line
    text = RE_STRIKETHROUGH_HYPHEN_LETTER.sub(lambda m: "-" + m.group(1), line.text)
    text = RE_STRIKETHROUGH.sub(lambda m: m.group(1), text)
    if text != line.text:
        return line.copy_with(text, "remove_strikethrough_artifacts")
    return line


def _convert_breaks(line: Line) -> list[Line]:
    """Split a line on ``<br>`` into multiple derived lines (same source)."""
    if "<br" not in line.text.lower():
        return [line]
    parts = RE_BR.split(line.text)
    out = []
    for i, part in enumerate(parts):
        new = line.copy_with(part, "convert_break")
        out.append(new)
    return out


def _strip_comments(line: Line) -> Line:
    if "<!--" in line.text:
        new_text = RE_HTML_COMMENT.sub("", line.text)
        if new_text != line.text:
            return line.copy_with(new_text, "strip_html_comment")
    return line


def _join_ligatures(line: Line) -> Line:
    """Join f-ligature word splits (fi/fl).  Conservative and guarded."""
    if not re.search(r"[a-z]{2,}(fi|fl) [a-z]{2,}", line.text):
        return line
    text = RE_FI.sub(r"\1fi\2", line.text)
    text = RE_FL.sub(r"\1fl\2", text)
    # A transformation is only "applied" if the text actually changed.
    if text != line.text:
        return line.copy_with(text, "join_f_ligatures")
    return line


def _strip_heading_emphasis(line: Line) -> Line:
    """``###### **Name**`` / ``###### _Name_`` -> ``###### Name``.

    Emphasis is redundant inside a heading and obscures entity-name matching.
    Handles the symmetric ``**…**`` and ``_…_`` forms that the conversion
    produces.
    """
    m = RE_HEADING_BOLD.match(line.text)
    if m:
        title = m.group(3).strip().strip("*_").strip()
        if title:
            return line.copy_with(f"{m.group(1)} {title}", "strip_heading_emphasis")
    # Asymmetric italic-only heading like "###### _Name_" that missed above.
    m = re.match(r"^(#{1,6})\s+_+(.+)_+\s*$", line.text)
    if m:
        title = m.group(2).strip().strip("*_").strip()
        if title:
            return line.copy_with(f"{m.group(1)} {title}", "strip_heading_emphasis")
    return line


def _strip_trailing_ws(line: Line) -> Line:
    stripped = line.text.rstrip()
    if stripped != line.text:
        return line.copy_with(stripped, "strip_trailing_whitespace")
    return line


WATERMARK_STRINGS = {"www.it-ebooks.info", "eZ | ARS"}


def _is_removable(line: str) -> bool:
    s = line.strip()
    if s in WATERMARK_STRINGS:
        return True
    if RE_PAGE_HEADER.match(s):
        return True
    return False


@dataclass
class CleanupCounts:
    total_input_lines: int = 0
    total_output_lines: int = 0
    removed_watermark: int = 0
    removed_page_header: int = 0
    transform_counts: Counter = field(default_factory=Counter)

    def to_report(self) -> dict:
        return {
            "total_input_lines": self.total_input_lines,
            "total_output_lines": self.total_output_lines,
            "removed_watermark": self.removed_watermark,
            "removed_page_header": self.removed_page_header,
            "transform_counts": dict(self.transform_counts),
            "generated_at": now_iso(),
        }


# 1:1 transform rules (applied before the splitting ``<br>`` rule).
TRANSFORM_RULES: list = [
    _strip_comments,
    _unwrap_sup,
    _remove_strikethrough_artifacts,
    _join_ligatures,
    _strip_heading_emphasis,
    _strip_trailing_ws,
]
# ``_convert_breaks`` is applied separately because it may split a line.


@dataclass
class CleanResult:
    text: str
    line_map: list[dict]
    counts: "CleanupCounts"


def clean_text(text: str) -> CleanResult:
    """Clean a Markdown string deterministically.

    Returns a :class:`CleanResult` with the cleaned text, a per-clean-line
    provenance map, and rule-level counts.
    """
    raw_lines = text.split("\n")
    counts = CleanupCounts(total_input_lines=len(raw_lines))

    # Seed with source line numbers (1-based).
    work: list[Line] = [
        Line(source_lines=[i + 1], text=ln) for i, ln in enumerate(raw_lines)
    ]

    # Apply 1:1 transform rules.
    for rule_fn in TRANSFORM_RULES:
        work = [rule_fn(ln) for ln in work]

    # Split on <br> (may multiply lines).
    split_work: list[Line] = []
    for ln in work:
        split_work.extend(_convert_breaks(ln))
    work = split_work

    # Remove watermark + page-header lines.
    kept: list[Line] = []
    for ln in work:
        if _is_removable(ln.text):
            if ln.text.strip() in WATERMARK_STRINGS:
                counts.removed_watermark += 1
            else:
                counts.removed_page_header += 1
            continue
        kept.append(ln)

    # Collapse 3+ blank lines to a single blank line.
    normalised: list[Line] = []
    blank_run = 0
    for ln in kept:
        if ln.text.strip() == "":
            blank_run += 1
            if blank_run > 1:
                continue
            normalised.append(ln)
        else:
            blank_run = 0
            normalised.append(ln)

    # Renumber clean lines and build the provenance map.
    cleaned_lines: list[str] = []
    line_map: list[dict] = []
    for idx, ln in enumerate(normalised, start=1):
        cleaned_lines.append(ln.text)
        counts.transform_counts.update(ln.transformations)
        seen: list[str] = []
        for t in ln.transformations:
            if t not in seen:
                seen.append(t)
        line_map.append(
            {
                "clean_line": idx,
                "source_lines": ln.source_lines,
                "transformations": seen,
            }
        )

    counts.total_output_lines = len(cleaned_lines)
    cleaned_text = "\n".join(cleaned_lines)
    if not cleaned_text.endswith("\n"):
        cleaned_text += "\n"
    return CleanResult(text=cleaned_text, line_map=line_map, counts=counts)


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #


def _discover_source(settings: Settings) -> tuple[str, str, str, str]:
    """Locate the source PDF and Markdown.  Returns (md_path, pdf_path, md_sha, pdf_sha)."""
    from .provenance import sha256_file

    repo = settings.paths.repo_root
    md_candidates = sorted(repo.glob("xUnit Test Patterns*.md"))
    pdf_candidates = sorted(repo.glob("xUnit Test Patterns*.pdf"))
    if not md_candidates:
        raise FileNotFoundError("No 'xUnit Test Patterns*.md' source file found.")
    md_path = md_candidates[0]
    if not pdf_candidates:
        raise FileNotFoundError("No 'xUnit Test Patterns*.pdf' source file found.")
    pdf_path = pdf_candidates[0]
    return str(md_path), str(pdf_path), sha256_file(md_path), sha256_file(pdf_path)


def run_clean() -> int:
    """Phase-0/M2 entry point: inspect, clean, write provenance artifacts."""
    from .source_inspect import run_inspection

    settings = load_settings()
    settings.paths.work_dir.mkdir(parents=True, exist_ok=True)
    md_path, pdf_path, md_sha, pdf_sha = _discover_source(settings)

    # 1. Record source manifest (inspection).
    report = run_inspection(md_path=md_path, pdf_path=pdf_path, md_sha256=md_sha, pdf_sha256=pdf_sha)

    # 2. Clean.
    source_text = Path(md_path).read_text(encoding="utf-8", errors="replace")
    result = clean_text(source_text)
    cleaned, line_map, counts = result.text, result.line_map, result.counts

    work = settings.paths.work_dir
    (work / "book.cleaned.md").write_text(cleaned, encoding="utf-8")
    with open(work / "line-map.jsonl", "w", encoding="utf-8") as fh:
        for entry in line_map:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    counts = result.counts
    report_payload = {
        "input_lines": counts.total_input_lines,
        "output_lines": counts.total_output_lines,
        "removed_watermark": counts.removed_watermark,
        "removed_page_header": counts.removed_page_header,
        "transform_counts": dict(counts.transform_counts),
        "generated_at": now_iso(),
    }
    (work / "cleanup-report.json").write_text(
        json.dumps(report_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    console.print(
        f"[green]cleaned[/green] {counts.total_input_lines} -> "
        f"{counts.total_output_lines} lines (watermarks: {counts.removed_watermark}, "
        f"page-headers: {counts.removed_page_header}) -> {work / 'book.cleaned.md'}"
    )
    return 0
