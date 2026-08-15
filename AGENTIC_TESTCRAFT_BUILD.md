# Agentic Testcraft — Master Build Plan

> **Repository/skill name:** `agentic-testcraft`
>
> **Mission:** Build a production-quality, framework-aware but framework-independent Agent Skill that makes coding agents substantially better at **designing, writing, reviewing, refactoring, and validating maintainable automated tests**. The primary conceptual source is Gerard Meszaros' *xUnit Test Patterns: Refactoring Test Code* (2007), but the final skill must not be a book summary. It must transform the source into compact, operational decision rules for modern coding agents, then carefully modernize those rules using current primary/official sources and validate the result with reproducible evaluations.

---

## 0. Instructions to the implementation agent

You are the implementation agent for this repository. **Execute this plan end-to-end; do not merely restate it.**

Read this entire file before making changes.

You are expected to:

1. inspect the repository and source files;
2. bootstrap the project structure and tooling;
3. implement deterministic preprocessing tools;
4. extract structured knowledge from the book with traceable provenance;
5. synthesize that knowledge into agent-operational decision rules;
6. modernize it using current primary/official sources;
7. build the final Agent Skill using progressive disclosure;
8. create and run a meaningful evaluation suite;
9. iteratively improve the skill based on measured failures;
10. leave the repository reproducible, documented, tested, and clean.

### Autonomy

Make routine engineering decisions yourself. Do not ask for permission for normal choices such as module names, exact internal file layouts, test helper names, refactorings, or commit timing.

Only stop for a genuinely blocking condition such as:

- the required source files are missing or unreadable;
- a required external credential is unavailable and there is no safe local/native fallback;
- a destructive operation would overwrite source data;
- a licensing/rights decision requires an explicit owner choice.

When a preferred tool is unavailable, choose a reasonable alternative and document the substitution.

### Quality bar

This is intended to become a **super-skill**, not a thin prompt wrapper.

Optimize for:

- correctness;
- source fidelity;
- traceability;
- maintainability;
- deterministic tooling;
- minimal hallucination;
- modern applicability;
- progressive context loading;
- cross-language usefulness;
- measurable improvement in coding-agent test quality.

Do not optimize for speed at the expense of correctness.

### Important distinction

The final skill is **not** intended to teach an agent the syntax of `pytest`, JUnit, Vitest, xUnit.net, etc. Modern coding agents already know common test syntax.

The final skill should improve the agent's **judgment** about:

- what behavior deserves a test;
- what test boundary or level to use;
- direct/state vs indirect/behavior verification;
- fixture design;
- dependency isolation;
- when to use a real dependency, fake, stub, spy, or mock;
- avoiding over-mocking and implementation-detail tests;
- deterministic and independent tests;
- test smells;
- readability and intent;
- testability-oriented production refactoring;
- database/external-resource testing;
- failure diagnosis;
- test maintenance;
- how to validate that generated tests are actually effective.

---

# 1. Source handling and copyright safety

The repository root will initially contain:

- the original book PDF;
- a Markdown conversion of the book;
- this build-plan Markdown file.

Discover the actual filenames rather than hard-coding guessed names.

## 1.1 Do not modify source files

Treat the PDF and source Markdown as immutable inputs.

Before processing them:

- compute SHA-256 hashes;
- record filenames, sizes, hashes, and discovery timestamp in a local/source manifest;
- never overwrite either source file.

## 1.2 Public-repository safety

The source book is copyrighted. Unless the repository owner has explicitly documented redistribution rights:

- **do not commit the full PDF;**
- **do not commit the full converted Markdown;**
- do not commit long verbatim extracts from the book;
- do not reconstruct the book in the repository through chunk files;
- do not put substantial source passages in fixtures, logs, prompts, snapshots, or generated artifacts.

The source files may exist locally in the working tree so the agent can process them, but they should be ignored by Git by default.

Add the discovered source filenames to `.gitignore` without deleting them.

Committed knowledge artifacts should be:

- structured;
- concise;
- paraphrased;
- transformative;
- traceable to source ranges by line/page metadata;
- not a substitute for the original book.

If source excerpts are temporarily needed during processing, place them under a gitignored local-work directory.

## 1.3 Provenance requirement

Every source-derived principle, smell, pattern, rule, tradeoff, or relationship must retain provenance pointing back to the original source.

Prefer:

```yaml
source:
  file_sha256: "..."
  markdown_start_line: 1234
  markdown_end_line: 1278
  pdf_page_start: 123
  pdf_page_end: 125
```

PDF pages may be null when reliable mapping is unavailable, but Markdown line provenance is mandatory for book-derived knowledge.

---

# 2. Repository bootstrap — Phase 0

Perform this before Stage 1.

## 2.1 Recommended initial repository structure

Create a clean structure similar to this. Minor improvements are allowed if documented.

```text
agentic-testcraft/
├── AGENTIC_TESTCRAFT_BUILD.md
├── README.md
├── CONTRIBUTING.md
├── NOTICE.md
├── .gitignore
├── .editorconfig
├── .env.example
├── pyproject.toml
│
├── src/
│   └── agentic_testcraft/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── provenance.py
│       ├── source_inspect.py
│       ├── clean.py
│       ├── structure.py
│       ├── chunk.py
│       ├── schemas.py
│       ├── extract.py
│       ├── graph.py
│       ├── synthesize.py
│       ├── modernize.py
│       ├── skill_validate.py
│       └── evals.py
│
├── schemas/
│   ├── goal.schema.json
│   ├── principle.schema.json
│   ├── smell.schema.json
│   ├── pattern.schema.json
│   ├── decision-rule.schema.json
│   ├── relationship.schema.json
│   └── modernization.schema.json
│
├── knowledge/
│   ├── book/
│   ├── modern/
│   ├── synthesized/
│   └── graph/
│
├── skill/
│   └── agentic-testcraft/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       └── assets/
│
├── evals/
│   ├── README.md
│   ├── cases/
│   ├── rubrics/
│   ├── baselines/
│   ├── results/
│   └── harness/
│
├── scripts/
│   ├── inspect_sources.py
│   ├── clean_book.py
│   ├── split_book.py
│   ├── extract_knowledge.py
│   ├── build_graph.py
│   ├── synthesize_rules.py
│   ├── validate_knowledge.py
│   ├── validate_skill.py
│   └── run_evals.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/
│   ├── architecture.md
│   ├── source-methodology.md
│   ├── modernization-methodology.md
│   ├── evaluation-methodology.md
│   └── decisions/
│
└── .local/                 # gitignored
    ├── source/
    ├── work/
    ├── chunks/
    ├── extraction/
    ├── renders/
    └── logs/
```

Do not create empty directories just to satisfy the diagram; use `.gitkeep` only where it has a real purpose.

## 2.2 Python environment

Use Python 3.12+ when available.

Prefer `uv` for environment and dependency management. If unavailable, use a standard virtual environment plus `pip`.

Recommended deterministic dependencies:

- `pydantic`
- `typer`
- `rich`
- `pytest`
- `jsonschema`
- `PyYAML`
- `networkx`
- `markdown-it-py`
- `pymupdf`
- `rapidfuzz` only where carefully justified
- `tenacity` for external API retry logic
- `httpx` if an HTTP client is required
- provider SDK(s) only when actually needed

Optional:

