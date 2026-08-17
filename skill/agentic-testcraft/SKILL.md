---
title: Agentic Testcraft
name: agentic-testcraft
description: "Judgment-first testing skill: design, write, review, refactor, and validate maintainable tests with behavior-focused, principled fixtures and test doubles."
version: 1.0.0rc1
status: release-candidate
compatibility: "Python 3.10+; pytest 8+. Mutation/fuzz tools (mutmut, atheris) are Linux/macOS-primary with Windows via WSL; core decision rules are platform-agnostic."
evidence_base: knowledge/synthesized/skill-traceability.json
generated_from: knowledge/synthesized/decision-rules.jsonl + knowledge/modern/
last_review: 2026-08-17
home: https://github.com/pedram-ahmadi/agentic-testcraft
---

# Agentic Testcraft

A compact, decision-oriented skill that makes a coding agent substantially better
at **designing, writing, reviewing, refactoring, and validating maintainable
automated tests**. It is framework-independent: it improves *judgment*, not test
syntax. Load `SKILL.md` as the agent's system/instruction memory; see
`references/` for the detailed catalogs (progressive disclosure).

**Evidence trace:** every rule is grounded in a knowledge `id`. Book-derived
principles are `origin:"book"` (the 2007 source book); modern additions are
`origin:"modern"` (see `knowledge/synthesized/skill-traceability.json`).

---

## When to apply this skill

Use this whenever you are writing, editing, deleting, or reviewing tests, or
planning a testability refactor of production code. Apply it **continuously**,
not as a final polish pass.

## Core stance

- Passing tests are necessary but **not sufficient**. Green means the SUT
  behaves as asserted — not that the assertions assert the *right* behavior.
- Favor **behavior through a stable interface**; avoid asserting incidental
  implementation details.
- Tests must be **fast, deterministic, isolated, self-checking, repeatable**.
  Every fixture is fresh unless a technical reason forces sharing.

---

## Runtime workflow (12 steps)

Steps 1–6 shape the design; 7–12 execute, review, validate, and report.

### 1. Inspect before writing
Determine: language; test framework; repo conventions; existing nearby tests;
test commands; SUT and dependencies; architectural boundary; available test
helpers/fixtures/factories; CI constraints if visible. **Do not introduce a new
framework without a compelling reason.**
- ref: `references/test-smells.md`, `references/test-doubles.md`

### 2. Define the behavior
State the observable behavior/test condition being verified. Distinguish:
requirement/behavior; implementation detail; incidental call.
- rule: R1 (`references/verification.md`)

### 3. Choose the smallest useful test boundary
Prefer the smallest boundary that faithfully verifies the behavior. Use a larger
boundary only when behavior intrinsically crosses components or isolation would
test the wrong thing. If the SUT is not seam-friendly (tight coupling, IO buried
deep), a minimal behavior-preserving testability refactor may enable a smaller
boundary — never `if testing` forks.
- rule: R3, R6, `references/test-boundaries.md`, `references/testability.md`

### 4. Choose verification strategy
Default to **state verification** through a stable public interface when it
adequately verifies the requirement. Use **interaction verification** only when
the interaction itself is the observable behavior, or when no reliable
post-state/output exists. Never assert incidental internal calls.
- rule: R1/R4, `references/verification.md`

### 5. Design the fixture
Default: minimal fixture; fresh per test. Shared/persistent fixtures only for a
demonstrated cost or technical reason, with the coupling risk actively managed.
- rule: R5, `references/fixtures.md`

### 6. Classify every replaced dependency
Before creating a double, name *why*. Route by need:
- controlled indirect input → **stub**;
- observe calls after exercise → **spy**;
- interaction is the requirement (expectation-style) → **mock**;
- lightweight realistic semantics → **fake**;
- placeholder never used → **dummy**;
- real dependency is fast, deterministic, local, safe → **use the real one**.
Never apply "dependency exists → mock it."
- rule: R4, `references/test-doubles.md`

### 7. Write intention-revealing tests
Make the behavior obvious to the next reader. Avoid unexplained literals, giant
fixtures, conditional logic inside tests, irrelevant setup, mystery guests,
excessive helper indirection, and intent-obscuring duplication. Extract helpers
only when repetition/noise is real and the helper can name itself.
- rule: R2/R8, `references/test-smells.md`, `references/core-principles.md`

### 8. Preserve test independence
Each test runs independently unless the project intentionally uses another
well-justified model. Avoid order dependence and shared mutable state.
- rule: R8, `references/test-smells.md` (Erratic/Flaky, Fragile Test)

### 9. Run the smallest relevant scope first
Start with one test, then one file/class, then one module; then run the broader
affected suite. (Locally: `pytest -n auto` or cache-driven selection when the
project uses pytest-xdist; in CI: use the project's matrix/shard config.)
- ref: `references/async-concurrency-and-flakiness.md`, R7

### 10. Review for smells before completion
Check, at minimum: Obscure Test, Conditional Test Logic, Test Code Duplication,
Assertion Roulette, Erratic/Flaky Test, Fragile Test, General/Overgrown
Fixture, Mystery Guest, excessive interaction verification, unnecessary mocks,
overspecified behavior, slow setup, hidden shared state.
- rule: R8, `references/test-smells.md`

### 11. Validate effectiveness (when justified)
Risk- and tooling-permitting, apply stronger validation: targeted mutation
testing; property-based testing for broad input spaces; focused fault seeding;
integration confirmation against the real dependency boundary. **Do not add
heavyweight validation to every trivial change.**
- rule: R7, `references/test-effectiveness.md`

### 12. Report completion precisely
State: tests added/changed; behavior covered; test command(s) run; result
(pass/skip/fail + counts); any production refactor done for testability;
important residual risk or untested boundary.

---

## Guardrails (must not do)

- Do not mock the SUT.
- Do not assert every internal call; assert observable outcomes.
- Do not change production behavior to satisfy a test.
- Do not add `if testing` style production branches when a cleaner dependency
  boundary is available.
- Do not introduce shared mutable fixtures merely to save setup code.
- Do not turn "one condition per test" into "one assertion per test."
- Do not ignore existing project conventions.
- Do not blindly port historical framework mechanics from the 2007 source.
- Do not suppress flakiness with retries; fix the cause (remove external-state
  dependence). Modern tools treat flakiness as fatal.

---

## Completion

The skill is complete when: the smallest faithful test for each condition
exists or is documented, all assertions target observable behavior, fixtures are
minimal and fresh, doubles are individually justified, the smallest relevant
scope is green, and the smell/review gate passes.

## References (progressive disclosure)

Detailed, framework-agnostic catalogs — load on demand:

- `references/core-principles.md` — defaults, exceptions, warnings.
- `references/test-boundaries.md` — where to cut the SUT boundary.
- `references/verification.md` — state vs. interaction verification.
- `references/fixtures.md` — fixture strategies and minimality.
- `references/test-doubles.md` — dummy/stub/spy/mock/fake classification.
- `references/test-smells.md` — the canonical smell catalog + review checklist.
- `references/testability.md` — testability refactors (seams, dependency
  boundaries).
- `references/async-concurrency-and-flakiness.md` — async, time, flakiness.
- `references/test-effectiveness.md` — mutation, property, contract, fuzz.
- `references/databases-and-resources.md` — DB/resource isolation.
- `references/decision-trees.md` — quick lookup for boundary/double decisions.
