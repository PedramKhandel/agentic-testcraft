"""Stage 10a — deterministic evaluation infrastructure for Agentic Testcraft.

M10a builds the *harness* that scores outputs produced later by **real** coding-agent
runs (M10b). It never simulates a candidate solution:

- The catalog (`CASE_CATALOG`) is a committed set of ~26 eval cases. Each case is a
  small, correct System-Under-Test plus one or more *seeded defect* variants and a
  task prompt describing what to test.
- `setup_case` materializes a case into a sandbox dir (SUT + empty ``tests/`` +
  task prompt) that a real agent edits, then the agent's produced ``tests/`` is
  imported via `score_run`.
- `score_run` drops the agent's tests into the sandbox, runs pytest (with the
  seeded defect active), and computes deterministic metrics (pass/fail, defect
  caught, runtime) plus AST-based static scorers (sleeps, doubles, shared
  fixtures, SUT mocked, interaction assertions, dependencies) and coarse rubric
  proxies. Qualitative rubric dimensions are emitted as 0–4 anchors ready for an
  independent human/LLM judge.
- `compare_runs` / `report` aggregate baseline vs. skill results.

No LLM is invoked here; M10a finishes with status
"evaluation infrastructure complete; real A/B execution pending" unless a real
agent can be run in the environment.

Run `agentic-testcraft eval --help` for the subcommand surface.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import typer
from pydantic import BaseModel, Field, field_validator

from .config import load_settings

EVAL_APP = typer.Typer(name="eval", help="M10 evaluation harness (cases, setup, score, compare).")

# Canonical metric keys computed by the harness. A case's `key_metrics` selects
# which of these are the discriminating metrics for that case.
METRIC_KEYS: list[str] = [
    "generated_tests_pass",
    "seeded_defects_caught",
    "mutation_score",
    "independent_execution",
    "randomized_order_execution",
    "repeated_run_stability",
    "test_runtime_seconds",
    "production_files_modified",
    "unnecessary_dependencies_introduced",
    "sut_mocked",
    "unnecessary_interaction_assertions",
    "shared_mutable_fixture",
    "explicit_sleeps",
]

# Qualitative rubric dimensions (0-4 anchored). The harness fills coarse proxies
# where deterministic; remaining dims are left for an independent judge.
RUBRIC_DIMS: list[str] = [
    "behavior_focus",
    "intent_readability",
    "fixture_minimality",
    "overspecification",
    "dependency_strategy",
    "maintainability",
    "diagnostic_quality",
    "appropriate_test_boundary",
]


# --------------------------------------------------------------------------- #
# Schemas                                                                     #
# --------------------------------------------------------------------------- #

class CaseDefect(BaseModel):
    """A seeded defect: an alternate, incorrect SUT source."""
    defect_id: str
    description: str
    sut_src: str


class EvalCase(BaseModel):
    """A committed evaluation case (case schema)."""
    case_id: str
    title: str
    category: str
    task: str
    sut_src: str
    defects: list[CaseDefect]
    key_metrics: list[str] = Field(default_factory=list)
    rubric_focus: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("case_id")
    @classmethod
    def _cid(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9-]{2,40}", v):
            raise ValueError("case_id must be lowercase-dashes, 2-40 chars")
        return v


class RunMetadata(BaseModel):
    """Metadata describing a real agent run that produced a `tests/` dir."""
    case_id: str
    condition: Literal["baseline", "skill"]
    agent: str
    model: str
    started_at: datetime
    finished_at: datetime | None = None
    budget: dict[str, Any] = Field(default_factory=dict)
    patch: str | None = None  # path to an imported git diff/patch, if any


class RubricScore(BaseModel):
    score: int | None = None  # 0-4; None = not yet judged
    anchor: str
    notes: str = ""


class EvalResult(BaseModel):
    """Result of scoring one agent run on one case (result schema)."""
    case_id: str
    condition: Literal["baseline", "skill"]
    run_meta: RunMetadata
    metrics: dict[str, Any] = Field(default_factory=dict)
    rubric: dict[str, RubricScore] = Field(default_factory=dict)
    scored_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    passed: bool = False  # all tests pass on the *correct* SUT
    defect_caught: dict[str, bool] = Field(default_factory=dict)  # defect_id -> caught
    errors: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Case catalog                                                                 #
# --------------------------------------------------------------------------- #

class _Spec(BaseModel):
    case_id: str
    title: str
    category: str
    task: str
    sut_src: str
    defects: list[CaseDefect]
    key_metrics: list[str]
    rubric_focus: list[str]
    tags: list[str]


def _c(s: _Spec) -> EvalCase:
    return EvalCase(**s.model_dump())


CASE_CATALOG: list[EvalCase] = [
    _c(_Spec(
        case_id="pure-function",
        title="Pure deterministic function",
        category="logic",
        task="Write pytest tests for `add`. Cover the happy path, negatives, and zero. Do not import anything beyond pytest.",
        sut_src="def add(a, b):\n    return a + b\n",
        defects=[CaseDefect(defect_id="negation", description="returns a-b instead of a+b",
                            sut_src="def add(a, b):\n    return a - b\n")],
        key_metrics=["seeded_defects_caught", "mutation_score"],
        rubric_focus=["behavior_focus", "diagnostic_quality"],
        tags=["logic"],
    )),
    _c(_Spec(
        case_id="boundary-validation",
        title="Boundary validation / off-by-one",
        category="logic",
        task="Write tests for `clamp`. Specifically assert the lower and upper boundaries inclusive.",
        sut_src="def clamp(value, lo, hi):\n    if value < lo:\n        return lo\n    if value > hi:\n        return hi\n    return value\n",
        defects=[CaseDefect(defect_id="off-by-one-hi", description="upper bound exclusive (hi+1)",
                            sut_src="def clamp(value, lo, hi):\n    if value < lo:\n        return lo\n    if value > hi + 1:\n        return hi + 1\n    return value\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["behavior_focus", "diagnostic_quality"],
        tags=["boundary"],
    )),
    _c(_Spec(
        case_id="clock-dependency",
        title="Clock dependency (inject a clock, not the wall clock)",
        category="design",
        task="Write tests for `is_past_deadline`. The SUT is intentionally written against a `clock` callable so tests never touch the wall clock. Assert the boundary between past and future precisely.",
        sut_src="from datetime import datetime\n\ndef now():\n    return datetime.now()\n\ndef is_past_deadline(deadline, clock=now):\n    return clock() > deadline\n",
        defects=[CaseDefect(defect_id="ge-not-gt", description="uses >= so the deadline instant is treated as past",
                            sut_src="from datetime import datetime\n\ndef now():\n    return datetime.now()\n\ndef is_past_deadline(deadline, clock=now):\n    return clock() >= deadline\n")],
        key_metrics=["seeded_defects_caught", "sut_mocked"],
        rubric_focus=["behavior_focus", "dependency_strategy", "appropriate_test_boundary"],
        tags=["clock", "inject-clock"],
    )),
    _c(_Spec(
        case_id="randomness-dependency",
        title="Randomness / UUID dependency (stub the generator, not the SUT)",
        category="design",
        task="Write tests for `make_id`. The SUT accepts a `gen` callable so tests can control the random/UUID source. Assert the produced id encodes the supplied generator output.",
        sut_src="import uuid\n\ndef make_id(gen=uuid.uuid4):\n    raw = gen()\n    return str(raw).replace('-', '')[:12]\n",
        defects=[CaseDefect(defect_id="truncates-too-short", description="truncates to 4 chars instead of 12",
                            sut_src="import uuid\n\ndef make_id(gen=uuid.uuid4):\n    raw = gen()\n    return str(raw).replace('-', '')[:4]\n")],
        key_metrics=["seeded_defects_caught", "sut_mocked"],
        rubric_focus=["dependency_strategy", "behavior_focus"],
        tags=["random", "uuid"],
    )),
    _c(_Spec(
        case_id="external-http-client",
        title="External HTTP client (mock the transport, not the SUT)",
        category="double",
        task="Write tests for `fetch_title`. Use httpx.MockTransport (or an equivalent in-process transport) so no real network call is made. Assert the parsed title and the request URL.",
        sut_src="import httpx\n\ndef fetch_title(url, client=None):\n    client = client or httpx.Client()\n    resp = client.get(url)\n    resp.raise_for_status()\n    return resp.text.split('<title>')[1].split('</title>')[0]\n",
        defects=[CaseDefect(defect_id="split-misses-title", description="index-1 split fails when <title> absent",
                            sut_src="import httpx\n\ndef fetch_title(url, client=None):\n    client = client or httpx.Client()\n    resp = client.get(url)\n    resp.raise_for_status()\n    return resp.text.split('<title>')[-1].split('</title>')[0]\n")],
        key_metrics=["seeded_defects_caught", "sut_mocked", "unnecessary_interaction_assertions"],
        rubric_focus=["dependency_strategy", "behavior_focus"],
        tags=["http", "httpx-mock"],
    )),
    _c(_Spec(
        case_id="database-repository",
        title="Database repository (disposable/transient DB, not a shared fixture)",
        category="integration",
        task="Write tests for `UserRepository.save`/`find`. Use a fresh, function-scoped sqlite3 in-memory database per test; do not share rows across tests.",
        sut_src="import sqlite3\n\nclass UserRepository:\n    def __init__(self, conn):\n        self.conn = conn\n        self.conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')\n        self.conn.commit()\n    def save(self, name):\n        cur = self.conn.execute('INSERT INTO users (name) VALUES (?)', (name,))\n        self.conn.commit()\n        return cur.lastrowid\n    def find(self, id_):\n        row = self.conn.execute('SELECT name FROM users WHERE id=?', (id_,)).fetchone()\n        return row[0] if row else None\n",
        defects=[CaseDefect(defect_id="find-by-name-not-id", description="find selects by name column instead of id",
                            sut_src="import sqlite3\n\nclass UserRepository:\n    def __init__(self, conn):\n        self.conn = conn\n        self.conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')\n        self.conn.commit()\n    def save(self, name):\n        cur = self.conn.execute('INSERT INTO users (name) VALUES (?)', (name,))\n        self.conn.commit()\n        return cur.lastrowid\n    def find(self, id_):\n        row = self.conn.execute('SELECT name FROM users WHERE name=?', (id_,)).fetchone()\n        return row[0] if row else None\n")],
        key_metrics=["seeded_defects_caught", "shared_mutable_fixture"],
        rubric_focus=["fixture_minimality", "appropriate_test_boundary"],
        tags=["sqlite", "repository"],
    )),
    _c(_Spec(
        case_id="file-system-dependency",
        title="File-system dependency (tmp_path, not the repo tree)",
        category="design",
        task="Write tests for `write_log`. The SUT appends to a path; tests must use pytest's tmp_path fixture and never write into the repository tree.",
        sut_src="from pathlib import Path\n\ndef write_log(path, line):\n    p = Path(path)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    with p.open('a') as fh:\n        fh.write(line + '\\n')\n    return p.stat().st_size\n",
        defects=[CaseDefect(defect_id="truncates-file", description="opens in 'w' mode, truncating prior content",
                            sut_src="from pathlib import Path\n\ndef write_log(path, line):\n    p = Path(path)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    with p.open('w') as fh:\n        fh.write(line + '\\n')\n    return p.stat().st_size\n")],
        key_metrics=["seeded_defects_caught", "production_files_modified"],
        rubric_focus=["dependency_strategy", "diagnostic_quality"],
        tags=["filesystem", "tmp_path"],
    )),
    _c(_Spec(
        case_id="event-publisher",
        title="Event publisher (interaction IS the requirement)",
        category="double",
        task="Write tests for `order_placed` which must publish an `OrderCreated` event to the bus. Here the interaction itself is the observable behavior — assert the bus received the expected event payload.",
        sut_src="def order_placed(bus, order_id):\n    bus.publish('OrderCreated', {'order_id': order_id})\n    return order_id\n",
        defects=[CaseDefect(defect_id="wrong-event-type", description="publishes 'OrderSaved' instead of 'OrderCreated'",
                            sut_src="def order_placed(bus, order_id):\n    bus.publish('OrderSaved', {'order_id': order_id})\n    return order_id\n")],
        key_metrics=["seeded_defects_caught", "unnecessary_interaction_assertions"],
        rubric_focus=["dependency_strategy", "behavior_focus"],
        tags=["event", "interaction-is-behavior"],
    )),
    _c(_Spec(
        case_id="async-service",
        title="Async service (async runner, not synchronous unwrap)",
        category="runtime",
        task="Write async tests for `fetch_json` using an async httpx transport. Mark tests async and run under an async-capable runner; do not synchronously unwrap the coroutine.",
        sut_src="import httpx\n\nasync def fetch_json(url, client=None):\n    client = client or httpx.AsyncClient()\n    async with client:\n        resp = await client.get(url)\n        resp.raise_for_status()\n        return resp.json()\n",
        defects=[CaseDefect(defect_id="returns-text-not-json", description="returns resp.text instead of resp.json()",
                            sut_src="import httpx\n\nasync def fetch_json(url, client=None):\n    client = client or httpx.AsyncClient()\n    async with client:\n        resp = await client.get(url)\n        resp.raise_for_status()\n        return resp.text\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["behavior_focus", "dependency_strategy"],
        tags=["async", "httpx"],
    )),
    _c(_Spec(
        case_id="flaky-sleep-test",
        title="Flaky sleep-based test (no real sleeps; deterministic control)",
        category="smell",
        task="The SUT `retry_after` waits with a backoff capped at 3 attempts. Write tests that exercise the attempt-count and backoff without introducing real `time.sleep` calls.",
        sut_src="def retry_after(attempts=3, delay=0.5):\n    sleeps = []\n    for i in range(attempts):\n        try:\n            return 'ok'\n        except Exception:\n            if i < attempts - 1:\n                sleeps.append(delay * (2 ** i))\n    return 'failed'\n",
        defects=[CaseDefect(
            defect_id="off-by-one-attempts",
            description="ranges over attempts-1 iterations (one fewer retry than configured)",
            sut_src="def retry_after(attempts=3, delay=0.5):\n    sleeps = []\n    for i in range(attempts - 1):\n        try:\n            return 'ok'\n        except Exception:\n            if i < attempts - 1:\n                sleeps.append(delay * (2 ** i))\n    return 'failed'\n",
        )],
        key_metrics=["explicit_sleeps", "seeded_defects_caught"],
        rubric_focus=["maintainability", "diagnostic_quality"],
        tags=["flaky", "retry", "no-sleep"],
    )),
    _c(_Spec(
        case_id="shared-mutable-fixture",
        title="Shared mutable fixture (fresh per test)",
        category="smell",
        task="The SUT `Counter` is stateful. Write tests that start from a fresh Counter each test; do not leak counts across tests via module/session scope.",
        sut_src="class Counter:\n    def __init__(self):\n        self.value = 0\n    def inc(self):\n        self.value += 1\n        return self.value\n    def reset(self):\n        self.value = 0\n",
        defects=[CaseDefect(defect_id="inc-resets", description="inc resets value to 0 before incrementing",
                            sut_src="class Counter:\n    def __init__(self):\n        self.value = 0\n    def inc(self):\n        self.value = 0\n        self.value += 1\n        return self.value\n    def reset(self):\n        self.value = 0\n")],
        key_metrics=["shared_mutable_fixture", "seeded_defects_caught", "independent_execution"],
        rubric_focus=["fixture_minimality"],
        tags=["fixture", "state"],
    )),
    _c(_Spec(
        case_id="expensive-fixture",
        title="Expensive fixture (function scope, not session)",
        category="smell",
        task="The SUT reads a large fixture file. Write tests that build the fixture per-test via a function-scoped fixture (or tmp), not a session-scoped shared object.",
        sut_src="import json, os\n\nDATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')\n\ndef load_records(path=DATA_FILE):\n    with open(path) as fh:\n        return json.load(fh)\n\ndef count_active(records):\n    return sum(1 for r in records if r.get('active'))\n",
        defects=[CaseDefect(defect_id="counts-active-wrong", description="counts inactive instead of active",
                            sut_src="import json, os\n\nDATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')\n\ndef load_records(path=DATA_FILE):\n    with open(path) as fh:\n        return json.load(fh)\n\ndef count_active(records):\n    return sum(1 for r in records if not r.get('active'))\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["fixture_minimality", "maintainability"],
        tags=["fixture", "io"],
    )),
    _c(_Spec(
        case_id="over-mocking-trap",
        title="Over-mocking trap (mock only the boundary, not the SUT)",
        category="double",
        task="The SUT `TaxCalculator` composes a `RateProvider`. Write tests that stub `RateProvider` (the DOC) but never mock/patch the `TaxCalculator` itself.",
        sut_src="class RateProvider:\n    def get(self, region):\n        return 0.2\n\nclass TaxCalculator:\n    def __init__(self, rates):\n        self.rates = rates\n    def total(self, amount, region):\n        return amount * self.rates.get(region)\n",
        defects=[CaseDefect(defect_id="doubles-rate", description="halves the rate provider result",
                            sut_src="class RateProvider:\n    def get(self, region):\n        return 0.2\n\nclass TaxCalculator:\n    def __init__(self, rates):\n        self.rates = rates\n    def total(self, amount, region):\n        return amount * self.rates.get(region) * 0.5\n")],
        key_metrics=["sut_mocked", "seeded_defects_caught"],
        rubric_focus=["dependency_strategy", "appropriate_test_boundary"],
        tags=["double", "no-mock-sut"],
    )),
    _c(_Spec(
        case_id="state-vs-behavior",
        title="State vs behavior verification (assert outcomes, not calls)",
        category="double",
        task="The SUT `append_unique` mutates a list. Assert the resulting list contents; do not assert that `.append` was called.",
        sut_src="def append_unique(items, value):\n    if value not in items:\n        items.append(value)\n    return items\n",
        defects=[CaseDefect(defect_id="allows-duplicates", description="appends even when value already present",
                            sut_src="def append_unique(items, value):\n    items.append(value)\n    return items\n")],
        key_metrics=["unnecessary_interaction_assertions"],
        rubric_focus=["behavior_focus", "overspecification"],
        tags=["state-vs-behavior"],
    )),
    _c(_Spec(
        case_id="interaction-is-requirement",
        title="Interaction really IS the requirement (audit log)",
        category="double",
        task="The SUT `transfer` MUST call `audit.log` with the transfer tuple. Here asserting the interaction is correct; do assert it precisely and nothing more.",
        sut_src="def transfer(audit, frm, to, amount):\n    audit.log(('transfer', frm, to, amount))\n    return amount\n",
        defects=[CaseDefect(defect_id="logs-wrong-field", description="logs to instead of frm",
                            sut_src="def transfer(audit, frm, to, amount):\n    audit.log(('transfer', to, frm, amount))\n    return amount\n")],
        key_metrics=["seeded_defects_caught", "unnecessary_interaction_assertions"],
        rubric_focus=["behavior_focus"],
        tags=["interaction-is-behavior"],
    )),
    _c(_Spec(
        case_id="fake-vs-stub",
        title="Fake vs stub choice (real semantics when fast/deterministic/safe)",
        category="double",
        task="The SUT `Report` needs a `Clock`. A `FixedClock` real double is fast, deterministic, and safe. Use it rather than stubbing each call.",
        sut_src="class Clock:\n    def now(self):\n        ...\n\nclass Report:\n    def __init__(self, clock):\n        self.clock = clock\n    def stamp(self):\n        return str(self.clock.now())\n",
        defects=[CaseDefect(defect_id="stamp-not-str", description="stamp returns the raw datetime, not str()",
                            sut_src="class Clock:\n    def now(self):\n        ...\n\nclass Report:\n    def __init__(self, clock):\n        self.clock = clock\n    def stamp(self):\n        return self.clock.now()\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["dependency_strategy"],
        tags=["fake-vs-stub", "real-double"],
    )),
    _c(_Spec(
        case_id="spy-vs-mock",
        title="Spy vs mock choice (record then assert, no expectation object)",
        category="double",
        task="The SUT `Greeter` calls `notifier.send`. Write tests that spy on `send` (record calls, assert after) rather than pre-programming a Mock expectation.",
        sut_src="class Greeter:\n    def __init__(self, notifier):\n        self.notifier = notifier\n    def greet(self, name):\n        msg = f'Hi, {name}'\n        self.notifier.send(msg)\n        return msg\n",
        defects=[CaseDefect(defect_id="greeting-prefix", description="greeting uses 'Hello' instead of 'Hi,'",
                            sut_src="class Greeter:\n    def __init__(self, notifier):\n        self.notifier = notifier\n    def greet(self, name):\n        msg = f'Hello, {name}'\n        self.notifier.send(msg)\n        return msg\n")],
        key_metrics=["seeded_defects_caught", "unnecessary_interaction_assertions"],
        rubric_focus=["dependency_strategy", "behavior_focus"],
        tags=["spy-vs-mock"],
    )),
    _c(_Spec(
        case_id="obscure-giant-fixture",
        title="Obscure/giant fixture (minimal, intention-revealing setup)",
        category="smell",
        task="The SUT `parse` parses a record dict. Write tests with small, explicit inputs inline; do not build a giant shared fixture that obscures the case under test.",
        sut_src="def parse(rec):\n    return {'id': rec['id'], 'active': bool(rec.get('active', False))}\n",
        defects=[CaseDefect(defect_id="bool-coerces-truthy", description="uses rec.get('active') without bool()",
                            sut_src="def parse(rec):\n    return {'id': rec['id'], 'active': rec.get('active', False)}\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["intent_readability", "fixture_minimality"],
        tags=["obscure-test", "fixture"],
    )),
    _c(_Spec(
        case_id="mystery-guest",
        title="Mystery guest (all inputs visible in the test)",
        category="smell",
        task="The SUT `format_name` reads a module-level `DEFAULT_PREFIX`. Tests must set up and tear down that prefix within the test so the fixture is not a mystery guest.",
        sut_src="DEFAULT_PREFIX = 'Mr'\n\ndef format_name(first, last, prefix=DEFAULT_PREFIX):\n    return f'{prefix} {first} {last}'\n",
        defects=[CaseDefect(defect_id="default-prefix-hardcoded-space", description="uses ' ' join that breaks when prefix is empty",
                            sut_src="DEFAULT_PREFIX = 'Mr'\n\ndef format_name(first, last, prefix=DEFAULT_PREFIX):\n    parts = [prefix, first, last]\n    return ' '.join(p for p in parts if p)\n")],
        key_metrics=["seeded_defects_caught", "shared_mutable_fixture"],
        rubric_focus=["fixture_minimality", "diagnostic_quality"],
        tags=["mystery-guest"],
    )),
    _c(_Spec(
        case_id="assertion-roulette",
        title="Assertion roulette (labeled / message assertions)",
        category="smell",
        task="The SUT `classify` returns a category. Write tests with explicit, self-describing assertions (or assertion functions) so a failure names the failed condition.",
        sut_src="def classify(score):\n    if score >= 90: return 'A'\n    if score >= 80: return 'B'\n    if score >= 70: return 'C'\n    return 'F'\n",
        defects=[CaseDefect(defect_id="b-and-c-swapped", description="C threshold uses 70 but returns B for 75",
                            sut_src="def classify(score):\n    if score >= 90: return 'A'\n    if score >= 80: return 'C'\n    if score >= 70: return 'B'\n    return 'F'\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["intent_readability", "diagnostic_quality"],
        tags=["assertion-roulette", "branching"],
    )),
    _c(_Spec(
        case_id="conditional-test-logic",
        title="Conditional test logic (no if/try inside tests)",
        category="smell",
        task="The SUT `validate` returns a bool. Write one test per condition (valid/invalid/empty) without `if`/`try` inside test bodies.",
        sut_src="def validate(token):\n    if not token:\n        return False\n    if not token.isalnum():\n        return False\n    return len(token) >= 8\n",
        defects=[CaseDefect(defect_id="empty-passes", description="empty token returns True (missing not-token guard effect)",
                            sut_src="def validate(token):\n    if not token.isalnum():\n        return False\n    return len(token) >= 8\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["intent_readability", "behavior_focus"],
        tags=["conditional-test-logic", "validation"],
    )),
    _c(_Spec(
        case_id="brittle-implementation-detail",
        title="Brittle implementation-detail testing (assert behavior, not internals)",
        category="smell",
        task="The SUT `to_csv` returns a string. Test the returned content at the record level; do not assert on private helper names or internal line-ordering beyond what the contract specifies.",
        sut_src="def to_csv(rows):\n    lines = ['id,value']\n    for r in rows:\n        lines.append(f\"{r['id']},{r['value']}\")\n    return '\\n'.join(lines)\n",
        defects=[CaseDefect(defect_id="no-header", description="omits the header row",
                            sut_src="def to_csv(rows):\n    lines = []\n    for r in rows:\n        lines.append(f\"{r['id']},{r['value']}\")\n    return '\\n'.join(lines)\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["behavior_focus", "overspecification"],
        tags=["brittle-test", "contract"],
    )),
    _c(_Spec(
        case_id="hard-to-test-legacy",
        title="Hard-to-test legacy code (minimal seam, no production behavior change)",
        category="design",
        task="The SUT `send_all` calls a module-level `dispatch`. Introduce the smallest seam (inject `dispatch`) to test `send_all` without touching external systems; do not add an `if testing` fork.",
        sut_src="def dispatch(msg):\n    return {'sent': msg}\n\ndef send_all(msgs, dispatch_fn=dispatch):\n    return [dispatch_fn(m) for m in msgs]\n",
        defects=[CaseDefect(defect_id="silently-drops", description="drops None messages from the result",
                            sut_src="def dispatch(msg):\n    return {'sent': msg}\n\ndef send_all(msgs, dispatch_fn=dispatch):\n    return [dispatch_fn(m) for m in msgs if m is not None]\n")],
        key_metrics=["seeded_defects_caught", "sut_mocked"],
        rubric_focus=["dependency_strategy", "behavior_focus"],
        tags=["seam", "legacy"],
    )),
    _c(_Spec(
        case_id="justified-testability-refactor",
        title="Justified small production refactor for testability",
        category="design",
        task="The SUT `Service` reads `time.time()` inline. Make the smallest behavior-preserving refactor (inject a clock) so the boundary time is testable; do not add an `if testing` branch.",
        sut_src="import time\n\ndef now():\n    return time.time()\n\ndef Service:\n    def __init__(self, clock=now):\n        self.clock = clock\n    def age(self, ts):\n        return self.clock() - ts\n".replace("def Service:", "class Service:\n    "),
        defects=[CaseDefect(defect_id="age-uses-now-directly", description="age ignores injected clock, calls module time.time()",
                            sut_src="import time\n\ndef age_now():\n    return time.time()\n\nclass Service:\n    def __init__(self, clock=None):\n        self.clock = clock\n    def age(self, ts):\n        return age_now() - ts\n")],
        key_metrics=["seeded_defects_caught", "sut_mocked"],
        rubric_focus=["dependency_strategy", "behavior_focus"],
        tags=["refactor", "seam"],
    )),
    _c(_Spec(
        case_id="integration-boundary",
        title="Integration-boundary (integration test more appropriate than a unit test)",
        category="boundary",
        task="The SUT `sync` reads from a source and writes to a destination. Explain in the test docstring why an integration test against a real tmp_path destination (not mocked) is the right boundary here, then implement it.",
        sut_src="import json, os\n\ndef copy_object(src_dir, dst_dir, name):\n    src = os.path.join(src_dir, name)\n    dst = os.path.join(dst_dir, name)\n    os.makedirs(dst_dir, exist_ok=True)\n    with open(src) as f, open(dst, 'w') as g:\n        json.load(f) and g.write(open(src).read())\n    return dst\n",
        defects=[CaseDefect(defect_id="writes-empty", description="bug: opens dst with 'w' before reading src fully (logic error)",
                            sut_src="import json, os\n\ndef copy_object(src_dir, dst_dir, name):\n    src = os.path.join(src_dir, name)\n    dst = os.path.join(dst_dir, name)\n    os.makedirs(dst_dir, exist_ok=True)\n    data = open(src).read()\n    with open(dst, 'w') as g:\n        g.write('')\n    return dst\n")],
        key_metrics=["seeded_defects_caught"],
        rubric_focus=["appropriate_test_boundary", "behavior_focus"],
        tags=["integration", "boundary"],
    )),
    _c(_Spec(
        case_id="weak-assertions",
        title="Weak assertions that survive mutations",
        category="effectiveness",
        task="The SUT `mean` returns the average. Write tests with concrete value assertions (not just 'returns a number') that would fail if the computation were mutated.",
        sut_src="def mean(values):\n    values = list(values)\n    if not values:\n        raise ValueError('empty')\n    return sum(values) / len(values)\n",
        defects=[CaseDefect(defect_id="sums-not-averaged", description="returns sum(values) instead of the mean",
                            sut_src="def mean(values):\n    values = list(values)\n    if not values:\n        raise ValueError('empty')\n    return sum(values)\n")],
        key_metrics=["seeded_defects_caught", "mutation_score"],
        rubric_focus=["diagnostic_quality", "behavior_focus"],
        tags=["mutation", "weak-assertion"],
    )),
]


def load_cases() -> list[EvalCase]:
    """Return the committed eval-case catalog."""
    return list(CASE_CATALOG)


def get_case(case_id: str) -> EvalCase:
    for c in CASE_CATALOG:
        if c.case_id == case_id:
            return c
    raise KeyError(f"unknown case_id: {case_id}")


def case_ids() -> list[str]:
    return [c.case_id for c in CASE_CATALOG]


# --------------------------------------------------------------------------- #
# Case materialization (setup_case)                                           #
# --------------------------------------------------------------------------- #

def cases_dir() -> Path:
    s = load_settings()
    return s.paths.repo_root / "evals" / "cases"


def init_cases(target: Path | None = None) -> Path:
    """Materialize the committed catalog into on-disk case trees for inspection."""
    base = Path(target) if target else cases_dir()
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    for c in CASE_CATALOG:
        d = base / c.case_id
        (d / "tests").mkdir(parents=True)
        (d / "task.md").write_text(c.task + "\n", encoding="utf-8")
        _write_case_meta(d / "case.toml", c)
    return base


def _write_case_meta(path: Path, case: EvalCase) -> None:
    data = {
        "case_id": case.case_id,
        "title": case.title,
        "category": case.category,
        "key_metrics": case.key_metrics,
        "rubric_focus": case.rubric_focus,
        "tags": case.tags,
        "defects": [d.defect_id for d in case.defects],
    }
    path.write_text(
        "# Auto-generated by `agentic-testcraft eval init-cases`. Edit via CASE_CATALOG in src/agentic_testcraft/evals.py.\n"
        + _dump_simple_toml(data),
        encoding="utf-8",
    )


def _toml_str(s: str) -> str:
    out: list[str] = ['"']
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _dump_simple_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for k, v in data.items():
        if isinstance(v, list):
            inner = ", ".join(_toml_str(str(x)) for x in v)
            lines.append(f"{k} = [{inner}]")
        else:
            lines.append(f"{k} = {_toml_str(str(v))}")
    return "\n".join(lines) + "\n"


def setup_case(
    case_id: str,
    defect_id: str | None = None,
    dest: Path | None = None,
) -> Path:
    """Create a fresh sandbox for a real agent to edit.

    Writes `sut.py` (base, or the chosen defect variant), an empty `tests/` dir,
    and `task.md`. Returns the sandbox root.
    """
    case = get_case(case_id)
    sandbox = Path(dest) if dest else (cases_dir().parent / "_sandbox" / case_id)
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True)
    (sandbox / "tests").mkdir(parents=True)
    (sandbox / "task.md").write_text(case.task + "\n", encoding="utf-8")
    sut_src = case.sut_src
    if defect_id is not None:
        defn = next((d for d in case.defects if d.defect_id == defect_id), None)
        if defn is None:
            raise KeyError(f"unknown defect {defect_id} for case {case.case_id}")
        sut_src = defn.sut_src
    if not sut_src:
        raise ValueError(f"case {case.case_id} has no SUT source (defect variant missing sut_src)")
    (sandbox / "sut.py").write_text(sut_src, encoding="utf-8")
    (sandbox / "conftest.py").write_text(
        "import sys, os\nsys.path.insert(0, os.path.dirname(__file__))\n", encoding="utf-8"
    )
    return sandbox


# --------------------------------------------------------------------------- #
# Test execution + deterministic scorers                                       #
# --------------------------------------------------------------------------- #

_PYTEST = [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider"]


def _run_pytest(workdir: Path, *extra: str) -> tuple[int, str]:
    proc = subprocess.run(
        [*_PYTEST, *extra, str(workdir)],
        cwd=str(workdir),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def _parse_outcome(text: str) -> tuple[int, int, float]:
    """Extract counts and runtime from pytest output (robust to pass/fail ordering)."""
    passed = 0
    failed = 0
    m = re.search(r"(\d+) passed", text)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+) failed", text)
    if m:
        failed = int(m.group(1))
    runtime = 0.0
    rm = re.search(r"in ([\d.]+)s", text)
    if rm:
        runtime = float(rm.group(1))
    return passed, failed, runtime


def _ast_files(tests_dir: Path) -> list[ast.Module]:
    mods: list[ast.Module] = []
    for p in sorted(tests_dir.rglob("test_*.py")) + sorted(tests_dir.rglob("*_test.py")):
        try:
            mods.append(ast.parse(p.read_text(encoding="utf-8"), filename=str(p)))
        except SyntaxError:
            continue
    return mods


def _static_metrics(tests_dir: Path, sut_module: str = "sut") -> dict[str, Any]:
    mods = _ast_files(tests_dir)
    sleeps = 0
    interaction_assertions = 0
    doubles = {"mock": 0, "stub": 0, "spy": 0, "fake": 0}
    sut_mocked = False
    shared_fixture = False
    deps: set[str] = set()
    for mod in mods:
        for node in ast.walk(mod):
            if isinstance(node, ast.Call):
                fn = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
                if re.search(r"\bsleep\b", fn or ""):
                    sleeps += 1
                if re.search(r"\b(assert_called|_mock_)", fn or ""):
                    interaction_assertions += 1
            if isinstance(node, ast.ImportFrom) and node.module and (
                node.module.startswith("unittest.mock") or node.module == "mock"
            ):
                doubles["mock"] += 1
            if isinstance(node, ast.Import):
                for n in node.names:
                    deps.add(n.name.split(".")[0])
            if isinstance(node, ast.ImportFrom) and node.module:
                deps.add(node.module.split(".")[0])
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in {
                "Mock", "MagicMock", "patch", "mock"
            }:
                doubles["mock"] += 1
        for node in ast.walk(mod):
            if isinstance(node, ast.FunctionDef):
                for d in node.decorator_list:
                    ds = ast.unparse(d) if hasattr(ast, "unparse") else ""
                    ds_or = ds or ""
                    if "fixture" in ds_or and "scope=" in ds_or and (
                        "scope=\"module\"" in ds_or or "scope=\"session\"" in ds_or
                    ):
                        shared_fixture = True
    # SUT mocked: a test imports/patches the sut module itself
    for p in sorted(tests_dir.rglob("*.py")):
        txt = p.read_text(encoding="utf-8")
        if ("import sut" in txt or "from sut" in txt) and ("mock.patch" in txt or "unittest.mock" in txt):
            sut_mocked = True
    stdlib_and_pytest = {"pytest", "unittest", "os", "sys", "pathlib", "json", "datetime",
                         "time", "uuid", "httpx", "sqlite3", "typing", "collections"}
    unnecessary_deps = sorted(d for d in deps if not d.startswith("_") and d not in stdlib_and_pytest and d != sut_module and d != "sut")
    return {
        "explicit_sleeps": sleeps,
        "sut_mocked": sut_mocked,
        "shared_mutable_fixture": shared_fixture,
        "test_doubles": doubles,
        "unnecessary_interaction_assertions": interaction_assertions,
        "unnecessary_dependencies_introduced": len(unnecessary_deps),
    }


def _rubric_proxies(metrics: dict[str, Any], case: EvalCase) -> dict[str, RubricScore]:
    """Coarse deterministic rubric proxies; remaining dims are judge-ready (None)."""
    rubric: dict[str, RubricScore] = {}
    for dim in RUBRIC_DIMS:
        rubric[dim] = RubricScore(score=None, anchor=_ANCHORED[dim], notes="")
    # overspecification proxy: high interaction-assertion / mock count is a risk
    if metrics.get("unnecessary_interaction_assertions", 0) > 0 and "interaction" not in " ".join(case.tags):
        rubric["overspecification"].score = 2
        rubric["overspecification"].notes = "interaction assertions present in a state-verified case"
    # fixture_minimality proxy: shared module/session fixtures are a risk
    if metrics.get("shared_mutable_fixture"):
        rubric["fixture_minimality"].score = 1
        rubric["fixture_minimality"].notes = "shared mutable fixture detected"
    # diagnostic_quality proxy: sleeps / no explicit messages is weak
    if metrics.get("explicit_sleeps", 0) > 0:
        rubric["diagnostic_quality"].score = 1
        rubric["diagnostic_quality"].notes = "explicit sleep(s) detected"
    return rubric


_ANCHORED: dict[str, str] = {
    "behavior_focus": "0 = asserts internals; 2 = mixed; 4 = observable behavior only",
    "intent_readability": "0 = obscured; 2 = adequate; 4 = self-describing",
    "fixture_minimality": "0 = shared/giant; 2 = adequate; 4 = minimal/fresh per test",
    "overspecification": "0 = asserts calls/internals; 2 = some over-spec; 4 = contract only",
    "dependency_strategy": "0 = mocks SUT/mismatched double; 2 = adequate; 4 = right double, real when safe",
    "maintainability": "0 = brittle; 2 = adequate; 4 = low-cost, clear",
    "diagnostic_quality": "0 = roulette/weak; 2 = adequate messages; 4 = failure names the condition",
    "appropriate_test_boundary": "0 = wrong boundary; 2 = adequate; 4 = boundary matches the behavior under test",
}


def score_run(
    case_id: str,
    tests_dir: Path,
    condition: Literal["baseline", "skill"],
    run_meta: RunMetadata,
    defect_id: str | None = None,
) -> EvalResult:
    """Score a real agent's `tests/` dir on a case.

    - Builds a sandbox from the case (base SUT + the agent's tests in tests/).
    - Runs pytest: `passed` = all pass on the correct SUT.
    - For each seeded defect variant, re-runs and records `caught` = a test that
      passed before now fails (the defect broke an intended invariant).
    """
    case = get_case(case_id)
    sandbox = setup_case(case_id, dest=tests_dir.parent / f"_score_{case_id}_{id(tests_dir)}")
    # drop the agent's tests into the sandbox
    if (sandbox / "tests").exists():
        shutil.rmtree(sandbox / "tests")
    shutil.copytree(tests_dir, sandbox / "tests")
    # correct SUT run
    rc_good, out_good = _run_pytest(sandbox)
    passed = rc_good == 0
    p_good, f_good, rt = _parse_outcome(out_good)
    metrics: dict[str, Any] = {
        "generated_tests_pass": passed,
        "test_runtime_seconds": rt,
        "seeded_defects_caught": 0,
        "mutation_score": 0.0,
    }
    # defect detection
    caught: dict[str, bool] = {}
    for d in case.defects:
        did = d.defect_id
        try:
            sb = setup_case(case_id, defect_id=did, dest=tests_dir.parent / f"_score_{case_id}_{did}")
        except ValueError:
            continue
        if (sb / "tests").exists():
            shutil.rmtree(sb / "tests")
        shutil.copytree(tests_dir, sb / "tests")
        rc_def, _ = _run_pytest(sb)
        # caught = tests passed on correct SUT but fail with the defect
        caught[did] = (rc_good == 0 and rc_def != 0)
        shutil.rmtree(sb, ignore_errors=True)
    n_defects = len([d for d in case.defects if d.defect_id in caught])
    n_caught = sum(1 for v in caught.values() if v)
    metrics["seeded_defects_caught"] = n_caught
    metrics["mutation_score"] = (n_caught / n_defects) if n_defects else 0.0
    # randomized-order / independence (pytest-randomly is present in this env)
    try:
        rc1, o1 = _run_pytest(sandbox, "-p", "randomly", "--randomly-seed=1")
        rc2, o2 = _run_pytest(sandbox, "-p", "randomly", "--randomly-seed=2")
        metrics["randomized_order_execution"] = rc1 == 0 and rc2 == 0
        metrics["independent_execution"] = rc1 == 0 and rc2 == 0
        metrics["repeated_run_stability"] = (rc_good == 0) and (rc1 == 0)
    except Exception:
        metrics["randomized_order_execution"] = None
        metrics["independent_execution"] = None
        metrics["repeated_run_stability"] = passed
    metrics["production_files_modified"] = _count_prod_changed(run_meta.patch)
    metrics.update(_static_metrics(sandbox / "tests", "sut"))
    rubric = _rubric_proxies(metrics, case)
    shutil.rmtree(sandbox, ignore_errors=True)
    return EvalResult(
        case_id=case_id,
        condition=condition,
        run_meta=run_meta,
        metrics=metrics,
        rubric=rubric,
        passed=passed,
        defect_caught=caught,
    )


def _count_prod_changed(patch: str | None) -> int:
    if not patch or not Path(patch).is_file():
        return 0
    try:
        text = Path(patch).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    n = 0
    for line in text.splitlines():
        if line.startswith("+++ b/") or line.startswith("+++ b"):
            path = line[6:]
            if path.endswith(".py") and not path.startswith("evals/cases") and "/tests/" not in path:
                n += 1
    return n


# --------------------------------------------------------------------------- #
# Comparison + reporting                                                      #
# --------------------------------------------------------------------------- #

def compare_runs(results: list[EvalResult]) -> dict[str, Any]:
    """Aggregate baseline-vs-skill results into a comparison summary."""
    by_case: dict[str, dict[str, EvalResult]] = {}
    for r in results:
        by_case.setdefault(r.case_id, {})[r.condition] = r
    out: dict[str, Any] = {"by_case": {}, "aggregate": {}}
    win = loss = tie = 0
    caught_base = caught_skill = 0
    for cid, conds in sorted(by_case.items()):
        b = conds.get("baseline")
        s = conds.get("skill")
        row: dict[str, Any] = {"baseline": None, "skill": None, "delta_defects_caught": 0}
        if b:
            row["baseline"] = _summary(b)
            caught_base += b.metrics.get("seeded_defects_caught", 0)
        if s:
            row["skill"] = _summary(s)
            caught_skill += s.metrics.get("seeded_defects_caught", 0)
        if b and s:
            row["delta_defects_caught"] = s.metrics.get("seeded_defects_caught", 0) - b.metrics.get("seeded_defects_caught", 0)
            if s.metrics.get("seeded_defects_caught", 0) > b.metrics.get("seeded_defects_caught", 0):
                win += 1
            elif s.metrics.get("seeded_defects_caught", 0) < b.metrics.get("seeded_defects_caught", 0):
                loss += 1
            else:
                tie += 1
        out["by_case"][cid] = row
    out["aggregate"] = {
        "cases_run": len(by_case),
        "baseline_defects_caught": caught_base,
        "skill_defects_caught": caught_skill,
        "wins": win,
        "losses": loss,
        "ties": tie,
    }
    return out


def _summary(r: EvalResult) -> dict[str, Any]:
    return {
        "passed": r.passed,
        "seeded_defects_caught": r.metrics.get("seeded_defects_caught"),
        "mutation_score": r.metrics.get("mutation_score"),
        "sut_mocked": r.metrics.get("sut_mocked"),
        "explicit_sleeps": r.metrics.get("explicit_sleeps"),
        "independent_execution": r.metrics.get("independent_execution"),
    }


def build_report(results: list[EvalResult], out: Path | None = None) -> Path:
    comp = compare_runs(results)
    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "cases": len({r.case_id for r in results}),
        "comparisons": comp,
    }
    out_path = Path(out) if out else (load_settings().paths.repo_root / "evals" / "results" / "report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return out_path


# --------------------------------------------------------------------------- #
# CLI commands                                                                #
# --------------------------------------------------------------------------- #

@EVAL_APP.command()
def list_cases() -> None:
    """List all eval cases."""
    for c in CASE_CATALOG:
        typer.echo(f"{c.case_id}\t{c.title}\t({len(c.defects)} defect(s))")


@EVAL_APP.command(name="init-cases")
def init_cases_cmd(
    target: Path = typer.Option(None, help="Output dir"),
) -> None:
    """Materialize the committed case catalog to disk for inspection."""
    out = init_cases(target)
    n = len(CASE_CATALOG)
    typer.echo(f"initialized {n} cases -> {out}")


@EVAL_APP.command()
def setup(
    case_id: str = typer.Argument(..., help="Case id from `list-cases`"),
    defect: str | None = typer.Option(None, "--defect", "-d", help="Seeded defect to apply"),
    dest: Path = typer.Option(None, help="Sandbox destination"),
) -> None:
    """Materialize a single case sandbox (SUT + empty tests/ + task) for an agent to edit."""
    sandbox = setup_case(case_id, defect_id=defect, dest=dest)
    typer.echo(f"setup {case_id} (defect={_defect_or_base(defect)}) -> {sandbox}")


@EVAL_APP.command(name="score")
def score_cmd(
    case_id: str = typer.Argument(...),
    tests_dir: Path = typer.Option(..., "--tests", "-t", help="Agent-produced tests/ dir"),
    condition: str = typer.Option("skill", "--condition", help="baseline|skill"),
    agent: str = typer.Option("opencode", "--agent"),
    model: str = typer.Option(..., "--model"),
    patch: str | None = typer.Option(None, "--patch", help="Imported git diff path"),
) -> None:
    """Score a real agent's tests/ dir against a case."""
    meta = RunMetadata(
        case_id=case_id,
        condition=condition,  # type: ignore[arg-type]
        agent=agent,
        model=model,
        started_at=datetime.now(UTC),
    )
    result = score_run(case_id, tests_dir, condition, meta, defect_id=None)  # type: ignore[arg-type]
    out = load_settings().paths.repo_root / "evals" / "results" / f"{case_id}-{condition}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.model_dump(), indent=2, default=str) + "\n", encoding="utf-8")
    typer.echo(f"scored {case_id} ({condition}): pass={result.passed} caught={sum(result.defect_caught.values())} -> {out}")


@EVAL_APP.command()
def report(
    results_dir: Path = typer.Option(None, help="Dir of <case>-<condition>.json result files"),
) -> None:
    """Aggregate result files into evals/results/report.json."""
    rd = Path(results_dir) if results_dir else (load_settings().paths.repo_root / "evals" / "results")
    results: list[EvalResult] = []
    for p in sorted(rd.glob("*.json")):
        if p.name == "report.json":
            continue
        try:
            results.append(EvalResult.model_validate_json(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    rep = build_report(results, rd / "report.json")
    typer.echo(f"report -> {rep} ({len(results)} results)")


def _defect_or_base(defect: str | None) -> str:
    return defect or "base(correct)"


def run_evals(name: str | None = None) -> dict[str, Any]:
    """High-level entry used by `agentic-testcraft eval` (single arg form).

    With no real agent available, this reports readiness rather than simulating
    candidate solutions. `name` selects a single case to set up, if provided.
    """
    if name:
        setup_case(name)
        typer.echo(f"setup {name} (edit tests/ then run `eval score --tests <dir>`)")
    else:
        typer.echo(f"cases: {len(CASE_CATALOG)} | harness ready; M10a status: "
                   "evaluation infrastructure complete; real A/B execution pending")
    return {"cases": len(CASE_CATALOG), "m10a_complete": True, "m10b_pending": True}


@EVAL_APP.callback(invoke_without_command=True)
def _eval_root() -> None:
    pass