- `tiktoken` or another tokenizer for approximate token accounting;
- `ruff` for linting/formatting;
- `mypy` or `pyright` for type checking.

Do not add dependencies merely because they might be useful.

## 2.3 CLI

Expose reproducible commands through a CLI, for example:

```bash
agentic-testcraft inspect-sources
agentic-testcraft clean
agentic-testcraft split
agentic-testcraft validate-knowledge
agentic-testcraft extract
agentic-testcraft build-graph
agentic-testcraft synthesize
agentic-testcraft modernize
agentic-testcraft validate-skill
agentic-testcraft eval
```

Thin wrapper scripts under `scripts/` may call the package CLI.

All commands should:

- provide useful `--help`;
- fail with non-zero exit status on real errors;
- be rerunnable;
- avoid silently overwriting unrelated data;
- log enough metadata for reproducibility.

## 2.4 Configuration

Use a checked-in configuration file if needed, e.g.:

```text
agentic-testcraft.yaml
```

Keep secrets in environment variables only.

Never commit:

- API keys;
- tokens;
- credentials;
- private endpoints;
- local absolute paths.

Provide `.env.example` with variable names but no secrets.

## 2.5 CI

Add a lightweight CI workflow if appropriate for the public repository.

At minimum CI should run:

- unit tests;
- schema validation;
- linting/format checks;
- static validation of the final skill.

CI must not require the copyrighted source book or private API credentials for the basic checks.

---

# 3. Git and commit policy

You have autonomy over commit timing.

Create commits whenever a coherent unit of work is complete and validated. Reasonable checkpoints include:

- repository bootstrap;
- deterministic source-inspection and cleanup tooling;
- semantic splitting;
- schemas and validators;
- first complete source extraction;
- relationship graph;
- synthesis;
- modernization layer;
- first production skill;
- evaluation harness;
- hardening/release candidate.

More granular commits are welcome when they improve reviewability.

## Commit messages

Use clear English commit titles and descriptions.

Prefer a conventional style such as:

```text
feat: add provenance-preserving book cleaner

Implement deterministic Markdown normalization while retaining
source line mappings and audit logs. Add regression tests for
watermark removal, OCR spacing fixes, and code-block preservation.
```

or:

```text
eval: add over-mocking and flaky-test scenarios

Add representative agent tasks that distinguish state verification
from interaction verification and measure unnecessary mock coupling.
```

Before committing:

1. review `git diff`;
2. ensure no source book or secrets are staged;
3. run relevant tests/validators;
4. commit only a coherent change.

Never commit generated temporary LLM logs that contain substantial verbatim source text.

---

# 4. Global engineering rules

These apply to all ten stages.

## 4.1 Deterministic first

If a task can be done reliably with deterministic code, do it with Python rather than an LLM.

Examples:

- hashing;
- file discovery;
- line numbering;
- Markdown heading parsing;
- page count;
- schema validation;
- reference integrity;
- duplicate detection;
- graph validation;
- JSONL formatting;
- file generation;
- regression checks.

Use LLMs for semantic judgment, not for basic text plumbing.

## 4.2 Never silently mix source knowledge and modern knowledge

All knowledge must carry an origin classification:

```text
book
modern_official
modern_research
inference
project_convention
```

Prefer `modern_official` over `modern_research` wherever possible.

A book-derived rule must not be silently rewritten as a modern rule.

A modern addition must not be falsely attributed to the book.

## 4.3 No unsupported source claims

During source extraction:

- use only information actually supported by the supplied book content;
- do not "correct" the author;
- do not add modern practices;
- do not reconcile disagreements using outside knowledge;
- mark uncertainty explicitly.

Modernization happens later, in Stage 8.

## 4.4 Preserve nuance

Avoid converting nuanced guidance into unconditional slogans.

Bad:

```text
Always use mocks for dependencies.
```

Good:

```text
Prefer direct/state verification through the public interface when it
adequately expresses the requirement. Use interaction verification when
the interaction itself is part of the observable contract or direct state
cannot adequately verify the requirement.
```

## 4.5 Avoid false precision

Do not turn examples, historical limitations, or context-dependent heuristics into universal rules.

Record strength explicitly when useful:

```text
default
preference
warning
exception
context_dependent
historical
```

## 4.6 Reproducibility

For every LLM-produced artifact, record at minimum:

- provider;
- exact model ID;
- execution date;
- prompt template version;
- source chunk IDs;
- schema version;
- generation parameters where applicable;
- validation result.

Do not record secret credentials.

---

# 5. Stage 1 — Define the target behavior of the skill

## Goal

Define exactly what the final skill should improve in a coding agent.

Do this before extracting knowledge so the pipeline does not devolve into a generic book summarizer.

## Tools

- Markdown;
- Git;
- no LLM required for the initial specification;
- optionally use the agent's own reasoning to critique the specification.

## Tasks

Create:

```text
docs/skill-spec.md
```

It must define:

### Primary use cases

At minimum:

- write tests for new or existing code;
- add missing tests around a change;
- review existing tests;
- refactor fragile or obscure tests;
- diagnose flaky/erratic tests;
- choose a test boundary;
- choose verification strategy;
- choose fixture strategy;
- choose dependency/test-double strategy;
- identify hard-to-test production design;
- perform small behavior-preserving refactorings for testability when justified;
- validate generated tests beyond "they pass."

### Non-goals

At minimum:

- teaching basic test-framework syntax;
- maximizing coverage percentage blindly;
- forcing every project into one testing philosophy;
- replacing project conventions without reason;
- mocking every dependency;
- producing tests that merely mirror implementation details;
- treating the 2007 source as complete modern testing doctrine.

### Desired behavioral outcomes

The skill should push an agent toward tests that are:

- behavior-focused;
- self-checking;
- deterministic;
- independent;
- readable;
- intention-revealing;
- minimal in setup;
- appropriately isolated;
- resistant to irrelevant refactors;
- diagnostically useful;
- reasonably fast;
- easy to maintain;
- consistent with the host repository's conventions.

### Decision points the skill must handle

At minimum:

1. What is the SUT/test boundary?
2. Which behavior or requirement is being verified?
3. What are the important test conditions?
4. Unit/component/integration/contract/system/browser test?
5. Direct/state verification or indirect/behavior verification?
6. Minimal/fresh/shared/persistent fixture?
7. Real dependency, fake, stub, spy, mock, or no double?
8. Is the dependency slow, nondeterministic, unavailable, dangerous, or part of the behavior under test?
9. Is production code hard to test because of design?
10. Is a test smell present?
11. What should run first?
12. What broader validation should run before completion?
13. Does the test detect plausible faults, not merely execute lines?

## Deliverables

- `docs/skill-spec.md`
- initial acceptance criteria for the final skill
- initial vocabulary/glossary mapping for terms such as SUT, DOC, fixture, direct output, indirect input, indirect output, test double

## Acceptance gate

Do not proceed until the spec makes it clear that the skill improves **testing judgment**, not syntax generation.

Recommended commit after this gate.

---

# 6. Stage 2 — Inspect, clean, and normalize the source Markdown

## Goal

Create a clean, stable, provenance-preserving representation of the Markdown source without destroying semantic content.

## Tools

Primary:

- Python
- `pymupdf`
- `markdown-it-py`
- regex/string processing
- hashing from the standard library

