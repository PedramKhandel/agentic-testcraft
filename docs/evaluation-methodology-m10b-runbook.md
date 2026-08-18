# M10b Runbook — A/B Evaluation Protocol Supplement

Complements `docs/evaluation-methodology.md` with the **operational** protocol used to
execute M10b: a real, same-agent/same-model OpenCode A/B against the committed
`CASE_CATALOG` (see `src/agentic_testcraft/evals.py`). M10a (the harness + rc1) is the
frozen candidate; M10b is the execution that M10a was built for.

## The single A/B variable

The skill `agentic-testcraft` is exposed to the child agent via an **OpenCode local
agent profile**, not by editing the task prompt:

- Profile: `~/.config/opencode/agents/agentic-testcraft.md` — a copy of the rc1
  `skill/agentic-testcraft/SKILL.md` with OpenCode agent front-matter
  (`name`, `model: openrouter/poolside/laguna-s-2.1:free`, `tools: [bash,read,edit,glob,grep,webfetch]`)
  and the SKILL.md body as the agent's instructions.
- Treatment: `opencode run '<case.task>' --model <M> --dir <sandbox> --auto --agent agentic-testcraft`
- Baseline:  `opencode run '<case.task>' --model <M> --dir <sandbox> --auto`   (no `--agent`)

Both conditions receive the **identical** `case.task` prompt and the same model
(`openrouter/poolside/laguna-s-2.1:free`). The OpenCode orca skill set is common to
both and cancels; the rc1 agentic-testcraft guidance is the only difference.

### Exposure validation (contamination control)
- opencnen startup log of a treatment run shows `agent=agentic-testcraft` and a
  `> agentic-testcraft · poolside/laguna-s-2.1:free` header (captured with
  `--print-logs --log-level DEBUG`).
- The baseline run's log contains **no** such line → the skill is absent in baseline.
- OpenRouter is configured in opencnen's credential store
  (`~/.local/share/opencode/auth.json`); `OPENROUTER_API_KEY` need not be in the
  environment; the free tier is rate-limited and opencmen retries mid-run.

## Orchestrator

`evals/m10b_run.py` drives the whole loop for a list of cases × conditions:

1. `setup_case(case_id, dest=<sandbox>)` — materializes `sut.py` + `task.md` +
   `conftest.py` + empty `tests/` into `evals/_sandbox/<case>-<condition>/`.
2. `opencode run <case.task> --model ... --dir <sandbox> --auto --print-logs --log-level DEBUG [--agent agentic-testcraft]`.
3. `stage_tests` — moves agent-written `test_*.py` from the sandbox root into
   `sandbox/tests/`. **This step is required**: opencnen writes tests at the sandbox
   root by default, but `score_run` expects them under `tests/`. Without staging, the
   copied `sut.py` shadows the seeded-defect `sut.py` and defect detection silently
   reports `caught=0`.
4. `score_run(...)` — runs pytest on the correct SUT and each seeded defect variant,
   computes deterministic metrics (pass, `seeded_defects_caught`, `mutation_score`,
   randomized-order/independence/stability, and AST static smell scorers) and
   persists `evals/results/<case>-<baseline|skill>.json`.
5. `eval report` aggregates all result JSONs into `evals/results/report.json`.

## Scoring invocation gotcha

`opencode eval score <case> --tests <dir>` **must** receive an **absolute** `--tests`
path. A relative path makes `score_run` build a relative sandbox; `_run_pytest` then
passes that same relative path both as `cwd` and as the pytest path argument, so
pytest resolves the path against its own (already-relative) cwd and reports
`ERROR: file or directory not found` (rc=4) → `pass=False`, `runtime=0.0`. Always pass
an absolute directory.

## Reproducing

```bash
# run a full smoke A/B (opencnen calls the model; results land in evals/results/)
PYTHONPATH=src .venv/Scripts/python evals/m10b_run.py

# re-aggregate (no model cost)
PYTHONPATH=src .venv/Scripts/python -c "from agentic_testcraft.cli import app; import sys; sys.argv=['atc','eval','report']; app()"
```

Generated sandboxes (`evals/_sandbox/`), per-run logs, and result JSONs
(`evals/results/`) are all gitignored — they are transient evaluation artifacts and
are **not** committed. Only the orchestrator and this runbook are committed.

## Interpreting results

For a single seeded defect per case, every compliant test set catches the defect
(`caught=1`, `mutation_score=1.0`), so defect-caught is a floor, not a differentiator.
The skill's value is evaluated on the **static smell / design metrics** and **qualitative**
test structure (parametrization, intention-revealing names, stubs vs. mocks, absence of
the over-mocking trap, interaction-is-the-requirement adherence). Example from smoke:
`clock-dependency` drops `unnecessary_dependencies_introduced` baseline→skill (1→0);
`over-mocking-trap` (skill) emits a guarded test that asserts the SUT is not a Mock —
which trips the harness's `sut_mocked` heuristic (a known false positive when `Mock` is
imported only to assert non-mocking).
