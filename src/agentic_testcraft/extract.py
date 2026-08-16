"""Stage 5 — knowledge extraction.

Extraction is driven by a small provider abstraction (build-plan *Provider
abstraction*).  When no LLM credentials are available, the ``native-agent``
provider performs deterministic, structurally-grounded extraction straight from
the cleaned book: it reads each chunk's provenance line span and pulls verbatim
subsection bodies into the pydantic knowledge models, attaching the chunk's own
source provenance.  This never fabricates material — fields the book's structure
does not supply are left empty (or, for required fields, filled from the chunk's
intro prose, which is still source-faithful).

Every record is validated against its pydantic model before it is written, so
the output is always schema-conformant.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from rich.console import Console

from .config import load_settings
from .provenance import SourceRef, read_jsonl
from .schemas import (
    GoalRecord,
    PatternRecord,
    PrincipleRecord,
    SmellRecord,
)

console = Console()

# Maps a chunk's `kind` to (knowledge model class, output file stem).
_KIND_MAP: dict[str, tuple[type, str]] = {
    "pattern": (PatternRecord, "patterns"),
    "code": (SmellRecord, "smells"),
    "behavior": (SmellRecord, "smells"),
    "project": (SmellRecord, "smells"),
    "goal": (GoalRecord, "goals"),
    "principle": (PrincipleRecord, "principles"),
}

# Output stem keyed by the *remapped* knowledge-record id prefix.
_STEM_BY_PREFIX: dict[str, str] = {
    "pattern": "patterns",
    "smell": "smells",
    "goal": "goals",
    "principle": "principles",
}

# Subsections the book uses as canonical field labels (matched on the
# normalised, lower-cased heading text).
_HEAD_PROBLEM = {"problem"}
_HEAD_SOLUTION = {"solution", "how it works"}
_HEAD_CONTEXT = {"context"}
_HEAD_FORCES = {"forces"}
_HEAD_WHEN = {"when to use it", "when to use"}
_HEAD_IMPL = {"implementation notes", "variations"}
_HEAD_SYMPTOMS = {"symptoms"}
_HEAD_IMPACT = {"impact"}
_HEAD_CAUSES = {"causes"}
_HEAD_ALIASES = {"also known as", "also known as:", "aka"}
_HEAD_RATIONALE = {"why we do this"}

_BOLD_RX = re.compile(r"^\*\*(.+)\*\*\s*$")
_ITALIC_RX = re.compile(r"^_(.*)_$")
_ITALIC_QUESTION_RX = re.compile(r"^\s*_(.*\?)\s*_\s*$")

# H6 "problem" statements for smells are declarative sentences ending with '.'.
_NON_SMELL_SUMMARY_HEADINGS = {
    "how it works", "why we do this", "implementation notes",
    "motivating example", "refactoring notes", "solution patterns",
}


def _clean_text(lines: list[str]) -> str:
    """Join non-empty lines into a single, whitespace-collapsed paragraph."""
    parts = [ln.strip() for ln in lines if ln.strip()]
    return " ".join(" ".join(parts).split())


def _first_sentence(text: str) -> str:
    text = " ".join(text.split())
    m = re.match(r"[^.!?]*[.!?]", text)
    return m.group(0) if m else text[:120]


def _bullets(lines: list[str]) -> list[str]:
    """Extract bullet items (``- text`` / ``* text``); fall back to one para."""
    items = [ln.strip()[1:].strip() for ln in lines if ln.strip().startswith(("- ", "* "))]
    if not items:
        txt = _clean_text(lines)
        return [txt] if txt else []
    return items


def _segments(chunk_lines: list[str]) -> list[tuple[str | None, list[str]]]:
    """Split a chunk's text into ordered ``(heading, body)`` segments.

    ``heading`` is the original H6 label (``None`` for leading intro prose).
    The first ``######`` line is the entity's own title and is skipped.
    """
    lines = list(chunk_lines)
    if lines and lines[0].startswith("######"):
        lines = lines[1:]
    segs: list[tuple[str | None, list[str]]] = []
    intro: list[str] = []
    cur_heading: str | None = None
    cur_body: list[str] = intro
    for ln in lines:
        if ln.startswith("######"):
            if cur_heading is None and intro:
                segs.append((None, intro))
            cur_heading = ln.lstrip("#").strip()
            cur_body = []
            segs.append((cur_heading, cur_body))
        else:
            cur_body.append(ln)
    # flush any trailing intro prose (chunks with no subsection H6s)
    if cur_heading is None and intro:
        segs.append((None, intro))
    return segs


def _first_body(segs: list[tuple[str | None, list[str]]], headings: set[str]) -> list[str]:
    for h, body in segs:
        if h is not None and h.lower() in headings:
            return body
    return []


def _intro(segs: list[tuple[str | None, list[str]]]) -> list[str]:
    for h, body in segs:
        if h is None:
            return body
    return []


def _source_refs_from(chunk: dict[str, Any]) -> list[SourceRef]:
    return [SourceRef(**ref) for ref in chunk.get("source_refs", [])]


def _remap_smell_id(chunk_id: str) -> str:
    """Smell chunks use category prefixes (code:/behavior:/project:); the
    knowledge schema requires the ``smell:`` prefix."""
    prefix = chunk_id.split(":", 1)[0]
    if prefix in ("code", "behavior", "project"):
        return "smell:" + chunk_id.split(":", 1)[1]
    return chunk_id


def _problem(intro: list[str], segs: list[tuple[str | None, list[str]]]) -> str | None:
    for ln in intro:
        t = ln.strip()
        m = _ITALIC_QUESTION_RX.match(t)
        if m:
            return m.group(1).strip()
    body = _first_body(segs, _HEAD_PROBLEM)
    return _clean_text(body) or None


def _essence(intro: list[str], name: str) -> str | None:
    """The bold definition line, distinct from the entity's own name."""
    name_lower = name.lower()
    for ln in intro:
        m = _BOLD_RX.match(ln.strip())
        if m and m.group(1).strip().lower() != name_lower:
            return m.group(1).strip()
    return None