LLM use is not allowed for bulk cleanup.

## 6.1 Source inspection

Implement source inspection that:

- discovers the likely PDF and Markdown source files;
- computes hashes;
- counts lines and bytes;
- estimates token count;
- records Markdown heading distribution;
- records obvious repeated watermark/footer strings;
- records repeated OCR-like artifacts;
- determines PDF page count;
- samples PDF text extraction quality;
- compares selected PDF pages to corresponding Markdown sections.

Create:

```text
.local/work/source-report.json
docs/source-methodology.md
```

Only methodology and non-copyright-sensitive statistics belong in Git.

## 6.2 PDF as reference, not as a second bulk source

The Markdown is the main machine-readable input.

Use the PDF to:

- verify suspicious conversions;
- recover headings or code when Markdown is clearly corrupted;
- verify table/figure semantics when important;
- map source sections to pages where feasible.

Do not perform expensive OCR across the whole PDF unless text extraction fails and there is no better alternative.

If visual verification is necessary, render only the needed pages to `.local/renders/`.

## 6.3 Cleaner

Implement a deterministic cleaner that can handle, with auditability:

- repeated site watermarks/footers;
- isolated page numbers;
- repeated page headers;
- broken whitespace;
- obvious ligature/OCR spacing artifacts such as split words;
- malformed Markdown headings when correction is unambiguous;
- HTML break noise where safe;
- repeated "intentionally blank" boilerplate;
- extraction comments that do not carry semantic information.

Be conservative.

### Preserve

- headings;
- pattern names;
- smell names;
- tables;
- lists;
- code samples;
- figure text if it encodes relationships or decision structure;
- references between patterns;
- qualifiers such as "when to use," "variation," "cause," "impact," etc.

### Line provenance

Cleaning must preserve a mapping from each cleaned block/line to original Markdown lines.

Do not rely on fragile 1:1 line correspondence after transformations.

Create an explicit provenance map, e.g.:

```json
{
  "clean_block_id": "b000123",
  "clean_start_line": 900,
  "clean_end_line": 917,
  "source_start_line": 1044,
  "source_end_line": 1068,
  "transformations": [
    "removed_repeated_footer",
    "normalized_ligature_spacing"
  ]
}
```

## 6.4 Audit log

Every cleanup rule must have:

- a name;
- rationale;
- unit tests;
- examples using short synthetic snippets;
- count of applications.

Do not include large source excerpts in checked-in tests.

## Deliverables

Local:

```text
.local/work/book.cleaned.md
.local/work/line-map.jsonl
.local/work/cleanup-report.json
```

Committed:

```text
src/agentic_testcraft/clean.py
tests/unit/test_clean.py
docs/source-methodology.md
```

## Acceptance gate

- source files unchanged;
- cleaner reruns deterministically;
- cleanup tests pass;
- line/provenance mappings validate;
- code blocks and headings survive representative checks;
- no substantial source text accidentally committed.

Recommended commit after this gate.

---

# 7. Stage 3 — Build semantic structure and split by concepts, not token size

## Goal

Convert the cleaned book into semantically meaningful units suitable for reliable knowledge extraction.

## Tools

- Python;
- Markdown parser;
- deterministic heading/state-machine logic;
- PDF lookup only for ambiguous structure;
- LLM only for rare unresolved boundary cases, never as the default splitter.

## Do not do this

Do not split the source every N tokens as the primary strategy.

Token windows may be used as a safety cap after semantic splitting, but should not define conceptual boundaries.

## Semantic units

Recognize at least:

- front matter;
- goals;
- principles;
- roadmap/narrative guidance;
- code smells;
- behavior smells;
- project smells;
- strategy patterns;
- fixture patterns;
- result-verification patterns;
- teardown patterns;
- test-double patterns;
- test-organization patterns;
- database patterns;
- design-for-testability patterns;
- value patterns;
- glossary/index/reference-only content.

Within a pattern/smell, preserve substructure such as:

```text
Problem
Also known as
Context
Forces
Solution
How it works
When to use
Implementation notes
Variations
Motivating example
Refactoring notes
Symptoms
Impact
Causes
Solution patterns
Further reading
```

The exact headings differ; preserve the source's actual structure.

## Structural manifest

Create a local manifest such as:

```json
{
  "id": "pattern:test-double",
  "kind": "pattern",
  "title": "Test Double",
  "chapter": 23,
  "clean_start_line": 15000,
  "clean_end_line": 15400,
  "source_start_line": 15120,
  "source_end_line": 15580,
  "pdf_page_start": 522,
  "pdf_page_end": 528,
  "subsections": [
    "When to Use It",
    "Variation: Test Stub",
    "Variation: Test Spy",
    "Variation: Mock Object",
    "Variation: Fake Object"
  ]
}
```

## Completeness checks

Build deterministic checks for:

- duplicate semantic IDs;
- missing source ranges;
- overlapping impossible ranges;
- empty patterns;
- unclassified major chapters;
- broken references;
- unusually huge chunks;
- unexpectedly tiny chunks.

Use the book's own pattern/smell lists and index as cross-checks where possible.

Do not assume every index term is a separate pattern.

## Deliverables

Local:

```text
.local/chunks/
.local/work/structure.json
.local/work/chunk-manifest.jsonl
```

Committed:

```text
src/agentic_testcraft/structure.py
src/agentic_testcraft/chunk.py
tests/unit/test_structure.py
```

## Acceptance gate

- major source sections accounted for;
- semantic units preserve complete pattern/smell contexts;
- every extractable unit has provenance;
- no large source chunks committed.

Recommended commit after this gate.

---

# 8. Stage 4 — Design strict knowledge schemas before extraction

## Goal

Define machine-validatable data structures that force extraction to capture decision-relevant knowledge instead of generic summaries.

## Tools

- Pydantic;
- JSON Schema;
- Python validators;
- no external LLM required for the base schemas.

## 8.1 Common source reference

Every record must support:

```yaml
source_refs:
  - source_id: "book"
    file_sha256: "..."
    markdown_start_line: 1234
    markdown_end_line: 1288
    pdf_page_start: 100
    pdf_page_end: 102
```

## 8.2 Goal record

Minimum fields:

```yaml
id:
name:
summary:
why_it_matters:
indicators:
tensions:
related_principles:
source_refs:
confidence:
```

## 8.3 Principle record

Minimum fields:

```yaml
id:
name:
statement:
rationale:
default_rule:
exceptions:
tradeoffs:
failure_modes_if_ignored:
related_patterns:
related_smells:
agent_checks:
source_refs:
confidence:
```

## 8.4 Smell record

Minimum fields:

```yaml
id:
name:
aliases:
summary:
symptoms:
impact:
causes:
detection_heuristics:
false_positive_risks:
related_smells:
recommended_patterns:
agent_review_checks:
source_refs:
confidence:
```

Do not invent `false_positive_risks` from the book if unsupported; it may be null/empty until later synthesis.

## 8.5 Pattern record

Minimum fields:

```yaml
id:
name:
aliases:
category:
problem:
intent:
context:
forces:
solution:
use_when:
avoid_when:
benefits:
costs:
risks:
implementation_variations:
related_patterns:
prevents_smells:
may_cause_smells:
refactorings:
agent_decision_rule:
agent_actions:
common_misinterpretations:
historical_or_framework_specific_notes:
source_refs:
confidence:
```

