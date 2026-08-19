"""M10b orchestrator: a real, same-agent/same-model OpenCode A/B on the committed
CASE_CATALOG.

A/B design (contamination-free, single variable = the agentic-testcraft skill):
  - baseline: `opencode run '<task>' --model <M> --dir <sandbox> --auto`  (default agent,
    NO agentic-testcraft guidance)
  - treatment (skill): same command + `--agent agentic-testcraft`, which loads the rc1
    agent profile (`~/.config/opencode/agents/agentic-testcraft.md`) whose instructions
    carry the rc1 SKILL.md guidance. The task prompt is the committed `case.task`,
    identical in both conditions.

Flow per (case, condition):
  1. setup_case(case_id, dest=<sandbox>)  -> SUT + task.md + conftest.py + empty tests/
  2. opencode run <case.task> --model M --dir <sandbox> --auto --print-logs --log-level DEBUG [--agent agentic-testcraft]
  3. stage: move any agent-written test_*.py from <sandbox>/ into <sandbox>/tests/
  4. score_run(...) -> evals/results/<case>-<condition>.json  (deterministic: pass,
     seeded_defects_caught, mutation_score, static smell scorers, randomized-order)

Run:  PYTHONPATH=src .venv/Scripts/python -m evals.m10b_run   (or: .venv/Scripts/python evals/m10b_run.py)
Results: evals/results/<case>-<baseline|skill>.json + .opencode.log per run.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from agentic_testcraft.evals import EvalCase

ROOT = Path(__file__).resolve().parents[1]  # repo root (evals/ -> repo root)
SRC = ROOT / "src"
SANDBOX_ROOT = ROOT / "evals" / "_sandbox"
RESULTS = ROOT / "evals" / "results"
MODEL = "openrouter/poolside/laguna-s-2.1:free"
AGENT = "agentic-testcraft"

# M10b Phase-1 smoke: 4 representative cases (logic / double-misuse / design / interaction).
SMOKE = ["pure-function", "over-mocking-trap", "clock-dependency", "interaction-is-requirement"]

# (label, include --agent agentic-testcraft?)
CONDITIONS: list[tuple[Literal["baseline", "skill"], bool]] = [("baseline", False), ("skill", True)]


def _which_opencode() -> str:
    for cand in ("opencode", "opencode.cmd", "opencnen", "opencnnen"):
        path = shutil.which(cand)
        if path:
            return path
    raise SystemExit("opencnen executable not found on PATH")


def stage_tests(sandbox: Path) -> Path:
    """Move agent-written test_*.py from sandbox root into sandbox/tests/ (harness expects tests/)."""
    tests = sandbox / "tests"
    tests.mkdir(exist_ok=True)
    for p in sorted(sandbox.glob("test_*.py")) + sorted(sandbox.glob("*_test.py")):
        shutil.move(str(p), str(tests / p.name))
    # also sweep any test files the agent may have placed in nested dirs
    return tests


def run_opencode(
    case: EvalCase, condition: Literal["baseline", "skill"], use_agent: bool, sandbox: Path
) -> tuple[int, str]:
    """Headless opencnen run; returns (returncode, log_path)."""
    cmd = [
        _which_opencode(),
        "run",
        case.task,
        "--model",
        MODEL,
        "--dir",
        str(sandbox),
        "--auto",
        "--print-logs",
        "--log-level",
        "DEBUG",
    ]
    if use_agent:
        cmd += ["--agent", AGENT]
    log_path = RESULTS / f"{case.case_id}-{condition}.opencode.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600
        )
    except subprocess.TimeoutExpired as e:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                "\n[TIMEOUT after 600s — likely rate-limited by the free model; partial output below]\n"
            )
            for stream in (e.stdout, e.stderr):
                if stream:
                    f.write(
                        stream.decode("utf-8", errors="replace")
                        if isinstance(stream, bytes)
                        else stream
                    )
        return 124, str(log_path)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(proc.stdout or "")
        f.write(proc.stderr or "")
    return proc.returncode, str(log_path)


def main() -> None:
    sys.path.insert(0, str(SRC))
    from agentic_testcraft.evals import (  # noqa: E402
        RunMetadata,
        case_ids,
        get_case,
        score_run,
        setup_case,
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
    OC = _which_opencode()
    phase = os.environ.get("M10B_PHASE", "all")
    CASE_IDS = SMOKE if phase == "smoke" else case_ids()
    print(f"M10b orchestrator — opencnen={OC} model={MODEL} agent={AGENT}")
    print(f"phase={phase} cases={len(CASE_IDS)} conditions=baseline(no --agent) vs skill(--agent {AGENT})")

    rows: list[tuple[str, str, str, bool, float, float, float]] = []
    for case_id in CASE_IDS:
        case = get_case(case_id)
        print(f"\n=== {case_id}: {case.title} ===")
        for condition, use_agent in CONDITIONS:
            sb_name = f"{case_id}-{condition}"
            sandbox = SANDBOX_ROOT / sb_name
            if sandbox.exists():
                shutil.rmtree(sandbox, ignore_errors=True)
            setup_case(case_id, dest=sandbox)
            t0 = time.time()
            rc, log = run_opencode(case, condition, use_agent, sandbox)
            wall = round(time.time() - t0, 1)
            tests_dir = stage_tests(sandbox)
            meta = RunMetadata(
                case_id=case.case_id,
                condition=condition,
                agent="opencnen",
                model=MODEL,
                started_at=datetime.now(UTC),
            )
            res = score_run(case.case_id, tests_dir, condition, meta, defect_id=None)
            (RESULTS / f"{case.case_id}-{condition}.json").write_text(
                json.dumps(res.model_dump(), indent=2, default=str), encoding="utf-8"
            )
            m = res.metrics
            line = (
                f"  {condition:8s} | opencnen_rc={rc} wall={wall}s | "
                f"pass={res.passed} caught={sum(res.defect_caught.values())}/"
                f"{len(res.defect_caught)} mut={m.get('mutation_score')} "
                f"smells[sleeps={m.get('explicit_sleeps')},sut_mocked={m.get('sut_mocked')},"
                f"shared={m.get('shared_mutable_fixture')},inter={m.get('unnecessary_interaction_assertions')},"
                f"deps={m.get('unnecessary_dependencies_introduced')}]"
            )
            print(line)
            rows.append(
                (
                    case_id,
                    condition,
                    str(tests_dir),
                    res.passed,
                    float(sum(res.defect_caught.values())),
                    float(m.get("mutation_score") or 0),
                    wall,
                )
            )

    # aggregate the committed result JSONs into evals/results/report.json
    env = dict(os.environ, PYTHONPATH=str(SRC))
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys;from agentic_testcraft.cli import app;sys.argv=['atc','eval','report'];app()",
        ],
        cwd=str(ROOT),
        env=env,
        timeout=120,
        capture_output=True,
        text=True,
        check=False,
    )
    print("\n=== summary ===")
    print(f"{'case':24s}{'cond':10s}{'pass':6s}{'caught':8s}{'mut':6s}{'wall_s':7s}")
    for cid, cond, _td, passed, caught, mut, wall in rows:
        print(f"{cid:24s}{cond:10s}{str(passed):6s}{caught:<8.0f}{mut:<6.1f}{wall:<7.1f}")
    print("\nreport -> evals/results/report.json  (also includes prior pure-function results)")


if __name__ == "__main__":
    main()
