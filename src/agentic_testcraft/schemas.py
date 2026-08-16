"""Pydantic models for the agentic-testcraft knowledge schemas.

These models are the canonical Python representation of the JSON Schemas in
``schemas/``.  They are used by extraction, synthesis and validation code so
that every knowledge artifact is validated the same way.

All book-derived models enforce provenance.  The ``origin`` field keeps the
book / modern split explicit (rule 4.2).
"""

from __future__ import annotations

import json
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator
from rich.console import Console

from .provenance import (
    VALID_ORIGINS,
    OriginLiteral,
    Provenance,
    SourceRef,
    ensure_book_provenance,
    read_jsonl,
)

Confidence = Literal[
    "default",
    "preference",
    "warning",
    "exception",
    "context_dependent",
    "historical",
    "certain",
]

# Strength for decision rules.
Strength = Confidence


class IdentifiedRecord(BaseModel):
    """Shared base: a stable, namespace-prefixed id plus provenance."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    id: str
    name: str
    origin: str = "book"
    confidence: Confidence = "default"
    aliases: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_provenance(self) -> IdentifiedRecord:
        if self.origin == "book":
            ensure_book_provenance(Provenance(origin=self.origin, source_refs=self.source_refs))
        return self


class KnowledgeRecord(IdentifiedRecord):
    """Records that carry source-faithful knowledge of the book."""

    problem: str | None = None
    summary: str | None = None
    statement: str | None = None


class GoalRecord(IdentifiedRecord):
    summary: str
    why_it_matters: str = ""
    indicators: list[str] = Field(default_factory=list)
    tensions: list[str] = Field(default_factory=list)
    related_principles: list[str] = Field(default_factory=list)
    confidence: Confidence = "default"


class PrincipleRecord(IdentifiedRecord):
    statement: str
    rationale: str = ""
    default_rule: str = ""
    exceptions: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    failure_modes_if_ignored: list[str] = Field(default_factory=list)
    related_patterns: list[str] = Field(default_factory=list)
    related_smells: list[str] = Field(default_factory=list)
    agent_checks: list[str] = Field(default_factory=list)


class SmellRecord(IdentifiedRecord):
    summary: str
    symptoms: list[str] = Field(default_factory=list)
    impact: list[str] = Field(default_factory=list)
    causes: list[str] = Field(default_factory=list)
    detection_heuristics: list[str] = Field(default_factory=list)
    false_positive_risks: list[str] = Field(default_factory=list)
    related_smells: list[str] = Field(default_factory=list)
    recommended_patterns: list[str] = Field(default_factory=list)
    agent_review_checks: list[str] = Field(default_factory=list)


class PatternRecord(IdentifiedRecord):
    category: str = ""
    problem: str
    solution: str
    intent: str | None = None
    context: str | None = None
    forces: list[str] = Field(default_factory=list)
    use_when: str | None = None
    avoid_when: str | None = None
    benefits: list[str] = Field(default_factory=list)
    costs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    implementation_variations: list[str] = Field(default_factory=list)
    related_patterns: list[str] = Field(default_factory=list)
    prevents_smells: list[str] = Field(default_factory=list)
    may_cause_smells: list[str] = Field(default_factory=list)
    refactorings: list[str] = Field(default_factory=list)
    agent_decision_rule: str | None = None
    agent_actions: list[str] = Field(default_factory=list)
    common_misinterpretations: list[str] = Field(default_factory=list)
    historical_or_framework_specific_notes: str | None = None


RelationshipType = Literal[
    "supports",
    "implements",
    "alternative_to",
    "variation_of",
    "specialization_of",
    "used_with",
    "prevents",
    "may_cause",
    "caused_by",
    "refactors_to",
    "requires",
    "conflicts_with",
    "preferred_over_when",
]
VALID_RELATIONSHIPS = get_args(RelationshipType)


class RelationshipRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_id: str
    relationship: RelationshipType
    to_id: str
    strength: str | None = None
    rationale: str | None = None
    source_refs: list[SourceRef] | None = None
    origin: str
    confidence: Confidence = "context_dependent"
    explicit: bool = False


# Strength classification for decision rules (kept separate from confidence).
RuleStrength = Confidence


class DecisionRuleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    trigger: str
    context: str | None = None
    default_action: str
    decision_logic: list[dict[str, str]] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    origin: str
    strength: RuleStrength = "default"
    applicability: str
    agent_verification: list[str] = Field(default_factory=list)


ModernizationStatus = Literal[
    "unchanged", "clarified", "expanded", "narrowed", "superseded", "historical"
]


class ModernizationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    topic: str
    book_position: str
    modern_position: str
    status: ModernizationStatus
    rationale: str
    official_sources: list[str] = Field(default_factory=list)
    affected_knowledge_ids: list[str] = Field(default_factory=list)
    agent_rule_change: str | None = None
    review_date: str
    modern_origin: str = "modern_official"


# --------------------------------------------------------------------------- #
# Pipeline-stage artifacts (not book knowledge): chunk manifest + reports.    #
# --------------------------------------------------------------------------- #

ChunkKind = Literal[
    "pattern",
    "code",
    "behavior",
    "project",
    "goal",
    "principle",
    "reference",
    "narrative",
]


class ChunkRecord(BaseModel):
    """One record from ``chunk-manifest.jsonl`` (Stage 3 output)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    id: str
    kind: ChunkKind
    chapter_kind: str
    chapter_title: str
    title: str
    category: str = ""
    clean_start_line: int = Field(ge=1)
    clean_end_line: int = Field(ge=1)
    source_refs: list[SourceRef] = Field(default_factory=list, min_length=1)
    subsections: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _bounds(self) -> ChunkRecord:
        if self.clean_end_line < self.clean_start_line:
            raise ValueError("clean_end_line must be >= clean_start_line")
        return self


