"""Stage 8 — modernize source-derived guidance with current primary/official sources.

The build plan prefers a frontier reasoning model for this stage, but no LLM is
available here. Instead, modernization records are produced from direct
research of authoritative primary/official documentation, each carrying an exact
URL and a review date. Every `ModernizationRecord` is validated through its
pydantic model (which enforces absolute-URL `official_sources` and a
`YYYY-MM-DD` `review_date`) before it is written, and is re-checked by
`validate-knowledge`.

Modernization records are deliberately compact (no long book quotations): they
state the **book position**, the **modern position**, a **status**
(`unchanged`/`clarified`/`expanded`/`narrowed`/`superseded`/`historical`), a
**rationale**, one or more **official_sources** URLs, the
**affected_knowledge_ids** (real ids from M5), and an optional **agent_rule_change**.

Records are grouped by category for the markdown digest at
`knowledge/modern/current-testing-practices.md`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from rich.console import Console

from .config import load_settings
from .provenance import write_jsonl
from .schemas import ModernizationRecord, ModernizationStatus

console = Console()

# Today's date, recorded in artifacts per Stage 8 ("current date recorded").
REVIEW_DATE = "2026-08-17"


class _ModItem(NamedTuple):
    record: dict[str, Any]
    category: str


def _rec(
    id: str,
    topic: str,
    book_position: str,
    modern_position: str,
    status: ModernizationStatus,
    rationale: str,
    sources: list[str],
    affected: list[str],
    rule_change: str | None = None,
) -> dict[str, Any]:
    return ModernizationRecord(
        id=id,
        topic=topic,
        book_position=book_position,
        modern_position=modern_position,
        status=status,
        rationale=rationale,
        official_sources=sources,
        affected_knowledge_ids=affected,
        agent_rule_change=rule_change,
        review_date=REVIEW_DATE,
    ).model_dump(exclude_none=True)


# --------------------------------------------------------------------------- #
# M8a — Runtime and determinism (async/await, clocks, randomness, flakiness)  #
# --------------------------------------------------------------------------- #

_M8A: list[_ModItem] = [
    _ModItem(
        _rec(
            id="modern:async-test-support",
            topic="Async/await test execution",
            book_position=(
                "The 2007 xUnit patterns were written before async/await (PEP 492, "
                "2015); Test Method / Test Runner / Assertion Method assume "
                "synchronous method calls."
            ),
            modern_position=(
                "Modern suites exercise coroutines via an async-aware runner. "
                "pytest-asyncio 'provides support for coroutines as test functions. "
                "This allows users to await code inside their tests' (e.g. "
                "@pytest.mark.asyncio), or stdlib unittest.IsolatedAsyncioTestCase. "
                "Awaiting inside a plain synchronous test yields a coroutine and "
                "silently skips the assertion."
            ),
            status="expanded",
            rationale=(
                "async/await did not exist in 2007; the book's patterns give no "
                "mechanism to await coroutines. Without an async runner, assertions "
                "on awaited results never execute."
            ),
            sources=["https://pytest-asyncio.readthedocs.io/en/latest/"],
            affected=[
                "pattern:recorded-test",
                "pattern:test-method",
                "pattern:test-runner",
                "principle:design-for-testability",
            ],
            rule_change=(
                "When a test must await a coroutine, declare it async and run it "
                "through an async-capable runner (pytest-asyncio or "
                "unittest.IsolatedAsyncioTestCase); do not synchronously unwrap "
                "coroutines with the synchronous front-door patterns."
            ),
        ),
        "Runtime and determinism",
    ),
    _ModItem(
        _rec(
            id="modern:deterministic-time",
            topic="Deterministic time / virtual clocks",
            book_position=(
                "Tests may call real time directly (e.g. timestamp comparisons "
                "inside Test Method); the book offers no mechanism to freeze the "
                "clock."
            ),
            modern_position=(
                "Tests must not depend on wall-clock time. Use a time-mocking tool "
                "such as time-machine, which is 'a tool for mocking the time in "
                "tests' and patches datetime/time so date-time logic becomes "
                "deterministic (via @time_machine.travel or its pytest plugin)."
            ),
            status="clarified",
            rationale=(
                "Letting the real clock into a test makes outcomes nondeterministic "
                "(slow / flaky tests). Freezing time keeps time-dependent behavior "
                "reproducible."
            ),
            sources=["https://time-machine.readthedocs.io/en/latest/"],
            affected=[
                "smell:erratic-test",
                "smell:fragile-test",
                "principle:isolate-the-sut",
                "pattern:transaction-rollback-teardown",
            ],
            rule_change=(
                "For any test touching the clock, freeze time deterministically with "
                "time-machine (or equivalent); never let date/time calls read the live "
                "clock."
            ),
        ),
        "Runtime and determinism",
    ),
    _ModItem(
        _rec(
            id="modern:flaky-as-fatal",
            topic="Flaky tests are a fatal error, not retried",
            book_position=(
                "The book names erratic / fragile tests and recommends refactoring, "
                "but modern tooling makes flakiness a hard failure rather than "
                "something to suppress."
            ),
            modern_position=(
                "Modern tooling treats flaky tests as fatal. Hypothesis: 'A flaky "
                "test is one which might behave differently when called again... not "
                "deterministic', and it 'raises an exception when it detects "
                "flakiness' because 'Hypothesis relies on deterministic behavior "
                "for the database to work.' Common sources: global state, "
                "filesystem/database state not reset between inputs, and 'un-managed "
                "sources of randomness... thread scheduling, network timing.' Fix by "
                "removing external-state dependence, not by retrying."
            ),
            status="expanded",
            rationale=(
                "Retrying masks real nondeterminism and breaks Hypothesis example "
                "database / shrinking. The modern stance (fix-then-pass) is stricter "
                "than 2007 and aligns with keep-tests-independent and repeated-test, "
                "but enforces it."
            ),
            sources=["https://hypothesis.readthedocs.io/en/latest/tutorial/flaky.html"],
            affected=[
                "smell:erratic-test",
                "smell:fragile-test",
                "principle:keep-tests-independent",
                "goal:repeatable-test",
                "principle:isolate-the-sut",
                "pattern:generated-value",
            ],
            rule_change=(
                "Do not add retry/suppression to silence a flaky test. Refactor to "
                "remove external-state dependence and reset shared state between "
                "inputs; treat flaky tests as failures to fix."
            ),
        ),
        "Runtime and determinism",
    ),
]


# --------------------------------------------------------------------------- #
# M8c — Modern test-effectiveness (mutation, property-based, contract, fuzz)    #
# --------------------------------------------------------------------------- #

_M8C: list[_ModItem] = [
    _ModItem(
        _rec(
            id="modern:mutation-testing",
            topic="Mutation testing as a test-quality gate",
            book_position=(
                "The 2007 book treats test enumeration and selection as manual "
                "risk management (Test Enumeration / Test Selection, coverage of "
                "equivalence classes and boundary values); it has no notion of "
                "automatically mutating the SUT to measure whether tests actually "
                "detect faults."
            ),
            modern_position=(
                "Mutmut 'is a mutation testing system for Python... a mutation "
                "testing tool that modifies your source code to find out if your "
                "test suite is able to stop it.' A surviving mutant means a test "
                "does not actually catch that kind of fault; mutation score = "
                "detected mutants / total mutants. Run `mutmut run`, inspect "
                "`mutmut results`, and add a test that kills each surviving mutant. "
                "(Linux/macOS primary; Windows via WSL.)"
            ),
            status="expanded",
            rationale=(
                "The book's manual risk-based design leaves holes in the safety net "
                "(Tests as Safety Net) invisible; mutation testing makes them "
                "measurable. 2007 predates practical, automatable mutation testing "
                "for mainstream languages."
            ),
            sources=["https://mutmut.readthedocs.io/en/latest/"],
            affected=[
                "pattern:test-enumeration",
                "pattern:test-selection",
                "pattern:parameterized-test",
                "principle:verify-one-condition-per-test",
                "goal:tests-as-safety-net",
                "goal:bug-repellent",
                "goal:repeatable-test",
            ],
            rule_change=(
                "Treat mutation score as a quality gate: run mutmut (or an "
                "equivalent mutation tool) in CI, and for each surviving mutant add "
                "a failing test that kills it — a surviving mutant is a missing "
                "assertion, not a passing test."
            ),
        ),
        "Test-effectiveness methods",
    ),
    _ModItem(
        _rec(
            id="modern:property-based-testing",
            topic="Property-based testing for input-space exploration",
            book_position=(
                "The value/specification patterns (Literal Value, Derived Value, "
                "Generated Value, Data-Driven Test, Parameterized Test) address "
                "hand- or script-supplied example inputs and tester-enumerated "
                "equivalence/boundary classes; there is no automated generation-and-"
                "shrinking of inputs from stated invariants."
            ),
            modern_position=(
                "Hypothesis 'is a property-based testing library... you write tests "
                "which should pass for all inputs... letting Hypothesis randomly "
                "choose which inputs to check — including edge cases,' then shrinks "
                "each failing example to a minimal reproducer and records it in its "
                "example database. 'A single property-based test can cover hundreds "
                "of cases that would otherwise need to be hand written.'"
            ),
            status="expanded",
            rationale=(
                "Hand-authored example generation misses edge cases and is "
                "labor-intensive; Hypothesis finds boundary and interaction bugs "
                "the book's Generated/Derived Values likely miss. 2007 predates "
                "Hypothesis."
            ),
            sources=["https://hypothesis.readthedocs.io/en/latest/"],
            affected=[
                "pattern:generated-value",
                "pattern:derived-value",
                "pattern:literal-value",
                "pattern:parameterized-test",
                "pattern:data-driven-test",
                "principle:verify-one-condition-per-test",
                "goal:bug-repellent",
            ],
            rule_change=(
                "State the invariant (property) and let Hypothesis generate inputs "
                "and shrink failures; when it reports a falsifying example, reduce "
                "it to a minimal case and add it as a permanent regression test."
            ),
        ),
        "Test-effectiveness methods",
    ),
    _ModItem(
        _rec(
            id="modern:contract-testing",
            topic="Consumer-driven contract testing for service boundaries",
            book_position=(
                "For layered/service architectures the book offers Layer Test, "
                "Back-Door Manipulation, and Shared Fixture, plus integration tests "
                "over a shared database; cross-service integration is validated "
                "end-to-end rather than at a boundary contract."
            ),
            modern_position=(
                "Pact is 'the de-facto API contract testing tool. Replace "
                "expensive and brittle end-to-end integration tests with fast, "
                "reliable and easy to debug unit tests.' Consumer tests record "
                "HTTP interactions against a stub provider; provider tests verify "
                "the real provider honors every recorded request via a Pact Broker; "
                "'powerful matching rules prevents brittle tests' and 'integrates "
                "with Pact Broker for powerful CI/CD workflows.'"
            ),
            status="expanded",
            rationale=(
                "End-to-end integration across independently-deployed services is "
                "slow and brittle (Fragile Test) — the 'expensive and brittle "
                "end-to-end integration tests' the modern position replaces. 2007 "
                "had no consumer-driven contract tooling."
            ),
            sources=[
                "https://raw.githubusercontent.com/pact-foundation/pact-python/main/README.md",
                "https://docs.pact.io/",
            ],
            affected=[
                "pattern:layer-test",
                "pattern:back-door-manipulation",
                "pattern:shared-fixture",
                "smell:fragile-test",
                "smell:erratic-test",
                "principle:use-the-front-door-first",
                "principle:isolate-the-sut",
                "goal:tests-as-safety-net",
            ],
            rule_change=(
                "For service boundaries, express consumer expectations as Pact "
                "contracts and verify the provider against them in CI via a Pact "
                "Broker; retire brittle cross-service end-to-end tests that only "
                "duplicate the contract."
            ),
        ),
        "Test-effectiveness methods",
    ),
    _ModItem(
        _rec(
            id="modern:fuzz-testing",
            topic="Coverage-guided fuzz testing for parsers and untrusted input",
            book_position=(
                "Input generation is covered by Literal Value, Derived Value, "
                "Generated Value, Data-Driven Test, and Parameterized Test — all "
                "tester-authored, example-based; there is no automated, "
                "coverage-guided input generation."
            ),
            modern_position=(
                "Atheris is 'a coverage-guided Python fuzzing engine... based "
                "off of libFuzzer... supports fuzzing of Python code, but also "
                "native extensions.' It instruments bytecode, mutates input bytes, "
                "and reports a crash on any uncaught exception; supports custom "
                "mutators and structure-aware fuzzing via libprotobuf-mutator, and "
                "integrates with OSS-Fuzz. (Linux/macOS primary; Windows via WSL.)"
            ),
            status="expanded",
            rationale=(
                "Hand-authored inputs cannot approach the input-space coverage a "
                "fuzzer explores for parsers/validators handling untrusted data; "
                "2007 predates practical Python/libFuzzer coverage-guided fuzzing."
            ),
            sources=[
                "https://raw.githubusercontent.com/google/atheris/master/README.md",
                "https://opensource.google.com/projects/atheris",
            ],
            affected=[
                "pattern:generated-value",
                "pattern:test-method",
                "pattern:data-driven-test",
                "goal:bug-repellent",
                "smell:production-bugs",
            ],
            rule_change=(
                "For parsers/validators consuming untrusted input, add "
                "coverage-guided fuzz tests with atheris (or Hypothesis as a "
                "fallback); treat any raised exception as a defect to fix."
            ),
        ),
        "Test-effectiveness methods",
    ),
]

# --------------------------------------------------------------------------- #
# M8b — Modern integration testing (disposable containers, hermeticity)        #
# --------------------------------------------------------------------------- #

_M8B: list[_ModItem] = [
    _ModItem(
        _rec(
            id="modern:disposable-integration-containers",
            topic="Disposable integration dependencies via containers",
            book_position=(
                "Meszaros' Database Sandbox / Transaction Rollback Teardown / "
                "Stored Procedure Test patterns provision a shared database and "
                "reset its state between tests (often via rollback); the "
                "Shared/Standard Fixture patterns share fixture state across tests."
            ),
            modern_position=(
                "Provide each integration test with a disposable Docker container "
                "via Testcontainers, which 'facilitates the use of Docker containers "
                "for functional and integration testing' (e.g. "
                "PostgresContainer('postgres:16') spun up per test, with a connection "
                "URL handed to the test). pytest function-scoped fixtures 'are "
                "destroyed at the end of the test', so each test gets its own fresh "
                "instance with no shared mutable state ('making sure tests aren't "
                "affected by each other')."
            ),
            status="expanded",
            rationale=(
                "2007 predates Docker (2013) and per-test disposable services. Shared "
                "mutable state between tests is the leading cause of fragile/erratic "
                "tests; per-test containers eliminate that coupling without relying on "
                "rollback discipline."
            ),
            sources=[
                "https://raw.githubusercontent.com/testcontainers/testcontainers-python/main/README.md",
                "https://docs.pytest.org/en/stable/how-to/fixtures.html",
            ],
            affected=[
                "pattern:database-sandbox",
                "pattern:transaction-rollback-teardown",
                "pattern:stored-procedure-test",
                "pattern:shared-fixture",
                "pattern:standard-fixture",
                "smell:fragile-test",
                "smell:erratic-test",
                "principle:isolate-the-sut",
                "principle:keep-tests-independent",
            ],
            rule_change=(
                "For integration tests touching a real database or service, spin up "
                "a disposable container per test with Testcontainers behind a "
                "function-scoped pytest fixture; do not share the database across tests."
            ),
        ),
        "Modern integration",
    ),
    _ModItem(
        _rec(
            id="modern:hermetic-integration",
            topic="Hermetic integration / function-scoped teardown",
            book_position=(
                "Shared/Persistent Fixtures accept shared state that tests reset "
                "(rollback/teardown) to remain independent; Suite Fixture Setup "
                "shares state across a group."
            ),
            modern_position=(
                "Prefer function-scoped fixtures that yield a fresh instance and tear "
                "down immediately after the test ('the fixture is destroyed at the end "
                "of the test'; teardown runs in reverse order); reserve wider scopes "
                "for genuinely immutable, reusable fixtures."
            ),
            status="clarified",
            rationale=(
                "Function scope + mandatory teardown is the modern baseline for "
                "hermetic tests; shared mutable fixtures are the exception, not the "
                "default."
            ),
            sources=[
                "https://docs.pytest.org/en/stable/how-to/fixtures.html",
            ],
            affected=[
                "pattern:shared-fixture",
                "pattern:standard-fixture",
                "pattern:fresh-fixture",
                "pattern:suite-fixture-setup",
                "principle:keep-tests-independent",
                "principle:isolate-the-sut",
                "smell:fragile-test",
            ],
            rule_change=(
                "Default fixtures touching external resources to function scope with "
                "guaranteed teardown; only escalate scope when the fixture is "
                "immutable and genuinely reusable."
            ),
        ),
        "Modern integration",
    ),
]

# --------------------------------------------------------------------------- #
# M8d — Service & browser testing (Playwright, pytest-httpserver)               #
# --------------------------------------------------------------------------- #

_M8D: list[_ModItem] = [
    _ModItem(
        _rec(
            id="modern:browser-ui-assertions",
            topic="Code-first browser automation with auto-waiting",
            book_position=(
                "UI automation is addressed only by Recorded Test — record/"
                "playback of interactions with the application, which is brittle "
                "and offers no robust synchronization or cross-browser story."
            ),
            modern_position=(
                "Playwright is 'a Python library to automate Chromium, Firefox and "
                "WebKit browsers with a single API... ever-green, capable, "
                "reliant and fast.' It provides auto-waiting, network "
                "interception/mocking, a unified selector model, and both "
                "`sync_api` and `async_api` entry points (docs at "
                "playwright.dev/python)."
            ),
            status="expanded",
            rationale=(
                "2007 predates modern browser automation; the book's only UI path "
                "is Recorded Test. Auto-waiting and per-test browser isolation "
                "eliminate the timing fragility and shared-state coupling that "
                "make UI tests erratic/fragile."
            ),
            sources=["https://github.com/microsoft/playwright-python"],
            affected=[
                "pattern:recorded-test",
                "smell:fragile-test",
                "smell:erratic-test",
                "principle:use-the-front-door-first",
                "principle:isolate-the-sut",
                "goal:simple-tests",
                "goal:bug-repellent",
                "goal:robust-test",
            ],
            rule_change=(
                "Prefer code-first Page-Object browser tests with Playwright "
                "(auto-waiting, one browser per test, network mocking) over "
                "Recorded Tests; isolate browser state per test."
            ),
        ),
        "Service & browser testing",
    ),
    _ModItem(
        _rec(
            id="modern:service-level-expectations",
            topic="In-process HTTP server for service-level expectations",
            book_position=(
                "Tests of HTTP clients/servers rely on a real external service, "
                "or on Back-Door Manipulation of a shared fixture; there is no "
                "in-process, programmatically-configured HTTP server per test."
            ),
            modern_position=(
                "pytest-httpserver 'allows you to start a real HTTP server for "
                "your tests. The server can be configured programmatically to "
                "how to respond to requests.' ... 'As the HTTP server is spawned "
                "in a different thread and listening on a TCP port, you can use "
                "any HTTP client.' Each test configures only the request paths it "
                "expects (expect_request/respond_with_*) and asserts the client's "
                "outbound request as part of verification; the server starts/stops "
                "per test, so no shared external service is required."
            ),
            status="expanded",
            rationale=(
                "2007 had no in-process HTTP server fixture; tests either "
                "depended on a shared live service (fragile/rerun-wars) or on "
                "back-door state checks. An isolated server per test makes "
                "service-level expectations hermetic and repeatable."
            ),
            sources=[
                "https://pytest-httpserver.readthedocs.io/en/latest/",
            ],
            affected=[
                "pattern:layer-test",
                "pattern:back-door-manipulation",
                "pattern:stored-procedure-test",
                "smell:fragile-test",
                "principle:use-the-front-door-first",
                "goal:tests-as-safety-net",
                "goal:repeatable-test",
            ],
            rule_change=(
                "For HTTP clients/servers, test against an in-process "
                "pytest-httpserver fixture that asserts expected requests and "
                "returns scripted responses; never depend on a shared running "
                "service for the contract."
            ),
        ),
        "Service & browser testing",
    ),
]

# --------------------------------------------------------------------------- #
# M8e — CI & execution (parallelism, suite partitioning, monorepos)           #
# --------------------------------------------------------------------------- #

_M8E: list[_ModItem] = [
    _ModItem(
        _rec(
            id="modern:ci-parallel-execution",
            topic="Parallelize test execution locally and in CI",
            book_position=(
                "The Test Runner / Testcase Object / Test Suite Object model runs "
                "tests serially within one process; Test Discovery, Enumeration and "
                "Selection can subset a run, but the book assumes a single machine "
                "and serial execution and offers no cross-CPU or CI parallelism."
            ),
            modern_position=(
                "pytest-xdist 'extends pytest with new test execution modes, the "
                "most used being distributing tests across multiple CPUs to speed "
                "up test execution: `pytest -n auto`,' spawning one worker process "
                "per CPU and distributing tests randomly. In CI, actions/"
                "setup-python ('installs a version of Python ... and caches "
                "dependencies for pip') with actions/checkout backs a job that "
                "runs the suite with `-n auto` (or a pytest-split shard)."
            ),
            status="expanded",
            rationale=(
                "2007 predates CI-as-standard and multicore-parallel test "
                "execution; the book's serial model leaves Slow Tests unaddressed "
                "at scale. Parallelism is now the default fast-feedback mechanism."
            ),
            sources=[
                "https://pytest-xdist.readthedocs.io/en/latest/",
                "https://github.com/actions/setup-python",
            ],
            affected=[
                "pattern:test-runner",
                "pattern:test-suite-object",
                "pattern:test-enumeration",
                "smell:slow-tests",
                "principle:keep-tests-independent",
                "principle:isolate-the-sut",
                "goal:repeatable-test",
            ],
            rule_change=(
                "Run tests in parallel (`-n auto` locally; matrix + xdist in CI) "
                "but keep every test independent and hermetic — parallelism "
                "amplifies shared-state bugs."
            ),
        ),
        "CI and execution",
    ),
    _ModItem(
        _rec(
            id="modern:monorepo-suite-partitioning",
            topic="Shard a monorepo-scale suite across CI jobs",
            book_position=(
                "Test Suite Object / Named Test Suite group a Composite of tests "
                "to run together in one pass; there is no notion of partitioning a "
                "single suite across parallel CI jobs."
            ),
            modern_position=(
                "pytest-split 'splits the test suite to equally sized sub-suites "
                "based on test execution time' via `pytest --splits N --group M`, "
                "letting each CI matrix job run one shard; durations persisted in "
                ".test_durations feed the duration-based algorithm so shards stay "
                "~equal in runtime."
            ),
            status="expanded",
            rationale=(
                "2007 predates CI job matrices and monorepo suites too large to run "
                "on one runner; without sharding, CI feedback grows with suite size. "
                "Sharding keeps feedback time roughly constant as the repo grows."
            ),
            sources=["https://jerry-git.github.io/pytest-split"],
            affected=[
                "pattern:test-suite-object",
                "pattern:named-test-suite",
                "pattern:test-selection",
                "smell:slow-tests",
                "goal:repeatable-test",
                "goal:fully-automated-test",
            ],
            rule_change=(
                "Persist test durations and shard the suite (`--splits/--group`) "
                "across CI matrix jobs so each job runs an equal shard; refresh "
                "durations after major suite changes."
            ),
        ),
        "CI and execution",
    ),
]

# --------------------------------------------------------------------------- #
# M8f — Randomness, snapshots & service boundaries                            #
# --------------------------------------------------------------------------- #

_M8F: list[_ModItem] = [
    _ModItem(
        _rec(
            id="modern:random-test-ordering",
            topic="Shuffled, repeatable test ordering and per-test random seeds",
            book_position=(
                "Tests run in source/declaration order; the book's Repeated Test "
                "(Running Tests More Than Once) re-runs the same sequence and gives no "
                "mechanism to randomize order or to control the random seed used by a "
                "test."
            ),
            modern_position=(
                "pytest-randomly 'randomly shuffles the order of test items... [and] "
                "resets Python's global random seed to a fixed value' derived from a "
                "base `--randomly-seed` per test, so ordering faults surface "
                "deterministically and each test gets a repeatable but distinct seed."
            ),
            status="expanded",
            rationale=(
                "Static order hides inter-test coupling; randomized order with a fixed, "
                "reproducible seed surfaces ordering dependencies without introducing "
                "flakiness."
            ),
            sources=["https://github.com/pytest-dev/pytest-randomly"],
            affected=[
                "goal:repeatable-test",
                "pattern:test-enumeration",
                "smell:erratic-test",
                "smell:fragile-test",
                "principle:keep-tests-independent",
                "principle:design-for-testability",
            ],
            rule_change=(
                "Run pytest-randomly in CI with a recorded --randomly-seed; if a test "
                "only passes in declaration order, fix the hidden dependency."
            ),
        ),
        "Runtime and determinism",
    ),
    _ModItem(
        _rec(
            id="modern:snapshot-golden",
            topic="Snapshot / golden-master assertions for large computed output",
            book_position=(
                "Assertions compare against hand-written expected values (Assertion "
                "Method / Expected Value); the book has no pattern for comparing a "
                "computed result against a stored, version-controlled canonical "
                "rendering."
            ),
            modern_position=(
                "Syrupy is 'a zero-dependency pytest snapshot plugin. It enables "
                "developers to write tests which assert immutability of computed "
                "results.' `assert actual == snapshot`; snapshots live in committed "
                "`__snapshots__` dirs and are refreshed via `pytest --snapshot-update`."
            ),
            status="expanded",
            rationale=(
                "Hand-maintaining large expected blobs is brittle and scales poorly; "
                "golden-master comparison with a committed baseline catches unintended "
                "regressions in rendered output."
            ),
            sources=["https://github.com/syrupy-project/syrupy"],
            affected=[
                "pattern:assertion-method",
                "smell:fragile-test",
                "principle:verify-one-condition-per-test",
                "goal:tests-as-safety-net",
            ],
            rule_change=(
                "For large/structured outputs, assert against a syrupy snapshot in a "
                "committed `__snapshots__` dir; review diffs via --snapshot-details, "
                "never blindly --snapshot-update."
            ),
        ),
        "Snapshot & boundary testing",
    ),
    _ModItem(
        _rec(
            id="modern:api-boundary-mocking",
            topic="Hermetic HTTP service boundary testing",
            book_position=(
                "Tests of HTTP clients/servers depend on a real external service or on "
                "Back-Door Manipulation of a shared fixture; the book offers no per-test, "
                "programmatically-configured transport."
            ),
            modern_position=(
                "httpx provides a `transport=` abstraction; `httpx.MockTransport("
                "handler)` 'return pre-determined responses, rather than making actual "
                "network requests,' so HTTP-client tests assert outbound requests "
                "against a hermetic, in-process server."
            ),
            status="expanded",
            rationale=(
                "Depending on a live third-party service makes tests slow, flaky, and "
                "rate-limited; MockTransport makes boundary assertions hermetic and "
                "repeatable."
            ),
            sources=["https://www.python-httpx.org/advanced/transports/"],
            affected=[
                "pattern:layer-test",
                "pattern:back-door-manipulation",
                "smell:fragile-test",
                "smell:erratic-test",
                "principle:isolate-the-sut",
                "principle:use-the-front-door-first",
                "goal:repeatable-test",
            ],
            rule_change=(
                "For HTTP clients, inject httpx.MockTransport (or pytest-httpserver) so "
                "the test never hits the network; assert expected requests were issued."
            ),
        ),
        "Service & browser testing",
    ),
    _ModItem(
        _rec(
            id="modern:cross-version-matrix",
            topic="Cross-version / cross-platform test gating",
            book_position=(
                "Test Runner runs one process; Test Selection subsets cases but the book "
                "assumes a single environment and gives no mechanism to gate on "
                "interpreter or OS version."
            ),
            modern_position=(
                "tox 'checking your package builds and installed correctly under "
                "different environments (such as different Python implementations, "
                "versions or installation dependencies)' and runs the suite in each env "
                "(e.g. py310-py313, pypy); GitHub Actions `matrix` + `setup-python` "
                "extend this across operating systems."
            ),
            status="expanded",
            rationale=(
                "A test that passes on one interpreter/OS can fail elsewhere "
                "(platform-dependent behavior); matrix execution is the modern baseline "
                "for portability."
            ),
            sources=["https://tox.wiki/en/latest/", "https://github.com/actions/setup-python"],
            affected=[
                "pattern:test-runner",
                "pattern:test-selection",
                "smell:production-bugs",
                "principle:design-for-testability",
                "goal:repeatable-test",
            ],
            rule_change=(
                "Gate every PR against a tox/GitHub-Actions matrix spanning supported "
                "Python versions and operating systems; do not ship platform "
                "assumptions untested."
            ),
        ),
        "CI and execution",
    ),
]

MODERN_RECORDS: list[dict[str, Any]] = [item.record for item in _M8A] + [
    item.record for item in _M8B
] + [item.record for item in _M8C] + [item.record for item in _M8D] + [
    item.record for item in _M8E
] + [item.record for item in _M8F]
_MODERN_CATEGORIES: dict[str, str] = {
    **{item.record["id"]: item.category for item in _M8A},
    **{item.record["id"]: item.category for item in _M8B},
    **{item.record["id"]: item.category for item in _M8C},
    **{item.record["id"]: item.category for item in _M8D},
    **{item.record["id"]: item.category for item in _M8E},
    **{item.record["id"]: item.category for item in _M8F},
}


# --------------------------------------------------------------------------- #
# Markdown digest                                                               #
# --------------------------------------------------------------------------- #

def _write_digest(out: Path, records: list[dict[str, Any]]) -> None:
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_cat.setdefault(_MODERN_CATEGORIES.get(r["id"], "Other"), []).append(r)
    lines: list[str] = ["# Current testing practices (modernization summary)", ""]
    lines.append(
        f"_Review date: `{REVIEW_DATE}`. Derived from authoritative primary/"
        "official documentation; book-derived principles remain distinguishable "
        "(`origin` field on each knowledge record)._ "
    )
    lines.append("")
    for cat in sorted(by_cat):
        lines.append(f"## {cat}")
        lines.append("")
        for r in by_cat[cat]:
            lines.append(f"### {r['topic']}")
            lines.append(f"- **Book position:** {r['book_position']}")
            lines.append(f"- **Modern position:** {r['modern_position']}")
            lines.append(f"- **Status:** `{r['status']}`")
            lines.append(f"- **Rationale:** {r['rationale']}")
            lines.append("- **Sources:** " + ", ".join(r.get("official_sources", [])))
            lines.append(
                "- **Affected knowledge:** " + ", ".join(r.get("affected_knowledge_ids", []))
            )
            if r.get("agent_rule_change"):
                lines.append(f"- **Agent rule change:** {r['agent_rule_change']}")
            lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Entry point                                                                   #
# --------------------------------------------------------------------------- #

def run_modernization() -> None:
    """Stage 8 entry point: emit validated modernization records from research."""
    settings = load_settings()
    settings.paths.ensure_knowledge_dirs()
    p = settings.paths

    records = list(MODERN_RECORDS)
    # Every record is constructed through ModernizationRecord above, so it is
    # already schema-valid; re-validate explicitly to fail fast on any drift.
    for r in records:
        ModernizationRecord(**r)

    out = p.knowledge_modern_dir / "modernization.jsonl"
    write_jsonl(out, records)
    _write_digest(p.knowledge_modern_dir / "current-testing-practices.md", records)
    console.print(
        f"[green]modernized {len(records)} records -> {out.relative_to(p.repo_root)}[/green]"
    )
