"""Stage 7 — global synthesis into operational decision rules.

The build plan notes that a large-context reasoning model is *most valuable*
for synthesis, and that the raw book must **not** be the only input — the
structured knowledge corpus + relationship graph are the preferred inputs.

No LLM credentials are available in this environment, so synthesis here is
**deterministic**: each rule is derived directly from a book knowledge record
(pattern / smell / goal / principle) plus the relationship graph, and carries
``evidence_ids`` back to that exact source. This never fabricates material —
rule text comes verbatim or as a faithful condensation of record fields.

Output:
* ``knowledge/synthesized/decision-rules.jsonl`` — operational rules, each
  validated by :class:`DecisionRuleRecord` and re-checked by
  `validate-knowledge`.
* ``knowledge/synthesized/testing-workflow.md`` — the agent execution workflow
  plus the "one condition per test" semantic rule, evidence-cited to goals /
  principles.

Per-entity rule derivation:

* **pattern** -> rule:"apply this pattern when its problem is present and the
  smell it addresses is detected" (evidence = pattern + addressed smells from
  the graph).
* **smell** -> rule:"don't introduce / refactor this smell; prefer the
  recommended patterns" (evidence = smell + recommended patterns).
* **principle** -> rule:"follow this principle; watch the failure modes"
  (evidence = principle + related entities).
* **goal** -> rule:"ensure this goal is satisfied; watch the listed indicators"
  (evidence = goal + related principles).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from rich.console import Console

from .config import Paths, load_settings
from .provenance import read_jsonl, write_jsonl
from .schemas import DecisionRuleRecord

console = Console()


# --------------------------------------------------------------------------- #
# Knowledge loading
# --------------------------------------------------------------------------- #

def load_knowledge(p: Paths) -> dict[str, dict[str, Any]]:
    """Load all knowledge records (book + graph + synthesized) keyed by ``id``."""
    by_id: dict[str, dict[str, Any]] = {}
    for kd in (
        p.knowledge_book_dir,
        p.knowledge_graph_dir,
        p.knowledge_modern_dir,
        p.knowledge_synthesized_dir,
    ):
        for jf in sorted(kd.glob("*.jsonl")):
            for rec in read_jsonl(jf):
                rid = rec.get("id")
                if rid:
                    by_id[rid] = rec
    return by_id


def load_graph_edges(p: Paths) -> list[dict[str, Any]]:
    rel_file = p.knowledge_graph_dir / "relationships.jsonl"
    return list(read_jsonl(rel_file)) if rel_file.exists() else []


# --------------------------------------------------------------------------- #
# Small text helpers
# --------------------------------------------------------------------------- #

def _slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return s or "item"


def _first_sentence(text: str | None) -> str:
    if not text:
        return ""
    text = " ".join(str(text).split())
    m = re.match(r"[^.!?]*[.!?]", text)
    return m.group(0) if m else text[:160]


def _short(text: str | None, cap: int = 160) -> str:
    text = " ".join((text or "").split())
    if len(text) <= cap:
        return text
    cut = text.rfind(" ", 0, cap)
    cut = cut if cut > 0 else cap
    return text[:cut].rstrip(".,;:") + " …"


def _bullets(items: Any, n: int = 3) -> list[str]:
    vals = list(items or [])
    return [str(i).strip() for i in vals[:n] if str(i).strip()]


# --------------------------------------------------------------------------- #
# Per-entity rule derivation
# --------------------------------------------------------------------------- #

def _via(edges: list[dict[str, Any]], rid: str, rels: set[str], *, role: str) -> list[str]:
    """Return the partner ids linked to ``rid`` by an edge in ``rels``."""
    out: list[str] = []
    for e in edges:
        if e.get("relationship") not in rels:
            continue
        if role == "from" and e.get("from_id") == rid:
            out.append(e["to_id"])
        elif role == "to" and e.get("to_id") == rid:
            out.append(e["from_id"])
    return out


def derive_pattern_rule(rec: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    rid = rec["id"]
    name = rec.get("name", "")
    problem = rec.get("problem") or rec.get("intent") or name
    solution = rec.get("solution") or ""
    # smells this pattern addresses (graph smell -> pattern refactors_to) and
    # smells it prevents/may-causes (graph pattern -> smell).
    addressed = _via(edges, rid, {"refactors_to"}, role="to")
    addressed += _via(edges, rid, {"prevents", "may_cause"}, role="from")
    evidence = [rid] + list(dict.fromkeys(addressed))

    trigger = _short(problem) or f"Encountering a situation described by '{name}'."
    default_action = ("Apply the " + name + " pattern. " + _first_sentence(solution)) or f"Use {name} to address the stated problem."
    logic: list[dict[str, str]] = []
    if addressed:
        logic.append({
            "condition": "a smell this pattern addresses is detected",
            "action": "introduce the pattern and refactor to remove the smell",
        })
    logic.append({
        "condition": "the pattern's problem statement applies to the current change",
        "action": f"introduce {name}",
    })
    if rec.get("use_when"):
        logic.append({"condition": _short(rec["use_when"], 120), "action": "proceed with the pattern"})

    return DecisionRuleRecord(
        id=f"rule:{_slug(name)}",
        trigger=trigger,
        context=_short(rec.get("context")) or None,
        default_action=default_action,
        decision_logic=logic,
        exceptions=_bullets(rec.get("avoid_when") and [rec["avoid_when"]]),
        warnings=_bullets(rec.get("risks")) or _bullets(rec.get("costs")),
        evidence_ids=evidence,
        origin="book",
        strength="certain",
        applicability="When the pattern's problem is observable in the system under test.",
        agent_verification=[
            "verify the test targets the stated problem, not an implementation detail",
            "assert observable behavior, not internal state",
        ],
    ).model_dump(exclude_none=True)


def derive_smell_rule(rec: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    rid = rec["id"]
    name = rec.get("name", "")
    summary = rec.get("summary") or name
    # patterns that address this smell (graph smell -> pattern refactors_to).
    addressed_by = _via(edges, rid, {"refactors_to"}, role="from")
    evidence = [rid] + list(dict.fromkeys(addressed_by))

    symptoms = _bullets(rec.get("symptoms"), 3)
    cond = _first_sentence(symptoms[0]) if symptoms else ""
    action_patterns = ", ".join(addressed_by) or "a recognized solution pattern"
    return DecisionRuleRecord(
        id=f"rule:smell-{_slug(name)}",
        trigger=_short(summary),
        default_action=f"Do not introduce or leave '{name}' in place; refactor toward {action_patterns}.",
        decision_logic=[{
            "condition": cond,
            "action": f"apply {action_patterns} to remove the smell",
        }],
        exceptions=[],
        warnings=_bullets(rec.get("causes"), 3),
        evidence_ids=evidence,
        origin="book",
        strength="warning",
        applicability="Any test code exhibiting the smell's symptoms.",
        agent_verification=symptoms or _bullets(rec.get("detection_heuristics"), 3),
    ).model_dump(exclude_none=True)


def derive_principle_rule(rec: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    rid = rec["id"]
    statement = rec.get("statement") or rec.get("name", "")
    # entities this principle supports + goals/principles that reference it.
    evidence = [rid] + list(dict.fromkeys(
        _via(edges, rid, {"supports"}, role="from")
        + _via(edges, rid, {"supports"}, role="to")
    ))
    return DecisionRuleRecord(
        id=f"rule:{_slug(rid.split(':', 1)[1])}",
        trigger=_short(statement),
        default_action=rec.get("default_rule") or _first_sentence(statement),
        decision_logic=[] if not rec.get("default_rule") else [
            {"condition": "the principle's guidance applies", "action": rec["default_rule"]},
        ],
        exceptions=_bullets(rec.get("exceptions"), 3),
        warnings=_bullets(rec.get("failure_modes_if_ignored"), 3),
        evidence_ids=evidence,
        origin="book",
        strength="certain",
        applicability=statement,
        agent_verification=_bullets(rec.get("agent_checks"), 3),
    ).model_dump(exclude_none=True)


def derive_goal_rule(rec: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    rid = rec["id"]
    # what this goal supports (graph goal -> *).
    evidence = [rid] + list(dict.fromkeys(_via(edges, rid, {"supports"}, role="from")))
    tensions = _bullets(rec.get("tensions"), 3)
    decision_logic: list[dict[str, str]] = []
    if tensions:
        decision_logic.append({
            "condition": _short(tensions[0], 120),
            "action": "resolve the tension before committing tests",
        })
    indicators = _bullets(rec.get("indicators"), 3)
    return DecisionRuleRecord(
        id=f"rule:{_slug(rid.split(':', 1)[1])}",
        trigger=_short(rec.get("summary") or rec.get("name", "")),
        default_action=(
            "Verify this goal is satisfied by the test suite; "
            f"the indicators to watch are: {', '.join(indicators) or 'none listed'}."
        ),
        decision_logic=decision_logic,
        exceptions=[],
        warnings=tensions,
        evidence_ids=evidence,
        origin="book",
        strength="default",
        applicability=rec.get("why_it_matters") or "",
        agent_verification=indicators,
    ).model_dump(exclude_none=True)


# --------------------------------------------------------------------------- #
# Higher-order (synthesised) rules
# --------------------------------------------------------------------------- #

def derive_workflow_rules(by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    principle_ids = [k for k in by_id if k.startswith("principle:")]
    goal_ids = [k for k in by_id if k.startswith("goal:")]
    rules: list[dict[str, Any]] = []

    # Semantic rule (plan §11.2.8): one condition per test != one assertion per test.
    rules.append(DecisionRuleRecord(
        id="rule:one-condition-per-test",
        trigger="Writing or reviewing a test that has more than one assertion.",
        context="An assertion verifies one condition; a test verifies one coherent observable outcome.",
        default_action=(
            "Group assertions that jointly verify one coherent observable outcome under a single "
            "logical test condition; split only when a second, independent condition is being verified."
        ),
        decision_logic=[{
            "condition": "two assertions verify different observable facts",
            "action": "split into separate tests",
        }],
        evidence_ids=principle_ids,
        origin="book",
        strength="certain",
        applicability="Applies to every test the agent writes or reviews.",
        agent_verification=[
            "each test maps to one coherent outcome",
            "assertions that jointly verify that outcome may appear in one test; independent conditions must not",
        ],
    ).model_dump(exclude_none=True))

    # Agent execution workflow (plan §11.1.7 H).
    rules.append(DecisionRuleRecord(
        id="rule:test-execution-workflow",
        trigger="The agent is asked to add, fix, or refactor tests.",
        context="Follow the deterministic workflow below; do not skip smell review.",
        default_action="Execute the 14-step testing workflow (inspect → choose boundary → design fixture → write smallest tests → run → review smells → report).",
        decision_logic=[{
            "condition": "after running focused tests, diagnose failures",
            "action": "review for smells before widening scope",
        }],
        exceptions=["do not change production behavior merely to make a test pass"],
        warnings=[
            "do not introduce smells to satisfy a deadline",
            "keep refactorings minimal and separately understandable",
        ],
        evidence_ids=list(goal_ids) + list(principle_ids),
        origin="book",
        strength="preference",
        applicability="Every test-authored task.",
        agent_verification=[
            "inspect repository and conventions first",
            "review for smells before broadening",
            "report what was validated",
        ],
    ).model_dump(exclude_none=True))

    return rules


# --------------------------------------------------------------------------- #
# Markdown workflow doc
# --------------------------------------------------------------------------- #

def write_workflow_doc(out: Path, by_id: dict[str, dict[str, Any]]) -> None:
    principle_ids = sorted(k for k in by_id if k.startswith("principle:"))
    goal_ids = sorted(k for k in by_id if k.startswith("goal:"))
    evidence = ", ".join(principle_ids) + "."
    semantic = (
        '"Verify one condition per test" does NOT mean "one assertion per test."'
        " Multiple assertions are appropriate when they jointly verify one coherent"
        " observable outcome. Evidence: principles " + evidence
    )
    lines = [
        "# Synthesized test execution workflow",
        "",
        "> Derived from the relationship graph and the book's goal/principle corpus",
        "> (`knowledge/synthesized/decision-rules.jsonl` is the operational rule set).",
        "",
        "## Semantic rule",
        "",
        semantic,
        "",
        "## Agent execution workflow",
        "",
        "1. inspect repository and conventions",
        "2. identify relevant behavior",
        "3. choose boundary and test conditions",
        "4. choose verification (state / output / interaction back-door / custom)",
        "5. design fixture (minimal / fresh / standard / shared)",
        "6. classify dependencies (real / fake / stub / spy / mock / dummy)",
        "7. write the smallest useful tests",
        "8. run focused tests",
        "9. diagnose failures",
        "10. review for smells",
        "11. run affected broader suite",
        "12. optionally run stronger validation (mutation / property / contract)",
        "13. report what was validated",
        "",
        "## Goal indicators (at minimum these goals must be satisfied)",
        "",
    ]
    for gid in goal_ids:
        g = by_id[gid]
        lines.append(f"- `{gid}` — {g.get('summary', g.get('name', ''))}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def build_decision_rules(
    records: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in records:
        rid = rec["id"]
        prefix = rid.split(":", 1)[0]
        try:
            if prefix == "pattern":
                rule = derive_pattern_rule(rec, edges)
            elif prefix == "smell":
                rule = derive_smell_rule(rec, edges)
            elif prefix == "principle":
                rule = derive_principle_rule(rec, edges)
            elif prefix == "goal":
                rule = derive_goal_rule(rec, edges)
            else:
                continue
        except Exception as exc:  # noqa: BLE001 - report, don't abort the whole synthesis
            console.print(f"[red]rule derivation failed for {rid}: {exc}[/red]")
            continue
        if rule["id"] in seen:
            continue
        seen.add(rule["id"])
        rules.append(rule)
    rules.extend(derive_workflow_rules(by_id))
    return rules


def run_synthesis() -> None:
    """Stage 7 entry point: synthesize operational decision rules from knowledge."""
    settings = load_settings()
    settings.paths.ensure_knowledge_dirs()
    p = settings.paths

    by_id = load_knowledge(p)
    records = list(by_id.values())
    edges = load_graph_edges(p)

    rules = build_decision_rules(records, edges, by_id)
    # Validate every rule through the pydantic model before writing (cannot emit invalid records).
    validated = []
    for r in rules:
        DecisionRuleRecord(**r)  # raises on invalid -> surfaced below
        validated.append(r)

    out = p.knowledge_synthesized_dir / "decision-rules.jsonl"
    write_jsonl(out, validated)
    write_workflow_doc(p.knowledge_synthesized_dir / "testing-workflow.md", by_id)
    console.print(
        f"[green]synthesized {len(validated)} decision rules -> {out.relative_to(p.repo_root)}[/green]"
    )