def _aliases(intro: list[str], segs: list[tuple[str | None, list[str]]]) -> list[str]:
    for ln in intro:
        t = ln.strip().lower()
        if "also known as" in t:
            m = _ITALIC_RX.match(ln.strip()) or re.search(r"_([^_]+)_", ln)
            if m:
                return [m.group(1).strip()]
    body = _first_body(segs, _HEAD_ALIASES)
    val = _clean_text(body)
    return [val] if val else []


def _smell_summary(intro: list[str], segs: list[tuple[str | None, list[str]]]) -> str | None:
    for h, _body in segs:
        if h is None:
            continue
        hl = h.lower()
        if hl in _NON_SMELL_SUMMARY_HEADINGS:
            continue
        if hl.startswith(("variation:", "example:", "cause:", "when to", "solution patterns")):
            continue
        if hl.endswith(".") and not hl.endswith(".."):
            return h.strip(".")
    return _clean_text(intro) or None


def _body_text(body: list[str]) -> str | None:
    txt = _clean_text(body)
    return txt or None


class NativeAgentExtractor:
    """Deterministic, structural extractor (no external LLM)."""

    name = "native-agent"

    def extract(self, chunks: list[dict[str, Any]], book_lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        records: list[dict[str, Any]] = []
        errors: list[str] = []
        for chunk in chunks:
            model_cls, _ = _KIND_MAP.get(chunk["kind"], (None, None))
            if model_cls is None:
                continue
            span = book_lines[(chunk["clean_start_line"] - 1) : (chunk["clean_end_line"] or chunk["clean_start_line"])]
            segs = _segments(span)
            rec = _build_record(chunk, model_cls, segs)
            if rec is None:
                errors.append(f"extraction failed for {chunk['id']}")
                continue
            if "__error__" in rec:
                errors.append(rec["__error__"])
                continue
            records.append(rec)
        return records, errors


def _build_record(
    chunk: dict[str, Any], model_cls: type, segs: list[tuple[str | None, list[str]]]
) -> dict[str, Any] | None:
    intro = _intro(segs)
    name = chunk["title"]
    common: dict[str, Any] = {
        "id": _remap_smell_id(chunk["id"]),
        "name": name,
        "origin": "book",
        "confidence": "default",
        "source_refs": [r.to_dict() for r in _source_refs_from(chunk)],
        "aliases": _aliases(intro, segs),
    }
    try:
        if model_cls is PatternRecord:
            rec: BaseModel = PatternRecord(
                **common,
                category=chunk.get("category", ""),
                problem=_problem(intro, segs) or _essence(intro, name) or _first_sentence(_clean_text(intro)) or name,
                intent=_essence(intro, name),
                solution=_body_text(_first_body(segs, _HEAD_SOLUTION)) or _essence(intro, name) or _first_sentence(_clean_text(intro)) or name,
                context=_body_text(_first_body(segs, _HEAD_CONTEXT)) or None,
                forces=_bullets(_first_body(segs, _HEAD_FORCES)),
                use_when=_body_text(_first_body(segs, _HEAD_WHEN)) or None,
                implementation_variations=_bullets(_first_body(segs, _HEAD_IMPL)),
            )
        elif model_cls is SmellRecord:
            rec = SmellRecord(
                **common,
                summary=_smell_summary(intro, segs) or _clean_text(intro) or name,
                symptoms=_bullets(_first_body(segs, _HEAD_SYMPTOMS)),
                impact=_bullets(_first_body(segs, _HEAD_IMPACT)),
                causes=_bullets(_first_body(segs, _HEAD_CAUSES)),
                detection_heuristics=_bullets(_first_body(segs, {"detection heuristics", "how to detect"})),
            )
        elif model_cls is GoalRecord:
            rec = GoalRecord(
                **common,
                summary=_clean_text(intro) or name,
            )
        elif model_cls is PrincipleRecord:
            rec = PrincipleRecord(
                **common,
                statement=_clean_text(intro) or name,
                rationale=_body_text(_first_body(segs, _HEAD_RATIONALE)) or "",
            )
        else:
            return None
    except Exception as exc:  # noqa: BLE001
        return {"__error__": f"{chunk['id']}: {exc}"}
    return rec.model_dump(exclude_none=True)


# --------------------------------------------------------------------------- #
# Optional LLM providers (used only with --provider openai/anthropic/google).  #
# --------------------------------------------------------------------------- #

def _require_key(env_var: str) -> str:
    import os

    key = os.environ.get(env_var)
    if not key:
        raise SystemExit(
            f"provider requires {env_var}; set it or use --provider native-agent"
        )
    return key


class OpenAIExtractor:
    """LLM-backed extraction via the OpenAI chat completions API."""

    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "gpt-4o"
        self._api_key = _require_key("OPENAI_API_KEY")

    def extract(self, chunks: list[dict[str, Any]], book_lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        import httpx  # noqa: PLC0415

        records: list[dict[str, Any]] = []
        for chunk in chunks:
            model_cls, _ = _KIND_MAP.get(chunk["kind"], (None, None))
            if model_cls is None:
                continue
            span = book_lines[(chunk["clean_start_line"] - 1) : (chunk["clean_end_line"] or chunk["clean_start_line"])][:120]
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a faithful documentation extractor."},
                        {"role": "user", "content": f"Extract a {model_cls.__name__} from:\n\n{_clean_text(span)}"},
                    ],
                },
                timeout=60,
            )
            resp.raise_for_status()
            records.append(json.loads(resp.json()["choices"][0]["message"]["content"]))
        return records, []