Again, unsupported fields remain empty rather than fabricated.

## 8.6 Relationship record

```yaml
from_id:
relationship:
to_id:
strength:
rationale:
source_refs:
origin:
confidence:
```

Relationship vocabulary should be controlled, for example:

```text
supports
implements
alternative_to
variation_of
specialization_of
used_with
prevents
may_cause
caused_by
refactors_to
requires
conflicts_with
preferred_over_when
```

Extend only with documented need.

## 8.7 Decision rule record

This becomes especially important in synthesis.

```yaml
id:
trigger:
context:
default_action:
decision_logic:
exceptions:
warnings:
evidence_ids:
origin:
strength:
applicability:
agent_verification:
```

## 8.8 Modernization record

```yaml
id:
topic:
book_position:
modern_position:
status:
  # unchanged | clarified | expanded | narrowed | superseded | historical
rationale:
official_sources:
affected_knowledge_ids:
agent_rule_change:
review_date:
```

## 8.9 Validation

Generate JSON Schema from Pydantic models or keep the two in sync programmatically.

Tests must detect:

- malformed IDs;
- invalid origin values;
- missing provenance on book records;
- references to unknown IDs;
- impossible line ranges;
- duplicate IDs;
- unsupported relationship types.

## Deliverables

- Pydantic models
- JSON schemas
- validator CLI
- unit tests
- schema documentation

## Acceptance gate

A human/agent should be able to inspect the schemas and see that they capture **decision logic and tradeoffs**, not merely summaries.

Recommended commit after this gate.

---

# 9. Stage 5 — Extract book knowledge with structured outputs

## Goal

Extract source-faithful structured knowledge from every relevant semantic unit.

This is the first stage where semantic LLM extraction is central.

## Tools

Preferred:

- a current high-quality model that supports structured/JSON-schema-constrained output;
- provider SDK;
- Pydantic validation;
- retry logic;
- local extraction cache.

Model choice must be resolved at execution time from **current official provider documentation**.

### Model selection guidance

For bulk extraction, prefer:

- high reliability;
- structured outputs;
- sufficient context for a full semantic unit;
- reasonable cost.

A full 1M-token context model is not required for every chunk.

Use a stronger long-context reasoning model for difficult or ambiguous chunks and later synthesis.

Record exact model IDs in run metadata.

## Provider abstraction

Implement extraction behind a small provider abstraction so the knowledge pipeline is not hard-wired to one vendor.

Do not over-engineer a universal framework; support what is actually used.

Possible execution modes:

```text
native-agent
openai
anthropic
google
```

If no API credentials are available, the implementation agent may perform extraction natively in semantic batches, but it must still write records through the same validators and provenance system.

## Extraction prompt contract

The extraction prompt must explicitly say:

- extract only what the supplied source supports;
- preserve the author's terminology where semantically important;
- paraphrase instead of copying long passages;
- do not modernize;
- do not "improve" the author's advice;
- do not fill schema fields from general model knowledge;
- distinguish explicit claims from cautious inference;
- attach source range IDs;
- return valid schema-constrained output only.

## Extraction strategy

Process by semantic unit:

```text
goal section -> goal records
principle section -> principle records
smell section -> smell records
pattern section -> pattern records
narrative/roadmap section -> candidate decision rules and cross-links
```

Do not blindly extract all glossary/index content.

Use the index and summary tables to validate completeness and aliases.

## Validation loop

For each output:

1. parse;
2. validate against Pydantic/JSON Schema;
3. validate all IDs;
4. validate provenance;
5. validate references;
6. reject records with unsupported invented source ranges;
7. retry only the failed unit;
8. cache the valid result.

## Second-pass source-faithfulness audit

A different pass should review a sample—and all low-confidence records—for:

- claims not supported by the chunk;
- collapsed nuance;
- misclassified "always" rules;
- lost exceptions;
- accidental modernization;
- confused aliases/variations/causes.

Where practical, use a stronger model for this audit.

## Output format

Prefer JSONL for atomic records:

```text
knowledge/book/goals.jsonl
knowledge/book/principles.jsonl
knowledge/book/smells.jsonl
knowledge/book/patterns.jsonl
knowledge/book/narrative-rules.jsonl
```

No long source prose should be embedded.

## Acceptance gate

Required:

- 100% schema-valid records;
- 100% book records have provenance;
- no unresolved unknown record references;
- extraction coverage report exists;
- low-confidence records are explicitly listed;
- sampled source-faithfulness review is documented;
- no modern practices silently inserted.

Recommended commit after this gate.

---

# 10. Stage 6 — Build and validate the pattern/smell/principle relationship graph

## Goal

Recover the book's value as a **pattern language**, not just a catalog.

The skill should eventually reason about consequences and alternatives, e.g.:

```text
choice -> tradeoff -> smell risk -> alternative pattern
```

## Tools

- Python;
- NetworkX;
- deterministic cross-reference parser;
- strong LLM for semantic relationships not explicitly encoded;
- schema validator.

## 10.1 Deterministic graph first

Build edges from:

- explicit "see" references;
- aliases;
- variations;
- "cause of";
- "solution pattern";
- related-pattern sections;
- book summary tables;
- pattern index/cross-reference material.

Label every deterministic edge as source-explicit where appropriate.

## 10.2 Semantic graph second

Use a strong model to propose only relationships that require semantic synthesis.

Every proposed semantic edge must include:

- supporting knowledge IDs;
- rationale;
- source provenance;
- confidence;
- whether it is explicit or inferred.

Do not allow an inference to masquerade as an explicit source relationship.

## 10.3 Graph checks

Validate:

- all nodes exist;
- all referenced IDs exist;
- no impossible self-edges unless meaningful;
- no duplicate edges with conflicting relation semantics;
- isolated important nodes are reviewed;
- cycles are allowed when conceptually valid but should be inspectable.

Generate useful graph statistics.

Optional: generate a small visual graph for maintainers, but do not make the final runtime skill depend on graph visualization.

## Deliverables

```text
knowledge/graph/relationships.jsonl
knowledge/graph/graph.json
docs/architecture.md
```

Optional:

```text
docs/pattern-graph.svg
```

## Acceptance gate

The graph should answer questions such as:

- What smells can this pattern prevent?
- What new risks can it introduce?
- What is an alternative?
- What principle motivates it?
- What patterns are typically used together?
- What does a smell suggest reviewing?

Recommended commit after this gate.

---

# 11. Stage 7 — Global synthesis into operational testing judgment

## Goal

Transform structured source knowledge into compact, operational decision rules suitable for an autonomous coding agent.

This is where a large-context reasoning model is most valuable.

## Tools

- current frontier long-context reasoning model;
- structured knowledge artifacts;
- relationship graph;
- Python validators;
- optional token accounting.

Do **not** use the raw book as the only input to this stage. Prefer the higher-signal structured corpus, plus targeted source excerpts only when needed to resolve ambiguity.

## Model selection

At execution time, verify current official model documentation.

Prefer a model with:

- strong reasoning;
- long context;
- reliable instruction following;
- enough context for the entire structured knowledge corpus;
- structured output if possible.

A roughly million-token context window is useful here, but quality of reasoning and retrieval discipline matter more than raw window size.

## Synthesis tasks

Produce explicit decision systems for at least:

### A. Test intent and scope

