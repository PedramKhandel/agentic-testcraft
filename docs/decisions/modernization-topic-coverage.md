# M8 Modernization — Topic Coverage Review

**Review date:** 2026-08-17
**Context:** M8 produced 13 modernization `ModernizationRecord`s (`knowledge/modern/modernization.jsonl`) covering async/await, deterministic time, flaky-as-fatal, disposable containers, hermetic fixtures, mutation testing, property-based testing, contract testing, fuzz testing, Playwright browser UI, pytest-httpserver, CI parallel execution, and monorepo suite partitioning. This document records the outcome of auditing the remaining "modern testing practice" topics against the existing 13 records, and explains what was added, reviewed-and-excluded, folded into an existing record, or excluded.

Each decision below is grounded in the existing `modern:*` records (and their `official_sources`), so no claim is made beyond what is already cited elsewhere in `knowledge/modern/`.

## Topics audited

| # | Topic | Outcome |
|---|---|---|
| 1 | Randomized test ordering / per-test randomness | **Added** as `modern:random-test-ordering` |
| 2 | Snapshot / golden-master assertions | **Added** as `modern:snapshot-golden` |
| 3 | Hermetic HTTP service-boundary mocking | **Added** as `modern:api-boundary-mocking` |
| 4 | Cross-version / cross-platform gating | **Added** as `modern:cross-version-matrix` |
| 5 | Flaky-test retries / re-runs | **Review-excluded** (see §2) |
| 6 | Eventual-consistency polling waits | **Review-excluded** (see §2) |
| 7 | Random-seed handling for generated values | **Folded** into `modern:random-test-ordering` (§3) |
| 8 | Deterministic time handling | **Folded** into `modern:deterministic-time` (§3) |
| 9 | Retry/back-off as a reliability strategy | **Folded** into `modern:flaky-as-fatal` (§3) |
| 10 | Record/playback of UI interactions | **Excluded** (see §4) |
| 11 | Shared/persistent fixtures across tests | **Excluded** (see §4) |
| 12 | Stored-procedure / in-DB test logic | **Excluded** (see §4) |
| 13 | Manual test selection / run subsets | **Excluded** (see §4) |

## 1. Records added

### 1.1 Randomized test ordering — `modern:random-test-ordering`
`pytest-randomly` "randomly shuffles the order of test items... [and] resets Python's global random seed to a fixed value" derived from `--randomly-seed`. Static declaration order (the book's `Repeated Test`) hides inter-test coupling; a fixed seed makes discovery of ordering faults reproducible.
- **Sources:** `https://github.com/pytest-dev/pytest-randomly`
- **Affected book ids:** `goal:repeatable-test`, `pattern:test-enumeration`, `smell:erratic-test`, `smell:fragile-test`, `principle:keep-tests-independent`, `principle:design-for-testability`.

### 1.2 Snapshot / golden-master assertions — `modern:snapshot-golden`
`syrupy` "enables developers to write tests which assert immutability of computed results" via `assert actual == snapshot`, with snapshots committed under `__snapshots__` and refreshed via `pytest --snapshot-update`. Covers the case the book's hand-written `Expected Value` / `Assertion Method` does not scale to.
- **Sources:** `https://github.com/syrupy-project/syrupy`
- **Affected book ids:** `pattern:assertion-method`, `smell:fragile-test`, `principle:verify-one-condition-per-test`, `goal:tests-as-safety-net`.

### 1.3 Hermetic HTTP service boundaries — `modern:api-boundary-mocking`
`httpx`'s `MockTransport(handler)` "return[s] pre-determined responses, rather than making actual network requests," so HTTP-client tests assert outbound requests against an in-process server without a shared live service.
- **Sources:** `https://www.python-httpx.org/advanced/transports/`
- **Affected book ids:** `pattern:layer-test`, `pattern:back-door-manipulation`, `smell:fragile-test`, `smell:erratic-test`, `principle:isolate-the-sut`, `principle:use-the-front-door-first`, `goal:repeatable-test`.

### 1.4 Cross-version / cross-platform gating — `modern:cross-version-matrix`
`tox` "check[s] your package builds and installed correctly under different environments (such as different Python implementations, versions or installation dependencies)" and runs the suite in each env; GitHub Actions `matrix` + `setup-python` extend this across operating systems.
- **Sources:** `https://tox.wiki/en/latest/`, `https://github.com/actions/setup-python`
- **Affected book ids:** `pattern:test-runner`, `pattern:test-selection`, `smell:production-bugs`, `principle:design-for-testability`, `goal:repeatable-test`.

## 2. Topics reviewed and excluded (intentionally no dedicated record)

### 2.1 Flaky-test retries / re-runs
The book has no "retry" guidance; a modern retry tool (`pytest-rerunfailures`) exists, but retrying is explicitly **rejected** by `modern:flaky-as-fatal`, whose `agent_rule_change` says "Do not add retry/suppression to silence a flaky test. Refactor to remove external-state dependence." Adding a retry record would contradict the established rule, so none is created. A brief mention is kept in §3 (fold).

### 2.2 Eventual-consistency polling waits
Polling for an eventually-consistent system is a **behavioral test pattern**, not a standalone modern tool, and is covered behaviorally by existing guidance: auto-waiting in `modern:browser-ui-assertions` and deterministic async in `modern:async-test-support`. No dedicated record is warranted.

## 3. Topics folded into existing records

| Topic | Folded into | How |
|---|---|---|
| Random-seed handling for generated values | `modern:random-test-ordering` | pytest-randomly resets the global `random.seed` per test, making Hypothesis / factory-boy / Generated Value data reproducible; the record's `modern_position` already describes per-test seed reset. |
| Deterministic time handling | `modern:deterministic-time` | Already covered by the `time-machine` record. |
| Retry/back-off as reliability | `modern:flaky-as-fatal` | The rejection of retries is already the rule; no separate positive endorsement of retrying is added. |

## 4. Topics excluded (already covered / not a practice gap)

These are genuine testing topics, but each is already represented by a `modern:*` record above, so a new record would duplicate coverage rather than add it:

- **Record/playback UI (the book's `Recorded Test`)** — superseded by `modern:browser-ui-assertions` (code-first Playwright with auto-waiting and per-test browser isolation).
- **Shared/persistent fixtures across tests** — superseded by `modern:hermetic-integration` (function-scoped fixtures with teardown).
- **Stored-procedure / in-database test logic** — superseded by `modern:disposable-integration-containers` (per-test disposable Postgres, etc.).
- **Manual test selection / run subsets** — superseded by `modern:ci-parallel-execution` and `modern:monorepo-suite-partitioning` (suite subsetting and sharding).

## 5. Validation

- All four new records are constructed through `ModernizationRecord` (`schemas.py`) and re-validated by `run_modernization` before writing.
- `validate-knowledge` confirms all `affected_knowledge_ids` resolve to declared book ids and that every `official_sources` URL is absolute `https://`.
- `tests/unit/test_modernize.py` enforces id uniqueness, id/URL/date format, and the rejection paths.
