# Decision: Modernization ↔ Skill-Spec Compatibility

**Status:** accepted
**Context:** M8 modernization produced 13 `modern:*` records (`knowledge/modern/`).
This record verifies they align with the authoring target in
`docs/skill-spec.md` (decision rules R1–R8 and acceptance criterion 6.13:
"All major rules map to evidence IDs (synthesized → book/modern)").

## Method

Map each skill-spec rule to the modernization record(s) that justify or refine
it, and flag gaps.

## Findings

| Skill rule | Modernization basis | Status |
|---|---|---|
| R1 — Verify through behavior, not implementation | `modern:contract-testing` (Pact = interaction-as-observable-contract at the service boundary) refines where interaction *is* the contract | aligned / refined |
| R2 — One condition ≠ one assertion | Unchanged by M8; `modern:mutation-testing` sharpens this: a surviving mutant means an assertion is *missing*, reinforcing "verify the real condition" | aligned |
| R3 — Smallest useful boundary | `modern:disposable-integration-containers` (per-test container) + `modern:hermetic-integration` (function-scoped teardown) make the smallest boundary cheap, supporting R3 | aligned |
| R4 — Dependency replacement is goal-driven | `modern:disposable-integration-containers` (real, isolated service instead of a shared DB double) + `modern:contract-testing` (contract over end-to-end double) give concrete "keep the real dependency when fast/deterministic/safe" guidance | aligned |
| R5 — Fixture minimality | `modern:hermetic-integration` (default function scope) + `modern:disposable-integration-containers` (no shared state) operationalize "fresh per test" | aligned |
| R6 — Guarded testability refactoring | `modern:async-test-support` (await coroutines through an async runner, not test-only forks) prevents `if testing` style bypasses; `modern:deterministic-time` enables time-based refactors to be verified | aligned |
| R7 — Effectiveness validation | `modern:mutation-testing`, `modern:property-based-testing`, `modern:fuzz-testing`, `modern:contract-testing` directly implement the "mutation / property-based / fault seeding" R7 trigger, with tool names and workflow (`mutmut run`, Hypothesis properties, `--splits`) | aligned |
| R8 — Smell-driven review | `modern:flaky-as-fatal` narrows `smell:erratic-test`/`smell:fragile-test`: flakiness is corrected, not retried — feeding R8's smell catalog | aligned |

## Acceptance-criterion 6.13 (evidence mapping)

Every modern record maps to real book `id`s (patterns/principles/goals/smells),
so the final skill can cite both a book principle (`origin:"book"`) and a
moderning record (`origin:"modern"`) for each decision. No modern record
introduces a claim without an `official_sources` URL + review date.

## Gaps to watch

- **Platform/skill manifest:** M8 confirms *which* modern tools, but the final
  skill must still confirm the target agent's extension manifest constraints
  (see AGENTIC_TESTCRAFT_BUILD.md Stage 8 "Research current skill specifications").
  The tool-agnostic `agent_rule_change` per record is manifest-safe, but
  framework-specific CLI flags (`-n auto`, `mutmut run`) are documented as
  *examples*, not hard dependencies.
- **Windows caveats:** `mutmut` and `atheris` are Linux/macOS-primary; the
  rules state this but the skill must keep equivalent fallbacks (e.g.,
  `pytest-randomly` + manual fuzzing for mutation on Windows) so the judgment
  travel holds across platforms.
- **CI coupling:** `modern:ci-parallel-execution` and
  `modern:monorepo-suite-partitioning` describe CI mechanics; the skill must
  keep these as *recommendations* (not requirements), since not every project
  has a CI matrix.

## Conclusion

M8 modernization is **compatible** with the skill authoring target. R7 is the
strongest win — the test-effectiveness records give the agent concrete,
tool-named actions for effectiveness validation. No record conflicts with
R1–R8 or acceptance criteria; the gaps above are tracked for M8f+/M9.