- identify observable behavior;
- distinguish behavior from implementation;
- identify test conditions;
- avoid redundant overlap.

### B. Test level/boundary

Create a decision framework for when the smallest useful boundary is enough and when a larger boundary is necessary.

Do not create a rigid universal "test pyramid" rule unless added later as a clearly modern external concept.

### C. Verification strategy

Decision logic for:

- direct output/state verification;
- behavior/interaction verification;
- back-door verification;
- custom/domain assertions.

The output should strongly guard against unnecessary interaction assertions.

### D. Fixture strategy

Decision logic for:

- minimal fixture;
- fresh fixture;
- standard fixture;
- shared/persistent fixture;
- setup/teardown tradeoffs;
- external-resource isolation.

### E. Dependency strategy

Decision logic for:

```text
real dependency
fake
stub
spy
mock
dummy
```

The decision must be driven by why the dependency is being replaced.

Explicitly handle:

- controllable indirect inputs;
- indirect outputs;
- nondeterminism;
- clock/time;
- random/UUID generation;
- network;
- database;
- file system;
- queues/events;
- concurrency;
- expensive setup.

### F. Test smell review

Create actionable detection and remediation rules for major smells.

The skill should not merely name smells; it should tell the agent:

- what evidence to inspect;
- why it matters;
- likely root causes;
- what alternatives to consider.

### G. Testability refactoring

Create rules for when the agent may propose or perform a small behavior-preserving production-code refactor to improve testability.

Guardrails:

- never change production behavior merely to make a test pass;
- prefer dependency boundaries over test-only conditionals;
- keep test logic out of production code;
- keep refactorings minimal and separately understandable;
- run existing tests before and after when possible.

### H. Test execution workflow

Create an execution strategy:

1. inspect repository;
2. identify existing framework and conventions;
3. identify relevant behavior;
4. choose boundary and test conditions;
5. choose verification;
6. design fixture;
7. classify dependencies;
8. write smallest useful tests;
9. run focused tests;
10. diagnose failures;
11. review for smells;
12. run affected broader suite;
13. optionally perform stronger validation such as targeted mutation testing where justified;
14. report what was validated.

## Very important semantic rule

Encode explicitly:

```text
"Verify one condition per test" does NOT mean "one assertion per test."
```

Multiple assertions are appropriate when they jointly verify one coherent observable outcome.

## Create synthesized artifacts

At minimum:

```text
knowledge/synthesized/testing-workflow.md
knowledge/synthesized/test-boundary-decision.md
knowledge/synthesized/verification-decision.md
knowledge/synthesized/fixture-decision.md
knowledge/synthesized/test-double-decision.md
knowledge/synthesized/test-smell-review.md
knowledge/synthesized/testability-refactoring.md
knowledge/synthesized/decision-rules.jsonl
```

Each synthesized rule must retain evidence IDs back to the structured knowledge.

## Contradiction and nuance audit

Ask the synthesis model to identify:

- tensions between principles;
- context-dependent recommendations;
- historical assumptions;
- dangerous literal interpretations;
- apparent conflicts;
- missing decision criteria.

Record unresolved issues in:

```text
knowledge/synthesized/open-questions.md
```

## Acceptance gate

Synthesis should be actionable enough that an agent can follow it without loading the whole book.

Recommended commit after this gate.

---

# 12. Stage 8 — Modernize carefully using current primary/official sources

## Goal

Update the operational skill for modern software-development practice while preserving a clean boundary between source-derived principles and modern additions.

## Tools

- web research;
- **primary/official documentation only for technical claims whenever available;**
- frontier reasoning model;
- modernization schema;
- current date recorded in artifacts.

## Source policy

For technical modernization, prefer:

- official framework documentation;
- official language documentation;
- official tool documentation;
- original research papers where directly relevant;
- official specifications.

Avoid using random blog posts as authority when primary documentation exists.

Every external claim must have a URL/source citation in the modernization records.

## Research current skill specifications

Before writing the final skill, verify the current official Agent Skills / coding-agent extension specifications for the intended targets.

At minimum investigate current official documentation for:

- OpenAI/Codex skill support;
- Anthropic/Claude Code skill support;
- the open Agent Skills format/specification if relevant.

Do not assume previously remembered front matter, directory names, size limits, or loading behavior are still current.

Document compatibility decisions.

## Modernization topics to investigate

Do not force all of these into the skill. Evaluate them as gaps and include only those that materially improve testing judgment.

At minimum review:

### Runtime and determinism

- async/await testing;
- concurrency and races;
- virtual/fake clocks;
- random/UUID control;
- retries and flakiness;
- event-driven systems;
- eventual consistency.

### Modern integration testing

- containerized databases/services;
- disposable environments;
- hermeticity;
- realistic integration tests without globally shared state.

### Browser/application testing

- modern browser automation;
- stable locators;
- waiting/synchronization;
- avoiding brittle implementation-detail assertions.

### Test effectiveness

- mutation testing;
- property-based testing;
- fuzzing when appropriate;
- contract testing where applicable.

### Assertion styles

- domain assertions;
- snapshot/golden tests and brittleness risks;
- rich diagnostics.

### Service boundaries

- HTTP clients;
- message queues;
- third-party APIs;
- local fakes vs mocks vs sandbox services;
- contract boundaries.

### Modern repository reality

- monorepos;
- incremental test selection;
- CI parallelism;
- test sharding;
- ephemeral CI;
- platform-dependent tests.

## Ecosystem-specific references

Keep the core skill framework-independent.

If needed, place framework-specific guidance under progressive references such as:

```text
skill/agentic-testcraft/references/ecosystems/
├── python-pytest.md
├── typescript-vitest-jest.md
├── java-junit.md
├── dotnet-xunit-nunit.md
├── go-testing.md
└── browser-playwright.md
```

Only create files that are actually researched and useful.

These references should translate the core decision rules into current framework idioms, not duplicate framework manuals.

## Modernization classification

For each major book-derived concept, classify where relevant:

```text
unchanged
clarified
expanded
narrowed
superseded
historical
```

Example structure:

```yaml
topic: "test doubles for external dependencies"
book_position: "..."
modern_position: "..."
status: "clarified"
rationale: "..."
official_sources:
  - "..."
affected_knowledge_ids:
  - "pattern:test-double"
agent_rule_change: "..."
review_date: "YYYY-MM-DD"
```

Do not include long book quotations.

## Deliverables

```text
knowledge/modern/modernization.jsonl
knowledge/modern/current-testing-practices.md
docs/modernization-methodology.md
docs/decisions/skill-compatibility.md
```

## Acceptance gate

- all modern claims sourced;
- source-derived and modern-derived knowledge remain distinguishable;
- obsolete mechanics are not blindly carried into the final skill;
- timeless ideas are not discarded merely because examples are old;
- framework-specific details stay out of the core unless truly universal.

Recommended commit after this gate.

---

# 13. Stage 9 — Author the production Agent Skill

## Goal

Build the final, compact, high-leverage skill.

The final runtime artifact should behave like expert procedural guidance, not like an encyclopedia.

## Tools

- current official skill specification(s);
- synthesized knowledge;
- modernization layer;
- coding agent;
- static validators;
- optional cross-agent compatibility checks.

## Skill name

Use:

```text
agentic-testcraft
```

Human-facing title:

```text
Agentic Testcraft
```

