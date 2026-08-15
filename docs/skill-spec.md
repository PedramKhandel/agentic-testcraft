# Agentic Testcraft — Skill Specification

> **Status:** M1 milestone — the authoritative definition of what the final
> skill must improve in a coding agent. This is written *before* knowledge
> extraction so the pipeline produces testing **judgment**, not a book summary.

The final skill is **not** a prompt wrapper around a test framework. It is a
compact, decision-oriented skill that makes a coding agent substantially
better at **designing, writing, reviewing, refactoring, and validating
maintainable automated tests**.

## Vision

A coding agent, having loaded `agentic-testcraft`, applies behavior-focused
test design with principled fixture and test-double strategy, detects and
remediates test smells, performs minimal testability refactors only when
justified, and validates that generated tests actually catch plausible
defects — all while adapting to the host repository's language, framework,
and conventions.

## Source

The conceptual source is Gerard Meszaros, *xUnit Test Patterns: Refactoring
Test Code* (Addison-Wesley, 2--7). The source book is **not redistributed**;
the pipeline transforms its testing-judgment ideas into operational rules and
modernizes them with current primary/official sources. The final skill must
not read as a 2007 field report.

---

## 1. Primary use cases

1. Write tests for new or existing code.
2. Add missing tests around a change.
3. Review existing tests.
4. Refactor fragile or obscure tests.
5. Diagnose flaky/erratic tests.
6. Choose a test boundary.
7. Choose a verification strategy.
8. Choose a fixture strategy.
9. Choose a dependency/test-double strategy.
10. Identify hard-to-test production design.
11. Perform small behavior-preserving refactorings for testability when justified.
12. Validate generated tests beyond "they pass."

## 2. Non-goals

1. Teaching basic test-framework syntax (pytest, JUnit, Vitest, etc.).
2. Maximizing coverage percentage blindly.
3. Forcing every project into one testing philosophy.
4. Replacing project conventions without reason.
5. Mocking every dependency.
6. Producing tests that merely mirror implementation details.
7. Treating the 2007 source as complete modern testing doctrine.

## 3. Desired behavioral outcomes

Skill-enabled agents produce tests that are:

- behavior-focused
- self-checking
- deterministic
- independent
- readable / intention-revealing
- minimal in setup
- appropriately isolated
- resistant to irrelevant refactors
- diagnostically useful
- reasonably fast
- easy to maintain
- consistent with the host repository's conventions

## 4. Decision points the skill must handle

1. What is the SUT / test boundary?
2. Which behavior or requirement is being verified?
3. What are the important test conditions?
4. Unit / component / integration / contract / system / browser?
5. Direct/state verification or indirect/behavior verification?
6. Minimal / fresh / shared / persistent fixture?
7. Real dependency, fake, stub, spy, mock, or dummy?
8. Is the dependency slow, nondeterministic, unavailable, dangerous, or part of the behavior under test?
9. Is production code hard to test because of design?
10. Is a test smell present?
11. What should run first?
12. What broader validation should run before completion?
13. Does the test detect plausible faults, not merely execute lines?

## 5. Core decision rules (authoring target)

These are the high-leverage rules the final skill must encode. They are
written here as the target; extraction must ultimately ground each in evidence.

### R1 — Verify through behavior, not implementation
State trigger: "I am asserting an internal call was made." Default: do not.
Exception: the interaction itself is the observable contract.

### R2 — One condition per test ≠ one assertion per test
Multiple assertions may jointly verify one coherent observable outcome.

### R3 — Smallest useful boundary
Prefer the smallest boundary that faithfully verifies the behavior.

### R4 — Dependency replacement is goal-driven
Before introducing a double, name why: controlled indirect input, observing
output, interaction-as-requirement, lightweight semantics, or placeholder.
Default: keep the real dependency when fast, deterministic, local, and safe.

### R5 — Fixture minimality
Default: minimal + fresh per test. Shared/persistent fixtures require a
demonstrated cost or technical reason.

### R6 — Guarded testability refactoring
Behavior-preserving only, dependency boundaries over test-only branches, no
`if testing` forks, run tests before/after.

### R7 — Effectiveness validation
Use mutation testing, property-based testing, or fault seeding when risk and
tooling justify it.

### R8 — Smell-driven review
Inspect generated/legacy tests for the canonical catalog of smells before
completion.

## 6. Acceptance criteria (final skill, Stage 9 gate)

- `SKILL.md` is concise (< 400 lines) and self-sufficient for the 12-step
  runtime workflow.
- Detailed catalogs live in `references/` (progressive disclosure).
- State-vs-behavior, fixture, and test-double decisions are all explicit.
- Over-mocking guardrail is explicit.
- "One condition ≠ one assertion" is explicit.
- Testability guardrails are explicit.
- Smell-review step is explicit.
- Focused-then-broader execution is explicit.
- Completion reporting is explicit.
- All major rules map to evidence IDs (synthesized → book/modern).
- No long verbatim source-book excerpts.
- Skill loads cleanly on the supported agent(s) and passes platform validators.

## 7. Vocabulary / glossary mapping

| Term | Definition (agent-facing) |
|------|---------------------------|
| SUT | System Under Test — the component whose behavior is observed. |
| DOC | Depended-On Component — a collaborator the SUT interacts with. |
| Direct output/state | Observable state of the SUT/DOC after exercise (returns, mutations). |
| Indirect input | A value supplied to the SUT through a DOC to drive its behavior. |
| Indirect output | A value the SUT sends to a DOC during exercise. |
| Test double | Generic wrapper term for any stand-in for a DOC. |
| Dummy | Pass-only placeholder, never used. |
| Stub | Supplies canned indirect inputs. |
| Spy | Observes and records indirect outputs for later verification. |
| Mock | Verifies expected interactions against a contract. |
| Fake | Lightweight working implementation with realistic semantics. |
| Fixture | The pre-built state a test exercises against. |
| Fresh fixture | Built per test. |
| Shared fixture | Used across multiple tests. |
| Minimal fixture | The smallest setup that exercises the condition. |
| Test smell | A pattern of poor test design practice with detectable symptoms. |
| Verification | The act of checking an outcome (direct state or indirect output). |

## 8. Evaluation acceptance (Stage 10+)

The final skill must demonstrate, on a nontrivial A/B suite, reproducible
improvement over a baseline (same agent, same task, no skill) on:

- seeded-defect detection;
- avoidance of unnecessary mocks;
- reduced brittle implementation coupling;
- fixture quality;
- test independence;
- readability/intent;
- mutation effectiveness where measured.

One cherry-picked example is insufficient. Every significant skill change
after initial evals must tie to a documented failure, new evidence, or a
clearly stated design objective.
