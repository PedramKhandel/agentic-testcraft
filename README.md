# Agentic Testcraft

**Agentic Testcraft** is an evidence-backed Agent Skill for designing, writing,
reviewing, refactoring, and validating maintainable automated tests. It helps a
coding agent make better testing decisions across languages and frameworks; it
does not teach the syntax of a particular test framework.

The project is currently a **release candidate** (`1.0.0rc1`). Its portable
skill is in [`skill/agentic-testcraft/`](skill/agentic-testcraft/), with a
deterministic pipeline that derives and validates the supporting guidance.

## What the skill emphasizes

- Observable behavior rather than incidental implementation details.
- The smallest test boundary that faithfully verifies a requirement.
- Minimal, fresh fixtures and intentional dependency choices.
- Appropriate use of real dependencies, fakes, stubs, spies, mocks, and
  dummies—not automatic mocking.
- Test independence, readability, deterministic execution, and smell review.
- Effectiveness checks such as seeded defects, mutation testing, or
  property-based testing when risk justifies them.

The skill is judgment-first and framework-independent. It is designed to be
loaded as an agent instruction, not imported as a runtime Python library.

## Quick start

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/pedram-ahmadi/agentic-testcraft.git
cd agentic-testcraft
uv sync --extra dev

# Inspect the available pipeline and evaluation commands.
uv run agentic-testcraft --help

# Verify the distributable skill and run the repository test suite.
uv run agentic-testcraft validate-skill
uv run pytest
```

To use the guidance with a compatible coding agent, load
[`skill/agentic-testcraft/SKILL.md`](skill/agentic-testcraft/SKILL.md) as that
agent's skill/instruction file. The detailed reference files are intentionally
loaded on demand from `skill/agentic-testcraft/references/`.

## Build the knowledge pipeline

The root source inputs are deliberately immutable. The commands below create
reproducible local working and knowledge artifacts; those intermediate files are
ignored by Git and can be regenerated.

```bash
uv run agentic-testcraft inspect-sources
uv run agentic-testcraft clean
uv run agentic-testcraft split
uv run agentic-testcraft validate-knowledge
uv run agentic-testcraft extract
uv run agentic-testcraft build-graph
uv run agentic-testcraft synthesize
uv run agentic-testcraft modernize
uv run agentic-testcraft validate-knowledge
uv run agentic-testcraft bundle
```

The default extraction provider is `native-agent`, which is deterministic and
does not require external credentials. See [`.env.example`](.env.example) for
the environment variables used when selecting a provider or model. Never commit
credentials.

## Evaluate the skill

The evaluation harness contains 26 small test-design cases with seeded defects.
It scores tests produced by a real agent in a baseline condition and a
skill-enabled condition.

```bash
uv run agentic-testcraft eval list-cases
uv run agentic-testcraft eval init-cases --target evals/cases
uv run agentic-testcraft eval setup pure-function --dest evals/sandbox
```

The complete same-model OpenCode A/B protocol, including its prerequisites and
scoring caveats, is in the [M10b runbook](docs/evaluation-methodology-m10b-runbook.md).
It invokes an external model and can take substantial time. The committed
`evals/_phase2.log` is an **incomplete operational log**, not a published
benchmark or evidence of comparative improvement.

## Repository map

| Path | Purpose |
| --- | --- |
| [`skill/`](skill/) | The release-candidate Agent Skill and its progressive-disclosure references. |
| [`src/agentic_testcraft/`](src/agentic_testcraft/) | Deterministic pipeline, CLI, validation, and evaluation harness. |
| [`schemas/`](schemas/) | JSON Schemas for provenance-linked knowledge artifacts. |
| [`docs/`](docs/) | Architecture, methodology, evaluation protocol, and recorded decisions. |
| [`tests/`](tests/) | Unit tests for pipeline stages and validation gates. |
| [`evals/`](evals/) | A/B orchestration and transient evaluation output locations. |

## Documentation

- [Architecture](docs/architecture.md) — components, stages, artifact lifecycle,
  and data flow.
- [Skill specification](docs/skill-spec.md) — intended agent behaviors and
  acceptance criteria.
- [Source-handling methodology](docs/source-methodology.md) — deterministic
  transformation and provenance rules.
- [Modernization methodology](docs/modernization-methodology.md) — how current
  primary sources refine the historical evidence base.
- [Evaluation methodology](docs/evaluation-methodology.md) and the
  [M10b runbook](docs/evaluation-methodology-m10b-runbook.md) — scoring model,
  limitations, and operational A/B procedure.
- [Contributing guide](CONTRIBUTING.md) — local development and contribution
  boundaries.

## License and source-material notice

The repository's code and authored, transformed artifacts are licensed under
the [MIT License](LICENSE). The root PDF and Markdown copies of *xUnit Test
Patterns: Refactoring Test Code* are copyrighted source material and are **not**
licensed under MIT. They are included here only under the repository owner's
stated authorization and remain immutable inputs; see [NOTICE.md](NOTICE.md) and
the [source-publication decision](docs/decisions/source-publication.md).