Suggested short description:

```text
Design, write, review, refactor, and validate maintainable automated tests using behavior-focused test design, principled fixtures and test doubles, test-smell detection, and modern testability practices.
```

Improve wording if the current skill specification imposes metadata constraints.

## Core design principle: progressive disclosure

`SKILL.md` should be concise.

It should contain:

- when the skill applies;
- the core workflow;
- core defaults and guardrails;
- routing instructions to references;
- completion/validation behavior.

Detailed catalogs belong in `references/`.

Do not put the whole book or all extracted knowledge in `SKILL.md`.

## Recommended skill structure

```text
skill/agentic-testcraft/
├── SKILL.md
├── references/
│   ├── core-principles.md
│   ├── test-boundaries.md
│   ├── verification.md
│   ├── fixtures.md
│   ├── test-doubles.md
│   ├── test-smells.md
│   ├── testability.md
│   ├── databases-and-resources.md
│   ├── async-concurrency-and-flakiness.md
│   ├── test-effectiveness.md
│   ├── decision-trees.md
│   └── ecosystems/
├── scripts/
│   └── optional deterministic helpers only
└── assets/
    └── only if genuinely useful
```

## Runtime workflow the skill must enforce

When asked to write or modify tests, the skill should direct the agent to:

### 1. Inspect before writing

Determine:

- language;
- test framework;
- repository conventions;
- existing nearby tests;
- test commands;
- SUT and dependencies;
- architectural boundary;
- available test helpers/fixtures/factories;
- CI constraints if visible.

Do not introduce a new framework without a compelling reason.

### 2. Define the behavior

State the observable behavior/test condition being verified.

Distinguish:

- requirement/behavior;
- implementation details;
- incidental calls.

### 3. Choose the smallest useful test boundary

Prefer a smaller boundary when it can faithfully verify the behavior.

Use a larger boundary when the behavior intrinsically crosses components or when isolation would test the wrong thing.

### 4. Choose verification strategy

Default toward direct/state verification through a stable public interface when sufficient.

Use behavior/interaction verification when:

- the interaction itself is the required observable behavior; or
- no reliable direct post-state/output adequately verifies the requirement.

Avoid asserting incidental internal calls.

### 5. Design the fixture

Default toward:

- minimal fixture;
- fresh/independent state.

Use shared/persistent fixtures only for demonstrated cost or technical reasons and actively manage resulting coupling risks.

### 6. Classify every replaced dependency

Before creating a double, identify why it is being replaced.

Ask:

- Need to supply a controlled indirect input? -> consider a stub.
- Need to observe calls after execution? -> consider a spy.
- Is the interaction itself part of the required behavior and expectation-style verification is appropriate? -> consider a mock.
- Need a lightweight working implementation with realistic semantics? -> consider a fake.
- Need only a placeholder that must never be used? -> dummy.
- Is the real dependency fast, deterministic, local, and safe? -> consider using it instead of a double.

Never apply the rule:

```text
dependency exists -> mock it
```

### 7. Write intention-revealing tests

Tests should make the behavior obvious.

Avoid:

- unexplained literals;
- giant fixtures;
- conditional logic inside tests;
- irrelevant setup;
- hidden mystery guests;
- excessive helper indirection;
- duplication that obscures intent.

Do not prematurely extract helpers. Extract them when repetition or noise is real and the helper can have an intent-revealing name.

### 8. Preserve test independence

Each test should be runnable independently unless the project intentionally uses another well-justified model.

Avoid order dependence and shared mutable state.

### 9. Run the smallest relevant scope first

Examples:

- one test;
- one file/class;
- one package/module.

Then run the broader affected suite.

### 10. Review the generated test for smells before completion

At minimum review for:

- Obscure Test;
- Conditional Test Logic;
- Test Code Duplication;
- Assertion Roulette;
- Erratic/Flaky Test;
- Fragile Test;
- General/Overgrown Fixture;
- Mystery Guest;
- excessive interaction verification;
- unnecessary mocks;
- overspecified behavior;
- slow setup;
- hidden shared state.

### 11. Validate effectiveness

When risk and tooling justify it, use stronger validation:

- targeted mutation testing;
- property-based testing;
- focused fault seeding;
- integration confirmation against the real dependency boundary.

Do not add heavyweight validation mechanically to every trivial change.

### 12. Report completion precisely

The agent should report:

- tests added/changed;
- behavior covered;
- test command(s) run;
- result;
- any production refactor performed for testability;
- any important residual risk or untested boundary.

## Guardrails that should appear in the final skill

At minimum:

- passing tests are necessary but not sufficient;
- coverage percentage is not the primary objective;
- do not mock the SUT;
- do not assert every internal call;
- do not change production behavior to satisfy a test;
- do not add `if testing` style production branches when a cleaner dependency boundary is possible;
- do not introduce shared mutable fixtures merely to save setup code;
- do not turn "one condition per test" into "one assertion per test";
- do not ignore existing project conventions;
- do not blindly port historical framework mechanics from the source book.

## Reference quality

Each reference document should:

- be self-contained enough for the decision it supports;
- avoid duplicate prose;
- use concise tables/decision trees where useful;
- clearly distinguish defaults, exceptions, and warnings;
- retain evidence IDs internally during authoring;
- avoid copyright-significant reproduction.

The user-facing/runtime references do not need to expose every source line, but the repository should preserve traceability from final rules to knowledge IDs.

## Traceability map

Create:

```text
knowledge/synthesized/skill-traceability.json
```

It should map major final skill rules to:

- synthesized rule IDs;
- book knowledge IDs;
- modernization IDs;
- official external sources where relevant.

## Skill validation

Implement checks for:

- required metadata/front matter;
- current specification compliance;
- broken local links;
- missing referenced files;
- duplicate/conflicting rules;
- overly large core file;
- accidental source-book excerpts;
- stale TODOs/placeholders.

If current target platforms provide official validators, run them.

## Acceptance gate

The final skill should be useful when loaded alone, while detailed references are loaded only when needed.

Recommended commit after this gate.

---

# 14. Stage 10 — Build rigorous evaluations and harden the skill

## Goal

Prove whether `agentic-testcraft` actually improves coding-agent test behavior.

A polished `SKILL.md` without evaluation is not enough.

## Tools

Core:

- Git;
- Docker or equivalent isolation when useful;
- real language test runners;
- Python evaluation harness;
- mutation-testing tools where practical;
- coding-agent CLI/API if available;
- structured result storage.

Use current official documentation for every tool selected.

## 14.1 Evaluation philosophy

Compare:

```text
A: same coding agent + same task + no skill
B: same coding agent + same task + Agentic Testcraft
```

Control as many variables as practical:

- same base model;
- same repository state;
- same task text;
- same tool permissions;
- same time/turn budget if configurable;
- fresh checkout/worktree per run.

Do not compare different models and attribute the difference to the skill.

## 14.2 Scenario catalog

Build a representative suite. Start with enough cases to expose real judgment differences, not merely syntax.

Include scenarios such as:

