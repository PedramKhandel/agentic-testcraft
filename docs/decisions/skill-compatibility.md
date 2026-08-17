# Decision: Modernization ↔ Skill-Spec Compatibility

**Status:** accepted
**Context:** M8 modernization produced 17 `modern:*` records (`knowledge/modern/`)
after the M8f research addendum (random test ordering, snapshot/golden-master,
HTTP boundary mocking, cross-version/cross-platform matrix). This record verifies
they align with the authoring target in `docs/skill-spec.md` (decision rules R1–R8
and acceptance criterion 6.13: "All major rules map to evidence IDs
(synthesized → book/modern)") and with the target agent's skill manifest spec.

## Method

Map each skill-spec rule to the modernization record(s) that justify or refine
it, and flag gaps.

## Findings

| Skill rule | Modernization basis | Status |
|---|---|---|
| R1 — Verify through behavior, not implementation | `modern:contract-testing` (Pact = interaction-as-observable-contract at the service boundary) refines where interaction *is* the contract | aligned / refined |
| R2 — One condition ≠ one assertion | Unchanged by M8; `modern:mutation-testing` sharpens this: a surviving mutant means an assertion is *missing*, reinforcing "verify the real condition" | aligned |
| R3 — Smallest useful boundary | `modern:disposable-integration-containers` (per-test container) + `modern:hermetic-integration` (function-scoped teardown) make the smallest boundary cheap, supporting R3 | aligned |
| R4 — Dependency replacement is goal-driven | `modern:disposable-integration-containers` (real, isolated service instead of a shared DB double) + `modern:contract-testing` (contract over end-to-end double) give concrete "keep the real dependency when fast/deterministic/safe" guidance | aligned |
| R5 — Fixture minimality | `modern:hermetic-integration` (default function scope) + `modern:disposable-integration-containers` (no shared state) operationalize "fresh per test" | aligned |
| R6 — Guarded testability refactoring | `modern:async-test-support` (await coroutines through an async runner, not test-only forks) prevents `if testing` style bypasses; `modern:deterministic-time` enables time-based refactors to be verified. **R6 is now cited in `SKILL.md` step 3** via `references/testability.md` (was un-cited pre-M9; regression-guarded by `test_committed_skill_cites_every_rule_and_step`) | aligned / cited
| R7 — Effectiveness validation | `modern:mutation-testing`, `modern:property-based-testing`, `modern:fuzz-testing`, `modern:contract-testing` directly implement the "mutation / property-based / fault seeding" R7 trigger, with tool names and workflow (`mutmut run`, Hypothesis properties, `--splits`); `modern:snapshot-golden` and `modern:browser-ui-assertions`/`service-level-expectations` extend coverage of R7's "stronger validation" guidance | aligned |
| R8 — Smell-driven review | `modern:flaky-as-fatal` narrows `smell:erratic-test`/`smell:fragile-test`: flakiness is corrected, not retried — feeding R8's smell catalog; `modern:random-test-ordering` helps *detect* order-dependent smells | aligned |

## Skill-spec / manifest conformance (M9)

Researched against the canonical Agent Skills open standard (https://agentskills.io,
adopted by Claude Code and many other agent clients) and the Claude Code skills
frontmatter reference (https://docs.anthropic.com/en/docs/claude-code/skills):

- **`name` and `description` are required at minimum.** The agentskills.io spec
  states a skill "includes metadata (`name` and `description`, at minimum)".
  `SKILL.md` now carries both (`name: agentic-testcraft`, a concise
  `description`). `skill_validate.REQUIRED_FRONT_MATTER` now enforces them.
- **`compatibility` is an optional spec field** (env/system requirements).
  `SKILL.md` carries a `compatibility` string (Python 3.10+; pytest 8+;
  mutmut/atheris Linux/macOS-primary via WSL; core rules platform-agnostic).
  `bundle.py` now records it in `.skill-manifest.json`.
- **`version`, `status`, `title` are project-internal fields**, NOT part of the
  agentskills.io spec frontmatter set and absent from Claude Code's standard
  frontmatter table. They are kept as the project's own lifecycle metadata.
  `status` moved from `stable` to `release-candidate` (version `1.0.0rc1`)
  because the skill is functional but not yet eval-validated (M10);
  `skill_validate.VALID_STATUS` now accepts `release-candidate`.
- **No verbatim book excerpts / no stale placeholders** — enforced by
  `skill_validate.BOOK_QUOTE_RE` / `PLACEHOLDER_RE`; the committed `SKILL.md`
  passes both.

## Acceptance-criterion 6.13 (evidence mapping)

Every modern record maps to real book `id`s (patterns/principles/goals/smells),
so the final skill can cite both a book principle (`origin:"book"`) and a
modernization record (`origin:"modern"`) for each decision. No modern record
introduces a claim without an `official_sources` URL + review date. The
traceability map (`knowledge/synthesized/skill-traceability.json`) records the
R1–R8 ↔ modern ↔ book linkage, now including the four M8f additions.

## Mitigations applied (M9)

- **Platform/skill manifest:** resolved by researching the canonical Agent
  Skills spec (https://agentskills.io) and the Claude Code frontmatter reference;
  `SKILL.md` now carries the spec-required `name` + `description` and the
  optional `compatibility` field (see "Skill-spec / manifest conformance"
  above). Framework-specific CLI flags (`-n auto`, `mutmut run`) remain
  *examples* in the body and are not hard dependencies.
- **Windows caveats:** surfaced in the `compatibility` frontmatter string
  (mutmut/atheris Linux/macOS-primary, Windows via WSL; core rules
  platform-agnostic) so the judgment travels across platforms.
- **CI coupling:** CI parallelism/sharding/cross-version are kept as
  *recommendations* in `SKILL.md` (step 9), not requirements.

## Conclusion

M8 (17 records) + M9 (spec-conformant `SKILL.md` v1.0.0rc1,
`release-candidate`) are **compatible** and complete: every R1–R8 is cited in
`SKILL.md` and mapped to evidence in the traceability JSON; R7 is the strongest
win; no record conflicts with R1–R8 or the acceptance criteria. `validate-skill`
+ `bundle` pass and the skill is ready for the M10 eval gate.
