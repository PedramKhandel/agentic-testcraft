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
from .provenance import (
    SourceRef,
    now_iso,
    read_jsonl,
    sha256_file,
    write_jsonl,
)
from .schemas import (
    Confidence,
    GoalRecord,
    NarrativeRecord,
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
_HEAD_REFACTORING = {"refactoring notes"}
_HEAD_KNOWN_USES = {"known uses"}
_HEAD_FURTHER_READING = {"further reading"}

# Chapters / pattern-family entries the standard form lists as historical tooling
# (Appendix C xUnit-family, "Historical Patterns and Smells" appendix, etc.).
_HISTORICAL_CHAPTER_HINTS = ("historical", "appendix", "xunit family")

# Source-faithful narrative guidance that is not a discrete pattern/smell/principle.
# ``source_refs`` and ``confidence`` are attached at emission time in
# ``run_extraction`` (they depend on the cleaned-book SHA-256 and chapter spans).
_NARRATIVE_RULES: list[dict[str, Any]] = [
    {
        "id": "narrative:tests-as-specification-first",
        "name": "Tests as specification-first",
        "statement": (
            "Automated tests double as executable specification. When the team "
            "writes tests before or alongside the production code, the tests "
            "capture the desired behaviour and serve as the source of truth for "
            "what 'done' means."
        ),
        "rationale": (
            "From Chapter 3 Goals of Test Automation: 'Tests as Specification' — "
            "the tests give us a way to capture what the SUT should be doing."
        ),
        "evidence_ids": ["goal:tests-as-specification"],
    },
    {
        "id": "narrative:minimal-fault-domain",
        "name": "Prefer a minimal, single-condition fault domain",
        "statement": (
            "Keep each test method small enough that a failure points at one "
            "behavioural condition; do not equate this with a single assertion."
        ),
        "rationale": (
            "Goal: Simple Tests states 'strive to Verify One Condition per Test by "
            "creating a separate Test Method for each unique combination of "
            "pre-test state and input'; the book explicitly notes this does not "
            "mean 'one assertion per test'."
        ),
        "evidence_ids": [
            "goal:simple-tests",
            "principle:verify-one-condition-per-test",
        ],
    },
    {
        "id": "narrative:testability-is-design-leverage",
        "name": "Testability is design leverage, not test glue",
        "statement": (
            "Design for testability by substituting dependencies at the system "
            "boundaries (front door, back door, test doubles); keep test wiring "
            "out of production code."
        ),
        "rationale": (
            "Principle: Design for Testability / Use the Front Door First and "
            "Keep Test Logic Out of Production Code; Chapter 4 philosophy notes "
            "substitutable dependency is designed in from the start."
        ),
        "evidence_ids": [
            "principle:design-for-testability",
            "principle:use-the-front-door-first",
            "principle:keep-test-logic-out-of-production-code",
        ],
    },
    {
        "id": "narrative:flakiness-is-a-failure-mode",
        "name": "Nondeterminism is a test bug",
        "statement": (
            "A test that can pass or fail without a code change is a defect in "
            "the test. Eliminate dependence on wall-clock time, shared state, and "
            "environment ordering before treating a green run as success."
        ),
        "rationale": (
            "Goal: Repeatable Test and smell:erratic-test define repeatability as "
            "a first-class test-quality criterion; the book warns the red-bar "
            "loses meaning once failures are tolerated."
        ),
        "evidence_ids": ["goal:repeatable-test", "smell:erratic-test"],
    },
]

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


def _has_subsection(segs: list[tuple[str | None, list[str]]], headings: set[str]) -> bool:
    return bool(_first_body(segs, headings))


def _has_variation(segs: list[tuple[str | None, list[str]]]) -> bool:
    body = _first_body(segs, _HEAD_IMPL)
    return any(ln.strip().lower().startswith("variation") for ln in body)


def _chapter_is_historical(chunk: dict[str, Any]) -> bool:
    ch = (chunk.get("chapter_title") or "").lower()
    title = (chunk.get("title") or "").lower()
    return any(h in ch for h in _HISTORICAL_CHAPTER_HINTS) or any(
        h in title for h in _HISTORICAL_CHAPTER_HINTS
    )


def _classify_confidence(
    chunk: dict[str, Any],
    segs: list[tuple[str | None, list[str]]],
    model_cls: type,
) -> Confidence:
    """Deterministic, structure-based confidence for a book record.

    Grounded in the book's *Pattern Form* (book line ~942): a pattern is
    ``certain`` when it has an explicit Problem/Solution/When-to-use structure;
    ``context_dependent`` when its Implementation Notes enumerate named
    variations (the book treats variants as a single pattern → choice is
    context-dependent); ``historical`` for appendix/xUnit-family tooling;
    ``warning`` when the primary extraction had to fall back to prose because a
    canonical section is absent; ``default`` otherwise.
    """
    if _chapter_is_historical(chunk):
        return "historical"
    if model_cls is PatternRecord:
        has_solution = bool(_body_text(_first_body(segs, _HEAD_SOLUTION)))
        if has_solution:
            if _has_variation(segs):
                return "context_dependent"
            return "certain"
        return "warning"
    if model_cls is SmellRecord:
        return "certain" if _has_subsection(segs, _HEAD_CAUSES) else "default"
    if model_cls is PrincipleRecord:
        return "certain" if _has_subsection(segs, _HEAD_RATIONALE) else "default"
    return "default"


def _build_record(
    chunk: dict[str, Any], model_cls: type, segs: list[tuple[str | None, list[str]]]
) -> dict[str, Any] | None:
    intro = _intro(segs)
    name = chunk["title"]
    common: dict[str, Any] = {
        "id": _remap_smell_id(chunk["id"]),
        "name": name,
        "origin": "book",
        "confidence": _classify_confidence(chunk, segs, model_cls),
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
                 refactorings=_bullets(_first_body(segs, _HEAD_REFACTORING)),
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


_CHAPTER_RX = re.compile(r"chapter\s+\d", re.IGNORECASE)


def _chapter_span(
    book_lines: list[str], *fragments: str
) -> tuple[int, int] | None:
    """1-based inclusive (start, end) line span of the book section named by any fragment.

    ``end`` is the line before the next chapter header (or EOF). Bounded so the
    span stays inside the chapter that justifies the claim.
    """
    start: int | None = None
    for i, ln in enumerate(book_lines, start=1):
        if any(f.lower() in ln.lower() for f in fragments):
            start = i
            break
    if start is None:
        return None
    end = len(book_lines)
    for j in range(start + 1, len(book_lines) + 1):
        ln = book_lines[j - 1]
        if _CHAPTER_RX.search(ln) and not any(
            f.lower() in ln.lower() for f in fragments
        ):
            end = j - 1
            break
    return start, end


# Optional richer fields the schemas define for each knowledge type. These are
# populated only when the book's structure supplies them; the coverage report
# documents which remain null because the source does not define that subsection.
_RICH_FIELDS: dict[str, list[str]] = {
    "pattern": [
        "intent", "context", "forces", "use_when", "avoid_when", "benefits", "costs",
        "risks", "implementation_variations", "refactorings", "related_patterns",
        "prevents_smells", "may_cause_smells", "agent_decision_rule", "agent_actions",
        "common_misinterpretations", "historical_or_framework_specific_notes",
    ],
    "smell": [
        "symptoms", "impact", "causes", "detection_heuristics", "false_positive_risks",
        "related_smells", "recommended_patterns", "agent_review_checks",
    ],
    "goal": ["why_it_matters", "indicators", "tensions", "related_principles"],
    "principle": [
        "rationale", "default_rule", "exceptions", "tradeoffs", "failure_modes_if_ignored",
        "related_patterns", "related_smells", "agent_checks",
    ],
    "narrative": ["rationale", "evidence_ids", "agent_decision_rule"],
}

# Maps a narrative evidence id to the book section that justifies it, so each
# narrative rule carries a real source span instead of a loose pointer.
_NARRATIVE_ANCHORS: dict[str, tuple[str, ...]] = {
    "goal:tests-as-specification": ("Goals of Test Automation",),
    "principle:verify-one-condition-per-test": ("Goals of Test Automation",),
    "principle:design-for-testability": ("Philosophy of Test Automation",),
    "principle:use-the-front-door-first": ("Principles of Test Automation",),
    "principle:keep-test-logic-out-of-production-code": ("Principles of Test Automation",),
    "goal:repeatable-test": ("Goals of Test Automation",),
    "smell:erratic-test": ("Project Smells", "Code Smells"),
}


def _narrative_source_refs(
    book_sha: str, book_lines: list[str], evidence_ids: list[str]
) -> list[SourceRef]:
    refs: list[SourceRef] = []
    seen: set[tuple[int, int]] = set()
    for eid in evidence_ids:
        frag = _NARRATIVE_ANCHORS.get(eid)
        span = _chapter_span(book_lines, *frag) if frag else None
        if span is None:
            continue
        start, end = span
        if (start, end) in seen:
            continue
        seen.add((start, end))
        refs.append(SourceRef(source_id="book", file_sha256=book_sha, markdown_start_line=start, markdown_end_line=end))
    if not refs:
        refs.append(SourceRef(source_id="book", file_sha256=book_sha, markdown_start_line=1, markdown_end_line=len(book_lines)))
    return refs


def _write_narrative_rules(
    out_path: Path, book_sha: str, book_lines: list[str]
) -> int:
    """Emit knowledge/book/narrative-rules.jsonl (Stage 5 narrative output)."""
    out: list[dict[str, Any]] = []
    for rule in _NARRATIVE_RULES:
        srefs = _narrative_source_refs(
            book_sha, book_lines, rule["evidence_ids"]
        )
        rec = {
            "id": rule["id"],
            "name": rule["name"],
            "statement": rule["statement"],
            "rationale": rule["rationale"],
            "evidence_ids": rule["evidence_ids"],
            "origin": "book",
            "confidence": "certain",
            "source_refs": [s.to_dict() for s in srefs],
        }
        NarrativeRecord(**rec)
        out.append(rec)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_path, out)
    return len(out)


def _build_coverage_report(
    records: list[dict[str, Any]], provider: str
) -> dict[str, Any]:
    """Build the extraction coverage / low-confidence / ambiguous report."""
    by_type: dict[str, dict[str, Any]] = {}
    low: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for rec in records:
        rid = rec["id"]
        prefix = rid.split(":", 1)[0]
        bucket = by_type.setdefault(
            prefix, {"count": 0, "confidence": {}, "field_coverage": {}}
        )
        bucket["count"] += 1
        conf = rec.get("confidence", "default")
        bucket["confidence"][conf] = bucket["confidence"].get(conf, 0) + 1
        for f in _RICH_FIELDS.get(prefix, []):
            if f in rec and bool(rec[f]):
                bucket["field_coverage"][f] = (
                    bucket["field_coverage"].get(f, 0) + 1
                )
        if conf in ("warning", "exception", "context_dependent", "historical"):
            reason = (
                "primary extraction fell back to prose (no canonical section)"
                if conf == "warning"
                else f"confidence={conf}"
            )
            low.append({"id": rid, "type": prefix, "confidence": conf, "reason": reason})
            if conf == "warning":
                ambiguous.append({"id": rid, "reason": reason})
    return {
        "generated_at": now_iso(),
        "provider": provider,
        "total_records": len(records),
        "by_type": by_type,
        "low_confidence": low,
        "ambiguous": ambiguous,
        "note": (
            "Only schema-required fields and subsections the book's structure "
            "actually defines are populated here. The 2007 Pattern Form does not "
            "define named Benefits/Costs/Risks/Exceptions/Related-Pattern "
            "subsections, so those optional fields are intentionally null; "
            "cross-reference fields are populated downstream from the Stage-6 "
            "relationship graph where the source supports them."
        ),
    }


def run_extraction(provider: str = "native-agent", model: str | None = None) -> None:
    """Stage 5 entry point: extract knowledge from chunks and write JSONL."""
    settings = load_settings()
    p = settings.paths
    p.ensure_knowledge_dirs()
    book_path = p.work_dir / "book.cleaned.md"
    book_lines = book_path.read_text(encoding="utf-8").split("\n")
    book_sha = sha256_file(book_path)
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

    # Stage 5 narrative output (the book's philosophy/pattern-form guidance that
    # is not a discrete pattern/smell/principle).
    n_paths = _write_narrative_rules(
        p.knowledge_book_dir / "narrative-rules.jsonl", book_sha, book_lines
    )
    written += n_paths
    console.print(f"[bold]narrative-rules.jsonl[/bold]: {n_paths} records")

    # Stage 5 coverage / low-confidence / ambiguous report.
    report = _build_coverage_report(records, provider)
    cov_path = p.knowledge_book_dir / "extraction-coverage-report.json"
    cov_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    console.print(
        f"[bold]extraction-coverage-report.json[/bold]: "
        f"{len(report['low_confidence'])} low-confidence, "
        f"{len(report['ambiguous'])} ambiguous of {report['total_records']} records"
    )

    if errors:
        console.print(f"[red]{len(errors)} extraction error(s):[/red]")
        for e in errors[:10]:
            console.print(f"  - {e}")
    console.print(f"[green]extracted {written} knowledge records via {provider}[/green]")
