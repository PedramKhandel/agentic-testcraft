"""Pydantic models for the agentic-testcraft knowledge schemas.

These models are the canonical Python representation of the JSON Schemas in
``schemas/``.  They are used by extraction, synthesis and validation code so
that every knowledge artifact is validated the same way.

All book-derived models enforce provenance.  The ``origin`` field keeps the
book / modern split explicit (rule 4.2).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .provenance import (
    VALID_ORIGINS,
    OriginLiteral,
    Provenance,
    SourceRef,
    ensure_book_provenance,
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
    def _check_provenance(self) -> "IdentifiedRecord":
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
VALID_RELATIONSHIPS = RelationshipType.__args__


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


__all__ = [
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
    "Strength",
    "VALID_RELATIONSHIPS",
    "VALID_ORIGINS",
    "OriginLiteral",
]