class StructureReport(BaseModel):
    """Schema for ``structure.json`` (Stage 3 validity summary)."""

    model_config = ConfigDict(extra="forbid")

    file_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    generated_at: str | None = None
    chunk_count: int = Field(ge=0)
    by_kind: dict[str, int]
    by_chapter_kind: dict[str, int]
    completeness_problems: list[str] = Field(default_factory=list)


# Maps a knowledge record's ``id`` prefix to its enforcing pydantic model.
_KNOWLEDGE_MODELS: dict[str, type[BaseModel]] = {
    "pattern:": PatternRecord,
    "smell:": SmellRecord,
    "goal:": GoalRecord,
    "principle:": PrincipleRecord,
    "relationship:": RelationshipRecord,
    "decision-rule:": DecisionRuleRecord,
    "modern:": ModernizationRecord,
}


def _model_for_id(record_id: str) -> type[BaseModel] | None:
    for prefix, model in _KNOWLEDGE_MODELS.items():
        if record_id.startswith(prefix):
            return model
    return None


def run_validate_knowledge() -> None:
    """Stage 4 entry point: validate every knowledge artifact against its schema.

    Validates:
    * ``.local/work/chunk-manifest.jsonl`` -> :class:`ChunkRecord` (one per line)
    * ``.local/work/structure.json``      -> :class:`StructureReport`
    * ``knowledge/{book,graph,modern}/*.jsonl`` -> dispatched by ``id`` prefix
      to the matching knowledge model (:class:`PatternRecord`, :class:`SmellRecord`,
      :class:`GoalRecord`, :class:`PrincipleRecord`, :class:`RelationshipRecord`,
      :class:`DecisionRuleRecord`, :class:`ModernizationRecord`).

    Exits non-zero if any record fails validation.
    """
    from .config import load_settings

    settings = load_settings()
    p = settings.paths
    console = Console()
    errors: list[str] = []

    # 1) chunk manifest
    manifest = p.work_dir / "chunk-manifest.jsonl"
    if manifest.exists():
        recs = read_jsonl(manifest)
        ok = 0
        for i, r in enumerate(recs, 1):
            try:
                ChunkRecord(**r)
                ok += 1
            except Exception as exc:  # noqa: BLE001 - report, don't crash
                errors.append(f"chunk-manifest.jsonl[{i}] (id={r.get('id')}): {exc}")
        console.print(f"[bold]chunk-manifest.jsonl[/bold]: {ok}/{len(recs)} records valid")
    else:
        console.print("[yellow]chunk-manifest.jsonl[/yellow]: missing (run `split` first)")

    # 2) structure report
    srep = p.work_dir / "structure.json"
    if srep.exists():
        try:
            StructureReport(**json.loads(srep.read_text(encoding="utf-8")))
            console.print("[bold]structure.json[/bold]: valid")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"structure.json: {exc}")
    else:
        console.print("[yellow]structure.json[/yellow]: missing (run `split` first)")

    # 3) extracted knowledge
    knowledge_dirs = [p.knowledge_book_dir, p.knowledge_graph_dir, p.knowledge_modern_dir]
    for kd in knowledge_dirs:
        for jf in sorted(kd.glob("*.jsonl")):
            recs = read_jsonl(jf)
            ok = 0
            for i, r in enumerate(recs, 1):
                model = _model_for_id(r.get("id", ""))
                if model is None:
                    errors.append(f"{jf.name}[{i}]: unknown id prefix {r.get('id', '')!r}")
                    continue
                try:
                    model(**r)
                    ok += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{jf.name}[{i}] (id={r.get('id')}): {exc}")
            console.print(f"[bold]{jf.relative_to(p.repo_root)}[/bold]: {ok}/{len(recs)} records valid")

    if errors:
        console.print(f"[red]{len(errors)} validation error(s):[/red]")
        for e in errors:
            console.print(f"  - {e}")
        raise SystemExit(1)

    console.print("[green]all knowledge artifacts valid[/green]")


__all__ = [
    "ChunkKind",
    "ChunkRecord",
    "Confidence",
    "DecisionRuleRecord",
    "GoalRecord",
    "KnowledgeRecord",
    "ModernizationRecord",
    "ModernizationStatus",
    "PatternRecord",
    "PrincipleRecord",
    "RelationshipRecord",
    "RelationshipType",
    "SmellRecord",
    "SourceRef",
    "Strength",
    "VALID_RELATIONSHIPS",
    "VALID_ORIGINS",
    "OriginLiteral",
    "StructureReport",
    "run_validate_knowledge",
]
