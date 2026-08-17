# Ecosystems & adapters

The skill is **framework-agnostic** and never names a specific framework's
assertions. These mappings translate a principle into the local framework.
They are *optional* adapters; the core rules do not depend on them.

- **pytest**: `pytest.mark.parametrize` (Parameterized Test), `pytest.fixture`
  (Fresh/Standard/Shared Fixture), `-n auto` (xdist parallelism), `-k`/markers
  (Test Selection), `pytest-httpserver` (in-process HTTP contract),
  `pytest-asyncio` (async).
- **unittest (Py)**: `unittest.IsolatedAsyncioTestCase`, `setUp/tearDown`.
- **pytest-httpserver** — in-process HTTP server per test; assert expected
  requests and scripted responses (`expect_request / respond_with_*`).
- **Playwright** — cross-browser (Chromium/Firefox/WebKit) code-first UI testing
  with auto-waiting + network mocking (replaces Recorded Test).
- **Contract testing** — `pact-python` + Pact Broker for consumer/provider
  contracts at service boundaries.
- **Effectiveness** — `mutmut` (mutation), `hypothesis` (property-based +
  shrinking), `atheris` (coverage-guided fuzz).

Evidence (modern): modern:async-test-support, modern:disposable-integration-containers, modern:hermetic-integration, modern:mutation-testing, modern:property-based-testing, modern:contract-testing, modern:fuzz-testing, modern:browser-ui-assertions, modern:service-level-expectations, modern:ci-parallel-execution, modern:monorepo-suite-partitioning.