1. pure deterministic function;
2. object with no dependencies;
3. clock dependency;
4. random/UUID dependency;
5. external HTTP client;
6. database repository;
7. event publisher;
8. message consumer;
9. file-system dependency;
10. cache dependency;
11. async service;
12. race/concurrency risk;
13. flaky sleep-based test;
14. shared mutable fixture;
15. expensive fixture;
16. over-mocking trap;
17. spy-vs-mock decision;
18. fake-vs-stub decision;
19. state-vs-behavior verification;
20. behavior where interaction really is the requirement;
21. obscure test with giant setup;
22. mystery guest;
23. assertion roulette;
24. conditional test logic;
25. brittle implementation-detail test;
26. legacy hard-to-test code;
27. small testability refactor;
28. integration boundary where a unit test is insufficient;
29. browser/UI synchronization issue;
30. existing failing test that should be diagnosed rather than rewritten.

Add more only when they exercise distinct decisions.

## 14.3 Multiple ecosystems

The skill claims framework-independent value. Validate across several ecosystems if tooling permits.

A strong initial target is at least three distinct ecosystems, for example:

- Python + `pytest`;
- TypeScript + Vitest/Jest;
- JVM + JUnit or .NET + xUnit/NUnit or Go's testing package.

Choose based on available tools and document the rationale.

Do not explode the scope by duplicating every scenario in every language. Use a balanced matrix.

## 14.4 Seeded defects

Each eval case should contain one or more plausible defects the generated tests should catch.

Examples:

- boundary operator changed;
- validation removed;
- wrong branch result;
- omitted side effect;
- wrong event payload;
- incorrect retry count;
- stale cache behavior;
- wrong exception;
- missing persistence;
- clock/time-zone bug.

The expected goal is to verify behavior, not exact test source.

## 14.5 Mutation testing

Where tooling is stable, mutation testing is a high-value metric.

Potential tools, to verify against current official docs before use:

- Python: a maintained mutation-testing tool;
- JavaScript/TypeScript: Stryker;
- JVM: PIT;
- .NET: Stryker.NET or current equivalent.

Do not hard-code stale commands from memory.

Record:

- mutants generated;
- mutants killed;
- survived;
- timed out;
- excluded;
- mutation score.

Use targeted mutation scopes to keep evals tractable.

## 14.6 Deterministic metrics

Collect where applicable:

- tests pass;
- seeded bugs caught;
- mutation score;
- independent execution success;
- order-randomization success;
- repeated-run stability;
- focused test runtime;
- broader suite runtime;
- number of production files modified;
- unnecessary new dependencies;
- number of mocks/doubles introduced;
- whether the SUT itself was mocked;
- whether real safe dependencies were replaced unnecessarily;
- whether existing repository conventions were preserved.

## 14.7 Qualitative rubric

Create a structured rubric for:

- behavior focus;
- intent/readability;
- fixture minimality;
- overspecification;
- appropriate dependency strategy;
- maintainability;
- diagnostic quality;
- appropriate test level;
- unnecessary implementation coupling.

Use anchored scoring criteria, not vague 1–10 impressions.

Example:

```text
0 = clearly harmful/incorrect
1 = weak
2 = acceptable
3 = strong
4 = exemplary
```

Define each level per dimension.

If an LLM judge is used:

- use a different evaluation context from the test-writing agent;
- provide a strict rubric;
- randomize A/B labels when possible;
- record judge model/version;
- never let the judge see which output used the skill;
- supplement with deterministic metrics.

## 14.8 Eval harness

The harness should support:

```bash
agentic-testcraft eval list
agentic-testcraft eval run <case>
agentic-testcraft eval run-all
agentic-testcraft eval compare <run-a> <run-b>
agentic-testcraft eval report
```

If direct coding-agent invocation is not available, still build:

- reproducible case repositories;
- task prompts;
- reset scripts;
- scoring scripts;
- a documented manual/semiautomated A/B protocol.

## 14.9 Results storage

Use machine-readable results:

```text
evals/results/<run-id>/
├── metadata.json
├── per-case.jsonl
├── summary.json
└── report.md
```

Do not commit huge raw model transcripts by default.

## 14.10 Release criteria

Initial release-candidate criteria:

### Hard requirements

- all knowledge schemas valid;
- no missing provenance for book-derived records;
- skill validation passes;
- no source PDF/full Markdown committed unintentionally;
- no secrets;
- core repo tests pass;
- eval harness is reproducible;
- final skill has no critical known instruction conflict.

### Behavioral requirements

The skill-enabled condition must show a clear, reproducible improvement over baseline on the combined evaluation, especially in:

- catching seeded defects;
- avoiding unnecessary mocks;
- reducing brittle implementation coupling;
- fixture quality;
- test independence;
- test readability/intent;
- mutation effectiveness where measured.

Do not declare success from one cherry-picked example.

If the skill improves qualitative scores but harms deterministic defect detection, investigate before release.

## 14.11 Failure-driven iteration

Use eval failures to update the skill.

Examples:

### Failure: agent still over-mocks

Strengthen:

- state-first verification;
- "real dependency if fast/local/deterministic/safe";
- fake-vs-mock decision rules;
- incidental-call warning.

Add a regression eval.

### Failure: agent interprets one condition as one assertion

Add an explicit counterexample/rule.

Add a regression eval.

### Failure: agent uses huge fixtures

Strengthen minimal/fresh fixture routing.

Add a regression eval.

### Failure: agent changes production code too much

Strengthen testability-refactoring guardrails.

Add a regression eval.

### Failure: tests pass but miss mutations

Strengthen outcome selection and assertion quality.

Add a regression eval.

Every significant skill change after initial evals should be tied to a documented failure, new evidence, or clearly stated design objective.

## Deliverables

- complete eval harness;
- case catalog;
- rubrics;
- A/B protocol;
- baseline results;
- skill-enabled results;
- comparison report;
- regression cases;
- `docs/evaluation-methodology.md`.

Recommended commits:

1. eval framework;
2. initial scenario suite;
3. baseline;
4. skill-enabled run;
5. failure-driven hardening;
6. release candidate.

---

# 15. Final skill knowledge architecture

The completed repository should maintain three separate knowledge layers.

## Layer A — Source-faithful book knowledge

```text
knowledge/book/
```

Properties:

- derived only from the supplied source;
- no silent modernization;
- provenance mandatory;
- structured and paraphrased.

## Layer B — Modern additions

```text
knowledge/modern/
```

Properties:

- current;
- externally sourced;
- primary/official sources preferred;
- dated;
- explicitly classified.

## Layer C — Synthesized operational rules

```text
knowledge/synthesized/
```

Properties:

- optimized for coding-agent decisions;
- evidence-linked to A and/or B;
- compact;
- conflict-aware;
- used to generate the final skill.

This separation is a core architectural invariant.

---

# 16. Suggested final knowledge areas

The final runtime skill should probably cover these areas, subject to actual extraction and evaluation:

```text
Core testing goals
Core principles
Test intent and scope
Test condition selection
Test boundaries / levels
Four-phase test structure
State/direct verification
Behavior/interaction verification
Custom/domain assertions
Fixture design
Fresh vs shared fixtures
Setup and teardown
External resources
Databases
Test doubles
Dummy / Stub / Spy / Mock / Fake
Dependency injection and testability
Humble-object style separation
Test organization
Test utility methods
Test smells
Fragility and overspecification
Erratic/flaky tests
Obscure tests
Slow tests
Modern async/concurrency
Modern integration environments
Property-based testing
Mutation testing
Browser testing
Validation workflow
```

