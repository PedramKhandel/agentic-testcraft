# Core principles

Defaults, exceptions, and warnings distilled from the source book and modern
additions. Each maps to a knowledge `id`; book entries are `origin:"book"`.

## Behavioral stance (defaults)

| Rule (agent-facing) | Default | Exceptions / warnings | Evidence |
|---|---|---|---|
| Verify through behavior, not implementation | Assert observable state/output through a stable interface | Interaction verification only when the call *is* the requirement | principle:use-the-front-door-first; principle:verify-one-condition-per-test; principle:test-concerns-separately |
| One condition ≠ one assertion | One coherent observable outcome may take several assertions | Many outcomes in one test → lose defect localization | principle:verify-one-condition-per-test; goal:defect-localization |
| Smallest useful boundary | Smallest boundary that faithfully verifies | Larger boundary when behavior crosses components | principle:isolate-the-sut; principle:test-concerns-separately |
| Dependency replacement is goal-driven | Name why before replacing | "dependency exists → mock it" is forbidden | principle:don-t-modify-the-sut; principle:design-for-testability |
| Fixture minimality | Minimal + fresh per test | Shared fixtures only with demonstrated cost/technical reason | principle:keep-tests-independent; principle:isolate-the-sut |
| Behavior-preserving testability refactor | Behavior-preserving only | No `if testing` forks; dependency boundaries over test branches | principle:keep-test-logic-out-of-production-code; principle:minimize-untestable-code |

## Goals (why we test)

Automated tests exist to **prevent** bugs (bug-repellent), give a **safety net**
for change (tests-as-safety-net), act as **specification** (tests-as-specification),
**document** behavior (tests-as-documentation), **localize** defects quickly
(defect-localization), and give fast, **self-checking, repeatable** feedback
(self-checking-test, repeatable-test). Coverage metrics are a *signal*, not the
goal.

## Warnings (do not do)

- Mock the SUT. | - Suppress flakiness with retries; fix the cause.
- Assert every internal call. | - Change production behavior to satisfy a test.
- Add `if testing` production branches when a seam exists. | - Share mutable fixtures just to save setup code.

Evidence: goals:{tests-as-safety-net, bug-repellent, repeatable-test, self-checking-test, fully-automated-test}; modern:flaky-as-fatal, modern:mutation-testing.
