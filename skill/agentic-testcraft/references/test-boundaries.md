# Choosing the test boundary

Decide what the **System Under Test (SUT)** is for this condition, then include
only the collaborators needed to observe the behavior.

## Decision tree

```
Does the behavior stay in one unit/component?
  yes -> Unit test the component directly (Layer Test).
  no  -> Does the requirement cross a boundary (HTTP/DB/stream/external API)?
           yes -> Integration test at the real boundary (Layer Test + real DOC).
           no  -> Refactor the behavior behind a seam so a unit test suffices,
                  OR test the smaller component in isolation.
```

## Principles

- **Isolate the SUT** from environment/changed collaborators.
- **Test concerns separately** — don't test two layers of logic in one test.
- **Use the front door first** — prefer the public interface over back doors.
- The SUT may be a class, a function, a service, or an HTTP layer; it is defined
  *by what the test verifies*, not by the production module structure.

## When to go wider

- The observable behavior genuinely spans services (e.g., a request flowing
  service A → B → DB). Here the SUT is the *cross-service flow* and the boundary
  is asserted via contract (see `test-effectiveness.md`) rather than a single
  process test.
- Legacy code with no seam: prefer a thin Humble Object seam (see
  `testability.md`) over a back-door that couples the test to internals.

Evidence: pattern:layer-test, pattern:back-door-manipulation, principle:isolate-the-sut, principle:test-concerns-separately, principle:use-the-front-door-first, principle:don-t-modify-the-sut, modern:contract-testing.
