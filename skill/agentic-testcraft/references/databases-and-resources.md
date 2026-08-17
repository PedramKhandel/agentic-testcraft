# Databases & external resources

## Isolation principle

Each test that touches a DB or external resource must start from a known state
and leave it clean, **without coupling tests to each other** (avoid Test Run
Wars / Erratic Tests from shared mutable state).

## Strategies (book + modern)

| Approach | Scope | Notes |
|---|---|---|
| Transaction Rollback Teardown | per test | Start/commit/rollback a test transaction; SUT must run inside it. |
| Table Truncation Teardown | per test/suite | `TRUNCATE` tables; efficient, side-effect-free. |
| Database Sandbox | per developer/run | Private DB/schema per run avoids cross-user pollution. |
| Disposable containers (modern) | per test | Spin up a fresh Docker container per test via Testcontainers; function-scoped fixture. Default today for integration tests touching a real DB/service. |

## Defaults (modern)

- **Default:** disposable, per-test container (Testcontainers) behind a
  function-scoped fixture. No shared DB across tests.
- **Exception:** when container spin-up is too slow, use an *immutable* shared
  fixture only (never mutable).
- Use `back-door` DB access only to assert/seed state that has no front-door
  equivalent — and never assert incidental internal calls.

## Teardown

Guarantee rollback/truncation/teardown even on failure. Prefer rollback for
fresh fixtures; per-test containers for integration boundaries.

Evidence (book): pattern:database-sandbox, pattern:transaction-rollback-teardown, pattern:table-truncation-teardown, pattern:stored-procedure-test, pattern:back-door-manipulation, pattern:shared-fixture; principle:isolate-the-sut, principle:keep-tests-independent, smell:fragile-test, smell:erratic-test. Evidence (modern): modern:disposable-integration-containers, modern:hermetic-integration.
