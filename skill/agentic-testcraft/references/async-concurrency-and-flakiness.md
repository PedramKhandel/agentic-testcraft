# Async, time, and flakiness

Modern additions (2026-08-17 review date) — the 2007 book predates these.

## Async/await

- Coroutines must run through an **async-aware** runner. Plain synchronous
  assertions on `await`-like results silently skip (a coroutine object is truthy).
- Use the framework's async support: `@pytest.mark.asyncio` (pytest-asyncio) or
  `unittest.IsolatedAsyncioTestCase`. Do **not** synchronously block on a
  coroutine (`run_until_complete`) in a sync test.

## Deterministic time

- Never let date/time calls read the live clock in a test (nondeterministic).
- Freeze time deterministically with a time-mocking tool
  (e.g., `time-machine` `@time_machine.travel` or its pytest plugin).

## Flakiness is fatal

- A flaky test must be **fixed, not retried/suppressed**. Retry masks real
  nondeterminism and breaks example databases / shrinking.
- Common causes: global state; filesystem/database state not reset between
  inputs; un-managed randomness, thread scheduling, network timing.
- Root-cause fix: remove external-state dependence and reset shared state between
  inputs.

Evidence (modern): modern:async-test-support, modern:deterministic-time,
modern:flaky-as-fatal; (book) smell:erratic-test, smell:fragile-test,
principle:keep-tests-independent, principle:isolate-the-sut,
goal:repeatable-test, pattern:generated-value.
