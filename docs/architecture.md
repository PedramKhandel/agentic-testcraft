# Architecture

`agentic_testcraft` turns provenance-linked testing knowledge into a portable,
decision-oriented Agent Skill. The Python package is both a deterministic build
pipeline and an evaluation harness; the distributable output is the skill under
`skill/agentic-testcraft/`.

## Component boundaries

| Component | Responsibility | Versioned output |
| --- | --- | --- |
| Source inspection and cleaning | Discover immutable source inputs, hash them, clean conversion artifacts, and preserve line provenance. | Source inputs and code; generated working files stay local. |
| Structure and extraction | Split the cleaned source by semantic headings and produce schema-constrained, provenance-linked records. | Code and schemas; generated JSONL stays local. |
| Graph, synthesis, and modernization | Relate records, derive operational rules, and add current guidance from official sources. | Code, methodology, and the committed skill traceability map. |
| Skill packaging | Validate `SKILL.md` and references, then emit a content-hash manifest. | `skill/agentic-testcraft/`, including `.skill-manifest.json`. |
| Evaluation | Materialize cases, score real agent-produced tests against seeded defects, and aggregate results. | Case definitions in code and the optional orchestrator; run outputs stay local. |

## Stages and CLI surface

| Stage | Command | Module | Primary generated artifact |
| --- | --- | --- | --- |
| M0 | — | `config`, `provenance`, `schemas`, `cli` | Shared configuration and validators. |
| M2 | `inspect-sources`, `clean` | `source_inspect`, `clean` | `.local/work/source-report.json`, cleaned text, line map. |
| M3 | `split` | `structure`, `chunk` | `.local/work/chunk-manifest.jsonl`, `structure.json`. |
| M4 | `validate-knowledge` | `schemas` | Validation report; no new canonical artifact. |
| M5 | `extract` | `extract` | `knowledge/book/*.jsonl`. |
| M6 | `build-graph` | `graph` | `knowledge/graph/relationships.jsonl`, `graph.json`. |
| M7 | `synthesize` | `synthesize` | `knowledge/synthesized/decision-rules.jsonl`. |
| M8 | `modernize` | `modernize` | `knowledge/modern/modernization.jsonl` and a digest. |
| M9 | `validate-skill`, `bundle` | `skill_validate`, `bundle` | Validated skill and `.skill-manifest.json`. |
| M10a | `eval` subcommands | `evals` | Case sandboxes, per-run scores, and aggregate report. |
| M10b | `evals/m10b_run.py` | External OpenCode orchestration | Optional real-agent A/B run data. |

## Data flow and artifact lifecycle

```text
immutable source inputs
        |
        v
 .local/work/  (clean text, provenance maps, chunk manifest)
        |
        v
 knowledge/book/ --> knowledge/graph/ --> knowledge/synthesized/
        |                                            |
        +-----------------> knowledge/modern/ -------+
                                                     v
                                      skill/agentic-testcraft/
                                      (SKILL.md, references, manifest)

real agent + eval case --> evals/_sandbox/ --> evals/results/report.json
```

`.local/`, generated `knowledge/*` JSONL/digests, `evals/_sandbox/`, and
`evals/results/` are ignored because they are rebuildable or run-specific. The
checked-in `knowledge/synthesized/skill-traceability.json` is the compact
evidence map referenced by the release-candidate skill. The checked-in
`evals/_phase2.log` is a single incomplete audit log; it is not an evaluation
result or a template for committing future run output.

## Invariants

1. **Provenance is preserved.** Source-derived records retain source hashes and
   line ranges, allowing a claim to be traced to its immutable input.
2. **Stages are deterministic.** The default extractor (`native-agent`) and
   all transformations use deterministic, schema-validated code.
3. **Generated records are validated.** Pydantic models validate on write, and
   `validate-knowledge` validates written artifacts and cross-record references.
4. **The skill is independently validated.** `validate-skill` checks required
   front matter, structure, references, and source-leak guardrails; `bundle`
   creates the content manifest only after that gate passes.
5. **Evaluation does not fabricate results.** The harness only scores tests
   created by an actual agent or human. A score report is meaningful only when
   its complete inputs and execution conditions are available.

## Key identifiers

- Knowledge IDs use prefixes such as `pattern:`, `smell:`, `goal:`,
  `principle:`, `modern:`, and `decision-rule:`.
- Relationship edges use `refactors_to`, `prevents`, `may_cause`, `used_with`,
  and `supports`.
- Evaluation case IDs are defined by `CASE_CATALOG` in
  `src/agentic_testcraft/evals.py`; `eval list-cases` prints the authoritative
  catalog.

For the assumptions and audit trail behind this design, read the
[source-handling methodology](source-methodology.md),
[modernization methodology](modernization-methodology.md), and
[build progress report](build-report.md).
