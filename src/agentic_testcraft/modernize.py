"""Stage 8 — modernize source-derived guidance with current primary/official sources.

The build plan prefers a frontier reasoning model for this stage, but no LLM is
available here. Instead, modernization records are produced from direct
research of authoritative primary/official documentation, each carrying an exact
URL and a review date. Every `ModernizationRecord` is validated through its
pydantic model (which enforces absolute-URL `official_sources` and a
`YYYY-MM-DD` `review_date`) before it is written, and is re-checked by
`validate-knowledge`.

Modernization records are deliberately compact (no long book quotations): they
state the **book position**, the **modern position**, a **status**
(`unchanged`/`clarified`/`expanded`/`narrowed`/`superseded`/`historical`), a
**rationale**, one or more **official_sources** URLs, the
**affected_knowledge_ids** (real ids from M5), and an optional **agent_rule_change**.

Records are grouped by category for the markdown digest at
`knowledge/modern/current-testing-practices.md`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from rich.console import Console

from .config import load_settings
from .provenance import write_jsonl
from .schemas import ModernizationRecord, ModernizationStatus

console = Console()

# Today's date, recorded in artifacts per Stage 8 ("current date recorded").
REVIEW_DATE = "2026-08-17"


class _ModItem(NamedTuple):
    record: dict[str, Any]
    category: str


def _rec(
    id: str,
    topic: str,
    book_position: str,
    modern_position: str,
    status: ModernizationStatus,
    rationale: str,
    sources: list[str],
    affected: list[str],
    rule_change: str | None = None,
) -> dict[str, Any]:
    return ModernizationRecord(
        id=id,
        topic=topic,
        book_position=book_position,
        modern_position=modern_position,
        status=status,
        rationale=rationale,
        official_sources=sources,
        affected_knowledge_ids=affected,
        agent_rule_change=rule_change,
        review_date=REVIEW_DATE,
    ).model_dump(exclude_none=True)


# --------------------------------------------------------------------------- #
# M8a — Runtime and determinism (async/await, clocks, randomness, flakiness)  #
# --------------------------------------------------------------------------- #

_M8A: list[_ModItem] = [
    _ModItem(
        _rec(
            id="modern:async-test-support",
            topic="Async/await test execution",
            book_position=(
                "The 2007 xUnit patterns were written before async/await (PEP 492, "
                "2015); Test Method / Test Runner / Assertion Method assume "
                "synchronous method calls."
            ),
            modern_position=(
                "Modern suites exercise coroutines via an async-aware runner. "
                "pytest-asyncio 'provides support for coroutines as test functions. "
                "This allows users to await code inside their tests' (e.g. "
                "@pytest.mark.asyncio), or stdlib unittest.IsolatedAsyncioTestCase. "
                "Awaiting inside a plain synchronous test yields a coroutine and "
                "silently skips the assertion."
            ),
            status="expanded",
            rationale=(
                "async/await did not exist in 2007; the book's patterns give no "
                "mechanism to await coroutines. Without an async runner, assertions "
                "on awaited results never execute."
            ),
            sources=["https://pytest-asyncio.readthedocs.io/en/latest/"],
            affected=[
                "pattern:recorded-test",
                "pattern:test-method",
                "pattern:test-runner",
                "principle:design-for-testability",
            ],
            rule_change=(
                "When a test must await a coroutine, declare it async and run it "
                "through an async-capable runner (pytest-asyncio or "
                "unittest.IsolatedAsyncioTestCase); do not synchronously unwrap "
                "coroutines with the synchronous front-door patterns."
            ),
        ),
        "Runtime and determinism",
    ),
    _ModItem(
        _rec(
            id="modern:deterministic-time",
            topic="Deterministic time / virtual clocks",
            book_position=(
                "Tests may call real time directly (e.g. timestamp comparisons "
                "inside Test Method); the book offers no mechanism to freeze the "
                "clock."
            ),
            modern_position=(
                "Tests must not depend on wall-clock time. Use a time-mocking tool "
                "such as time-machine, which is 'a tool for mocking the time in "
                "tests' and patches datetime/time so date-time logic becomes "
                "deterministic (via @time_machine.travel or its pytest plugin)."
            ),
            status="clarified",
            rationale=(
                "Letting the real clock into a test makes outcomes nondeterministic "
                "(slow / flaky tests). Freezing time keeps time-dependent behavior "
                "reproducible."
            ),
            sources=["https://time-machine.readthedocs.io/en/latest/"],
            affected=[
                "smell:erratic-test",
                "smell:fragile-test",
                "principle:isolate-the-sut",
                "pattern:transaction-rollback-teardown",
            ],
            rule_change=(
                "For any test touching the clock, freeze time deterministically with "
                "time-machine (or equivalent); never let date/time calls read the live "
                "clock."
            ),
        ),
        "Runtime and determinism",
    ),
    _ModItem(
        _rec(
            id="modern:flaky-as-fatal",
            topic="Flaky tests are a fatal error, not retried",
            book_position=(
                "The book names erratic / fragile tests and recommends refactoring, "
                "but modern tooling makes flakiness a hard failure rather than "
                "something to suppress."
            ),
            modern_position=(
                "Modern tooling treats flaky tests as fatal. Hypothesis: 'A flaky "
                "test is one which might behave differently when called again... not "
                "deterministic', and it 'raises an exception when it detects "
                "flakiness' because 'Hypothesis relies on deterministic behavior "
                "for the database to work.' Common sources: global state, "
                "filesystem/database state not reset between inputs, and 'un-managed "
                "sources of randomness... thread scheduling, network timing.' Fix by "
                "removing external-state dependence, not by retrying."
            ),
            status="expanded",
            rationale=(
                "Retrying masks real nondeterminism and breaks Hypothesis example "
                "database / shrinking. The modern stance (fix-then-pass) is stricter "
                "than 2007 and aligns with keep-tests-independent and repeated-test, "
                "but enforces it."
            ),
            sources=["https://hypothesis.readthedocs.io/en/latest/tutorial/flaky.html"],
            affected=[
                "smell:erratic-test",
                "smell:fragile-test",
                "principle:keep-tests-independent",
                "goal:repeatable-test",
                "principle:isolate-the-sut",
                "pattern:generated-value",
            ],
            rule_change=(
                "Do not add retry/suppression to silence a flaky test. Refactor to "
                "remove external-state dependence and reset shared state between "
                "inputs; treat flaky tests as failures to fix."
            ),
        ),
        "Runtime and determinism",
    ),
]

MODERN_RECORDS: list[dict[str, Any]] = [item.record for item in _M8A]
_MODERN_CATEGORIES: dict[str, str] = {item.record["id"]: item.category for item in _M8A}


# --------------------------------------------------------------------------- #
# Markdown digest                                                               #
# --------------------------------------------------------------------------- #

def _write_digest(out: Path, records: list[dict[str, Any]]) -> None:
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_cat.setdefault(_MODERN_CATEGORIES.get(r["id"], "Other"), []).append(r)
    lines: list[str] = ["# Current testing practices (modernization summary)", ""]
    lines.append(
        f"_Review date: `{REVIEW_DATE}`. Derived from authoritative primary/"
        "official documentation; book-derived principles remain distinguishable "
        "(`origin` field on each knowledge record)._ "
    )
    lines.append("")
    for cat in sorted(by_cat):
        lines.append(f"## {cat}")
        lines.append("")
        for r in by_cat[cat]:
            lines.append(f"### {r['topic']}")
            lines.append(f"- **Book position:** {r['book_position']}")
            lines.append(f"- **Modern position:** {r['modern_position']}")
            lines.append(f"- **Status:** `{r['status']}`")
            lines.append(f"- **Rationale:** {r['rationale']}")
            lines.append("- **Sources:** " + ", ".join(r.get("official_sources", [])))
            lines.append(
                "- **Affected knowledge:** " + ", ".join(r.get("affected_knowledge_ids", []))
            )
            if r.get("agent_rule_change"):
                lines.append(f"- **Agent rule change:** {r['agent_rule_change']}")
            lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Entry point                                                                   #
# --------------------------------------------------------------------------- #

def run_modernization() -> None:
    """Stage 8 entry point: emit validated modernization records from research."""
    settings = load_settings()
    settings.paths.ensure_knowledge_dirs()
    p = settings.paths

    records = list(MODERN_RECORDS)
    # Every record is constructed through ModernizationRecord above, so it is
    # already schema-valid; re-validate explicitly to fail fast on any drift.
    for r in records:
        ModernizationRecord(**r)

    out = p.knowledge_modern_dir / "modernization.jsonl"
    write_jsonl(out, records)
    _write_digest(p.knowledge_modern_dir / "current-testing-practices.md", records)
    console.print(
        f"[green]modernized {len(records)} records -> {out.relative_to(p.repo_root)}[/green]"
    )