Do not include a topic simply because it appears in this list. Include it when source evidence, modern evidence, or eval value justifies it.

---

# 17. Decision-rule quality standard

A final rule is good when it contains:

1. a trigger;
2. a default;
3. a reason;
4. exceptions;
5. risks;
6. a verification step.

Example shape:

```yaml
trigger: "The SUT depends on a collaborator."
default_action: >
  Keep the real collaborator when it is fast, deterministic, local, safe,
  and part of the useful test boundary.
decision_logic:
  - condition: "Need controlled indirect inputs"
    action: "Use a stub or configurable fake."
  - condition: "Need to inspect indirect outputs after exercise"
    action: "Use a spy."
  - condition: "Interaction itself is the required behavior"
    action: "A mock may be appropriate."
warnings:
  - "Do not replace dependencies merely because a mocking library exists."
  - "Do not assert incidental calls."
agent_verification:
  - "Explain why each double exists."
```

The exact final rule must be evidence-based. This example defines the desired operational style.

---

# 18. Testing the extraction pipeline itself

The project is about testing; its own pipeline should be well tested.

Add tests for:

- source discovery;
- hashing;
- cleanup transforms;
- provenance maps;
- semantic heading parsing;
- chunk boundary logic;
- schema validation;
- unknown reference detection;
- graph edge validation;
- extraction cache behavior;
- retry behavior;
- skill link validation;
- copyright-source leak checks;
- eval result parsing.

Use small synthetic fixtures instead of copyrighted source excerpts whenever possible.

---

# 19. Source-leak prevention

Add a validator that helps prevent accidental publication of the book.

At minimum it should:

- verify ignored source filenames are not tracked;
- flag unusually long passages in generated knowledge;
- detect accidental copies of local chunk files into tracked directories;
- detect known watermark strings;
- optionally compare long n-grams between tracked Markdown and local source and flag suspicious overlap.

This validator is a safety mechanism, not a legal determination.

Run it before release commits.

---

# 20. Documentation requirements

The public repository should explain what it is without distributing the book.

## README.md

Include:

- what Agentic Testcraft does;
- why it exists;
- that it was inspired by/derived from structured study of *xUnit Test Patterns*;
- that the source book is not redistributed;
- how the skill differs from a book summary;
- supported agent platforms, based on current validation;
- installation/use instructions;
- how to run validators;
- how to run evals;
- current evaluation headline results;
- limitations.

Do not claim universal superiority.

## docs/source-methodology.md

Explain:

- source handling;
- cleanup;
- semantic splitting;
- provenance;
- extraction constraints.

## docs/modernization-methodology.md

Explain:

- distinction between book and modern sources;
- primary-source policy;
- review date;
- modernization statuses.

## docs/evaluation-methodology.md

Explain:

- A/B method;
- cases;
- metrics;
- mutation testing;
- qualitative judge;
- limitations.

## NOTICE.md

State clearly that:

- the original book is copyrighted by its rights holder;
- the repository does not grant rights to the book;
- the PDF/source Markdown are not intended to be redistributed by this repository;
- repository artifacts are transformed tooling/knowledge, not a copy of the book.

Do not make legal claims beyond what can be safely supported.

---

# 21. Suggested milestone sequence

A practical autonomous sequence is:

```text
M0  Bootstrap repository/tooling
M1  Skill specification
M2  Source inspection + cleaner + provenance
M3  Semantic structure/chunking
M4  Schemas + validators
M5  Complete source extraction
M6  Relationship graph
M7  Global synthesis
M8  Modernization
M9  Production skill v1
M10 Eval suite + baseline
M11 Skill-enabled eval
M12 Failure-driven hardening
M13 Cross-agent compatibility
M14 Release candidate
```

Do not skip directly from source Markdown to `SKILL.md`.

---

# 22. Final end-to-end validation checklist

Before declaring the project complete, verify all of the following.

## Repository

- [ ] source book files are not accidentally tracked;
- [ ] no secrets are committed;
- [ ] Python project installs cleanly;
- [ ] CLI help works;
- [ ] tests pass;
- [ ] lint/static checks pass;
- [ ] CI passes without access to the book.

## Source pipeline

- [ ] source hashes recorded locally;
- [ ] cleaner deterministic;
- [ ] provenance map valid;
- [ ] semantic chunking complete;
- [ ] cleanup report produced;
- [ ] source leak validator passes.

## Knowledge

- [ ] schemas valid;
- [ ] all book records have provenance;
- [ ] IDs unique;
- [ ] links valid;
- [ ] low-confidence items reviewed;
- [ ] book and modern knowledge separated;
- [ ] graph validated;
- [ ] synthesis evidence-linked.

## Modernization

- [ ] current official skill specs checked;
- [ ] current framework/tool docs used;
- [ ] external claims cited;
- [ ] review date recorded;
- [ ] historical mechanics not silently treated as modern defaults.

## Skill

- [ ] `SKILL.md` concise;
- [ ] progressive references work;
- [ ] no large source excerpts;
- [ ] state-vs-behavior decision explicit;
- [ ] fixture decision explicit;
- [ ] test-double classification explicit;
- [ ] over-mocking guardrail explicit;
- [ ] one-condition-not-one-assertion explicit;
- [ ] testability guardrails explicit;
- [ ] smell review explicit;
- [ ] focused-then-broader execution explicit;
- [ ] completion reporting explicit;
- [ ] current format validators pass.

## Evaluation

- [ ] meaningful case catalog exists;
- [ ] baseline A runs captured;
- [ ] skill B runs captured;
- [ ] deterministic metrics collected;
- [ ] mutation testing used where practical;
- [ ] qualitative rubric anchored;
- [ ] A/B labels blinded to judge when possible;
- [ ] results reproducible;
- [ ] failures converted to regression cases;
- [ ] skill shows clear value over baseline.

## Documentation

- [ ] README complete;
- [ ] source methodology complete;
- [ ] modernization methodology complete;
- [ ] evaluation methodology complete;
- [ ] architecture documented;
- [ ] known limitations documented.

---

# 23. Definition of done

The project is done only when all of the following are true:

1. The source book has been transformed into structured, provenance-linked knowledge rather than merely summarized.
2. Historical/source-specific guidance is separated from modern additions.
3. The final skill is compact enough to be useful in an agent context window.
4. The skill contains executable decision guidance, not just definitions.
5. The skill adapts to the host repository's language, framework, and conventions.
6. It improves the coding agent's decisions around verification, fixtures, doubles, testability, and smells.
7. It has measurable evidence of benefit on a nontrivial A/B eval suite.
8. It avoids distributing the copyrighted source.
9. The repository can be cloned and its public tooling/tests run without the source book.
10. Major claims and rules are traceable to source or modern evidence.
11. The working tree is clean.
12. The final commits are reviewable and well described.

---

# 24. Final instruction

Begin with repository inspection and Phase 0 bootstrap.

Then execute Stages 1 through 10 in order.

Do not skip quality gates.

Do not jump ahead to writing the final skill before the structured knowledge and synthesis layers exist.

Use deterministic Python tooling wherever practical, use strong language models only where semantic judgment adds real value, use current primary/official documentation for modernization, and let evaluation failures drive the final hardening.

The objective is not to preserve the book's wording.

The objective is to preserve and modernize its **testing judgment** well enough that a modern coding agent consistently produces better tests because this skill exists.