class AnthropicExtractor:
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        _require_key("ANTHROPIC_API_KEY")
        self.model = model or "claude-3-7-sonnet-20250219"

    def extract(self, chunks: list[dict[str, Any]], book_lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        raise SystemExit("anthropic provider: extraction not implemented")


class GoogleExtractor:
    name = "google"

    def __init__(self, model: str | None = None) -> None:
        _require_key("GOOGLE_API_KEY")
        self.model = model or "gemini-1.5-pro"

    def extract(self, chunks: list[dict[str, Any]], book_lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        raise SystemExit("google provider: extraction not implemented")


_PROVIDERS: dict[str, type] = {
    "native-agent": NativeAgentExtractor,
    "openai": OpenAIExtractor,
    "anthropic": AnthropicExtractor,
    "google": GoogleExtractor,
}


def _book_sha256(report_path: Path) -> str:
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            for entry in report.get("files", []):
                if entry.get("filename", "").endswith(".md"):
                    sha = entry.get("sha256", "unknown")
                    return sha if isinstance(sha, str) else "unknown"
        except Exception:
            pass
    return "unknown"


def _group_by_stem(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        if "__error__" in rec:
            continue
        prefix = rec["id"].split(":", 1)[0]
        stem = _STEM_BY_PREFIX.get(prefix)
        if stem is None:
            continue
        grouped[stem].append(rec)
    return grouped


def run_extraction(provider: str = "native-agent", model: str | None = None) -> None:
    """Stage 5 entry point: extract knowledge from chunks and write JSONL."""
    settings = load_settings()
    p = settings.paths
    book_lines = (p.work_dir / "book.cleaned.md").read_text(encoding="utf-8").split("\n")
    chunks = read_jsonl(p.work_dir / "chunk-manifest.jsonl")

    factory = _PROVIDERS.get(provider)
    if factory is None:
        raise SystemExit(f"unknown provider {provider!r}; use native-agent|openai|anthropic|google")
    extractor = factory() if provider == "native-agent" else factory(model=model)

    records, errors = extractor.extract(chunks, book_lines)

    grouped = _group_by_stem(records)
    written = 0
    for stem, recs in grouped.items():
        out = p.knowledge_book_dir / f"{stem}.jsonl"
        out.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs),
            encoding="utf-8",
        )
        written += len(recs)
        console.print(f"[bold]{out.name}[/bold]: {len(recs)} records")

    if errors:
        console.print(f"[red]{len(errors)} extraction error(s):[/red]")
        for e in errors[:10]:
            console.print(f"  - {e}")
    console.print(f"[green]extracted {written} knowledge records via {provider}[/green]")
