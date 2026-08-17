# Evaluation methodology (Stage 10a / M10a)

This document describes how Agentic Testcraft is evaluated. **M10a only builds the
deterministic harness and scoring infrastructure; it does not simulate any
candidate solution and does not invoke an LLM.** Real A/B execution
(M10b) runs a coding agent in two conditions and feeds its `tests/` into this
harness. The status M10a leaves the project in is:

> *evaluation infrastructure complete; real A/B execution pending*

Run `agentic-testcraft eval --help` for the subcommand surface.

## 1. A/B method

An agent is run against the same suite of evaluation cases in two conditions:

- **baseline** — the agent **without** the Agentic Testcraft skill (or a neutral
  prompt).
- **skill** — the agent **with** the Agentic Testcraft skill loaded.

For each run the agent produces a `tests/` directory (and optionally a git diff
patch of the SUT). The harness imports those tests via `eval score` and computes
metric + rubric evidence. M10a compares `baseline` vs `skill` per case
(`compare_runs` / `report`) and aggregates wins/losses and defects-caught deltas.

The harness never generates or grades the agent's `tests/` itself; it only
**scores** `tests/` that a real agent produced. The `run_evals` entry point merely
reports readiness when no real agent is available — it does not fake results.

## 2. Cases

The committed catalog lives in `src/agentic_testcraft/evals.py` as `CASE_CATALOG`
(26 cases). Each case is a small System-Under-Test plus one or two **seeded
defect** variants and a task prompt.

- `eval list-cases` — print all case ids/titles.
- `eval init-cases [--target DIR]` — materialize the catalog to disk for
  inspection (per-case `case.toml`, `task.md`, empty `tests/`).
- `eval setup <case> [--defect ID] [--dest DIR]` — materialize one case sandbox:
  `sut.py` (correct SUT, or the chosen defect variant), an empty `tests/`, and
  `task.md`. An agent edits `tests/` here.

A real agent's workflow per case:

1. `eval setup <case> --dest <sandbox>` (optionally `--defect <id>` to reproduce a
   known-bad SUT).
2. The agent writes `tests/test_*.py` inside `<sandbox>/tests/`.
3. `eval score <case> --tests <sandbox/tests> --condition skill|baseline
   --model <model> --agent <agent> [--patch <diff>]` imports the tests, runs
   pytest, and writes `evals/results/<case>-<condition>.json`.
4. `eval report` aggregates all result files into `evals/results/report.json`.

## 3. Metrics

The harness computes these deterministic signals (a case's `key_metrics` selects
which are discriminating for that case):

| Metric | Meaning |
|---|---|
| `generated_tests_pass` | all agent tests pass on the **correct** SUT |
| `seeded_defects_caught` | count of seeded defect variants that a passing test now fails |
| `mutation_score` | `seeded_defects_caught / total_defects` (0–1) |
| `independent_execution` | tests pass under randomized ordering (pytest-randomly) |
| `randomized_order_execution` | same run, second seed — stable |
| `repeated_run_stability` | the same SUT+tests pass on a second clean run |
| `test_runtime_seconds` | wall-clock pytest runtime (parsed from output) |
| `production_files_modified` | count of SUT `.py` files touched in the imported patch |
| `unnecessary_dependencies_introduced` | imports beyond stdlib/pytest/SUT |
| `sut_mocked` | tests patch/mock the `sut` module itself |
| `unnecessary_interaction_assertions` | `assert_called*`/`_mock_` style assertions |
| `shared_mutable_fixture` | module/session-scoped fixtures detected |
| `explicit_sleeps` | `time.sleep` / `sleep(...)` calls in tests |

## 4. Mutation testing

`mutation_score` is the fraction of seeded defects caught. **mutmut / atheris are
not installed** in this environment, so the harness uses the committed
seeded-defect variants as the mutation mutants (the same fault-injection idea: a
passing test suite that survives a defect is a weak suite). A defect is "caught"
iff the agent's tests **pass on the correct SUT and fail when that single defect
is applied** — i.e. the tests actually pin the intended invariant.

## 5. Qualitative rubric

Eight dimensions, each scored 0–4 by an independent judge (human or LLM). The
harness emits only the 0–4 **anchor text** and coarse automated **proxies** (e.g.
an `explicit_sleep` → `diagnostic_quality` proxy of 1); most dimensions are left
`null` for the judge:

- `behavior_focus` — asserts observable behavior, not internals.
- `intent_readability` — self-describing test intent.
- `fixture_minimality` — fresh/minimal per-test fixtures.
- `overspecification` — contract-level assertions, no call-count asserts.
- `dependency_strategy` — right double (real when fast/deterministic/safe).
- `maintainability` — low-cost, clear, non-brittle.
- `diagnostic_quality` — a failure names the failed condition.
- `appropriate_test_boundary` — unit/integration boundary matches the behavior.

## 6. Determinism, timeouts, and optional dependencies

- pytest is invoked as a subprocess with `-p no:cacheprovider`; each case has a
  120s timeout.
- Randomized-order/independence metrics use `pytest-randomly` **if installed**;
  otherwise they are recorded as `null` (never crash the run).
- `httpx`/`sqlite3`/`async` cases require those libraries in the execution
  environment.

## 7. Limitations

- No end-to-end simulated agent: A/B results require real agent runs (M10b).
- Rubric proxies are coarse; qualitative dimensions require a judge.
- `mutation_score` approximates mutmut/atheris via seeded defects only.
- Static AST scorers are heuristic (e.g. `sut_mocked` flags `import sut`+mock
  patterns, not semantic mocking).
