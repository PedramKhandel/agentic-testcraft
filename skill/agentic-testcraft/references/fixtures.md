# Fixtures

## Fixture scope (pick one)

| Name | Lifetime | When to use | Risk |
|---|---|---|---|
| Fresh Fixture | built per test, torn down after | Default. Avoids shared-state coupling. | Setup cost |
| Minimal Fixture | smallest setup that exercises the condition | Always, with Fresh or Shared | — |
| Immutable Shared | built once, never mutated | Expensive, genuinely reusable state | — |
| Shared / Persistent | reused across tests | Demonstrated cost/technical reason only | Erratic/Fragile Test |
| Prebuilt | built outside the run (DB seed, etc.) | Very expensive setup, immutable | Staleness, Test Run Wars |

## Setup styles

- **In-line**: all setup in the test body — readable end-to-end.
- **Implicit**: shared setup in `setUp`/`setUp`-equivalent — use for
  essential-but-irrelevant pieces only.
- **Delegated**: intent-revealing creation methods / object builders.

## Teardown

Guarantee teardown for any external resource. Prefer rollback or in-process
disposable containers (see `databases-and-resources.md`) over shared mutable
state. Teardown runs even on failure.

Evidence: pattern:fresh-fixture, pattern:minimal-fixture, pattern:shared-fixture, pattern:standard-fixture, pattern:prebuilt-fixture, pattern:suite-fixture-setup, pattern:in-line-setup, pattern:implicit-setup, pattern:delegated-setup, principle:keep-tests-independent, principle:isolate-the-sut, modern:hermetic-integration, modern:disposable-integration-containers.
