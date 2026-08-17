# Build Progress Report

A running narrative of how each milestone (`M0`–`M14`) was executed, its
deterministic outputs, and key quality-gate results. Updated after each
milestone.

---

## M0 — Bootstrap repository / tooling

**How:** Created the project skeleton per Phase 0 of
`AGENTIC_TESTCRAFT_BUILD.md`:

- `pyproject.toml` (Python ≥3.12, `uv`-managed) with `pydantic`, `typer`,
  `rich`, `PyYAML`, `networkx`, `markdown-it-py`, `pymupdf`, `httpx`,
  `tenacity`; dev extras for `pytest`, `ruff`, `mypy`.
- Removed the copyrighted PDF/Markdown from Git tracking (`git rm --cached`)
  while keeping them in the working tree; added both to `.gitignore` together
  with `.local/`, `*.egg-info/`, `.venv/`.
- `src/agentic_testcraft/` package: `__init__`, `cli` (typer), `config`,
  `provenance`, `schemas`.
- `schemas/` JSON-Schema files for source-ref, goal, principle, smell,
  pattern, decision-rule, relationship, modernization, source-manifest.
- `NOTICE.md`, `CONTRIBUTING.md`, `.editorconfig`, `.env.example`.

**Outputs:** clean working tree; `agentic-testcraft --help` lists all
pipeline commands; `uv sync` reproducible.

**Verification:** `tests/unit/test_config.py`, `tests/unit/test_provenance.py`,
`tests/unit/test_clean.py` pass (pytest, randomised order via `pytest-randomly`).

**Commit:** `e6f3b14` + `5a0f653` (squashed egg-info removal).

---

## M1 — Skill specification

**How:** Authored `docs/skill-spec.md` *before* any knowledge extraction so the
pipeline targets testing judgment, not book summarisation. Defined 12 primary
use cases, 7 non-goals, 13 decision points, 8 core decision rules (R1–R8),
final-skill acceptance criteria, a 20-term glossary, and A/B evaluation
acceptance criteria.

**Verification (gate):** The spec makes explicit that the skill improves
testing **judgment** (boundary choice, verification strategy, fixture/double
strategy, smell detection, testability refactors, effectiveness validation) —
not framework syntax.

**Commit:** `0da7d9d`.

---

## M2 — Source inspection + deterministic cleaner + provenance

**How:**

1. **Discovery/inspection** (`source_inspect.py`): globs `xUnit
   Test Patterns*.{md,pdf}` (no hard-coded names), records SHA-256, byte/line
   counts, token estimate, heading distribution, artifact frequencies, and PDF
   page count (948) + text-extractability. Writes
   `.local/work/source-report.json`.
2. **Cleaner** (`clean.py`): six named, unit-tested rules applied
   deterministically: HTML-comment stripping, `<sup>` unwrapping,
   strikethrough restoration (`~~-~~`, `~~-o~~`, `~~I~~`, `~~—~~` → restored;
   genuine multi-word strikethrough preserved), **f-ligature joining for
   `fi`/`fl` only** (er/st/ds/ff are genuine word boundaries — "sniff test",
   "number of" must NOT be joined), heading bold stripping, `<br>`→newline,
   trailing-whitespace stripping, and removal of `www.it-ebooks.info`
   watermarks + `Chapter N …` page headers.
3. **Provenance**: per-clean-line map (`.local/work/line-map.jsonl`) recording
   source lines + applied transforms; no assumption of 1:1 correspondence.

**Key empirical finding:** 1667 `fi` + ~52 `fl` ligature splits are all
artifacts; 3458 `er`/`ff`/`st` splits are all genuine. Joining `er`/`ff`/`st`
would be a disaster, so they are explicitly excluded and guarded by tests.

**Outputs (`.local/work/`):**
- `source-report.json` (manifest + stats)
- `book.cleaned.md` (20798 → 19853 lines: 932 watermarks + 336 page headers
  removed; 1092 ligature joins; 119 sups; 3 stuck-hyphens; 1761 heading-bold
  stripped; 2014 comments; 3427 breaks)
- `line-map.jsonl` (19853 entries, 0 malformed)
- `cleanup-report.json`

**Determinism:** re-running `clean` produces byte-identical `book.cleaned.md`
and `line-map.jsonl`.

**Commit:** `eb7ad57`.

---

## M3 — Deterministic, catalog-driven chunking

**How:** `structure.py` reconstructs semantic units from the flattened Markdown
(chapters are `H5`; every entry and subsection is `H6`).

- **Chapter classification** (`_classify_chapter`): H5 titles map to
  `goal`/`principle`/`smell`/`pattern` chapters (via `CHAPTER_KINDS` +
  `SMELL_CATEGORIES`), `reference`/`narrative` chapters (via `REFERENCE_CHAPTERS`),
  with the rest treated as narrative.
- **Entity detection is catalog-driven** for smell & pattern chapters. Each such
  chapter opens with a `Patterns/Smells in This Chapter` table
  (`_collect_catalog` / `_parse_chapter_catalog`); we anchor exactly **one
  chunk per catalog entry** at its first `H6` occurrence. This suppresses
  false entities (descriptive intros, figure labels, repeated cross-references)
  and deduplicates within a chapter automatically.
- **Goal / principle chapters** (which have no catalogue table) use the
  `Goal:` / `Principle:` heading prefix to distinguish real entities from
  noise such as `"Tests Should …"`, `"Chapter N"`, `"What's Next?"`.
- **Reference / narrative / front-matter** chapters collapse to a single
  chapter-scale chunk.
- Smart-apostrophe normalisation (`'` → `'`) is applied in `_normalise_name` so
  keyword matching survives OCR/curly-quote variants.
- Each chunk carries a clean-line span and, via the provenance line map, the
  original Markdown line range + source SHA-256; `_collect_subsections`
  records the structural subsections (`How It Works`, `Variations`, …) within
  each entity.
- **Global ID dedup**: chunk IDs (`{kind}:{slug}`) are deduplicated across the
  whole book (first occurrence wins); duplicates are reported, not emitted.
- **Completeness checks**: catalog entries with no `H6` *anywhere* in the book
  are flagged; catalog entries that are H6s elsewhere are treated as
  cross-references (expected, not bugs).

**Outputs (`.local/work/`):**
- `chunk-manifest.jsonl` (119 records, each with `source_refs` provenance)
- `structure.json` (`chunk_count`, `by_kind`, `by_chapter_kind`,
  `completeness_problems`)

**Result:**
```
chunked 119 chunks ({'reference': 28, 'goal': 13, 'principle': 13,
                      'code': 5, 'behavior': 6, 'project': 4, 'pattern': 50})
completeness problems: []   (zero duplicates, zero genuine misses)
```
Counts match Meszaros: **50 patterns, 15 smells (5 code + 6 behavior + 4
project), 13 goals, 13 principles**, plus 28 reference/narrative chapters.

**Supporting change:** `clean.py` extended to strip italic heading emphasis
(`###### _Name_` → `###### Name`) in addition to bold. This is required for
catalog detection — the book marks its `Patterns/Smells in This Chapter`
catalog headings with italics, so without it the catalog table would never be
located.

**Verification:** `tests/unit/test_structure.py` (9 cases: slugify, heading
parsing, subsection detection, catalog-driven entity creation, subsection
recording, provenance ranges, source-ref records, no-duplicate-ids, and
unmatched-catalog-entry reporting) — all green.

**Quality gates:** ruff clean, mypy clean (1 source), **35 tests pass**.

**Commits:** M3 chunking on `main`; `clean.py` italic-heading fix on `main`.

---

## M4 — Schema validators + `validate-knowledge` CLI

**How:** Implemented the Stage-4 validator in `schemas.py` (the canonical
pydantic-model layer that mirrors `schemas/*.schema.json`), plus two new JSON
Schema artifacts and the CLI wiring already referenced by `cli.py`.

- **`ChunkRecord`** + **`StructureReport`** pydantic models enforcing the M3
  chunk-manifest record shape and the `structure.json` validity summary
  (`extra="forbid"`, `id` prefix patterns, clean-line bounds, source-ref
  presence/positivity, SHA-256 format).
- New JSON Schemas: `schemas/chunk-record.schema.json`,
  `schemas/structure-report.schema.json`.
- **`run_validate_knowledge()`** validates:
  1. `.local/work/chunk-manifest.jsonl` — one `ChunkRecord` per line;
  2. `.local/work/structure.json` — `StructureReport`;
  3. `knowledge/{book,graph,modern}/*.jsonl` — each record dispatched to its
     enforcing model by `id` prefix (`pattern:`/`smell:`/`goal:`/
     `principle:`/`relationship:`/`decision-rule:`/`modern:`).
  Missing artifacts are warnings (not fatal); schema failures are collected and
  the command exits non-zero on any error.
- Knowledge-model dispatch uses `get_args(RelationshipType)` (mypy-clean).

**Supporting tidy-up:** made `chunk.py` lint- and mypy-clean
(`dict[str, Any]`, dropped unused `SourceRef` import, unquoted `from __future__`
annotations).

**Verification:**
```
agentic-testcraft validate-knowledge
chunk-manifest.jsonl: 119/119 records valid
structure.json: valid
all knowledge artifacts valid
```

**Quality gates:** ruff clean, mypy clean (`schemas`, `structure`, `chunk`),
**43 tests pass**.

**Commit:** M4 schemas + validator on `main`.

---

## M5 — Extraction (native-agent)

**How:** `extract.py` with a provider abstraction (build-plan *Provider
abstraction*).  No LLM credentials are present in the environment, so the
``native-agent`` provider performs **deterministic, structural extraction**
directly from the cleaned book (the plan explicitly permits this: *"the
implementation agent may perform extraction natively in semantic batches, but
it must still write records through the same validators and provenance
system"*).

- For each knowledge chunk, read its provenance line span from
  `book.cleaned.md` and split it into `(heading, body)` segments (the first
  `######` is the entity title and is skipped).
- Map the book's canonical subsection headings onto schema fields verbatim —
  **no text is invented** (per the extraction prompt contract):
  - **patterns**: `problem` = the italic problem question `_…?_`; `intent`
    = the bold essence definition `**…**`; `solution` = the *How It Works*
    body; `context/forces/use_when/implementation_variations` from matching
    subsections.
  - **smells**: `summary` = the declarative "It is difficult…" problem
    sentence (an H6); `symptoms/impact/causes/detection_heuristics` from the
    matching subsection bullet lists (first occurrence only, so nested
    `Cause: …` sub-sections don't duplicate).
  - **goals**: `summary` = the intro paragraph.
  - **principles**: `statement` = the intro paragraph; `aliases` from an
    *Also known as:* line.
- Required fields fall back to the chunk's own intro prose or title (still
  source-faithful), never to model knowledge.
- Smell ids are remapped (`code:`/`behavior:`/`project:` → `smell:`) to match
  `smell.schema.json`.
- Output written to `knowledge/book/{patterns,smells,goals,principles}.jsonl`;
  every record is instantiated through its pydantic model (so invalid records
  can never be written) and re-checked by `validate-knowledge`.
- `openai`/`anthropic`/`google` providers are stubbed behind the same
  abstraction and raise if their API key env var is absent.

**Outputs (`knowledge/book/`):** `patterns.jsonl` (50), `smells.jsonl` (15),
`goals.jsonl` (13), `principles.jsonl` (13) = **91 records**, each carrying
`source_refs` back to the original Markdown.

**Verification:**
```
agentic-testcraft extract          -> extracted 91 knowledge records via native-agent
agentic-testcraft validate-knowledge
    goals.jsonl:       13/13 valid
    patterns.jsonl:   50/50 valid
    smells.jsonl:     15/15 valid
    principles.jsonl: 13/13 valid
all knowledge artifacts valid
```

**Quality gates:** ruff clean, mypy clean (`extract`, `schemas`, `structure`,
`chunk`), **55 tests pass**.

**Commit:** M5 extraction + provider abstraction on `main`.

---

## M6 — Relationship graph

**How:** `graph.py` builds a directed, deterministic knowledge graph purely
from the book's own *italic* cross-references (`_Name_`) — never fabricated.

- `build_name_index` indexes every knowledge record by its normalised name
  (plus plural/singular variants) → id, so duplicate-named entities resolve to
  a set (ambiguous → dropped, not guessed).
- For each knowledge chunk, the chunk's provenance line span is read from
  `book.cleaned.md`; `_ITALIC_RX` extracts italic spans, which `_resolve`
  maps to knowledge ids, **excluding the chunk's own id** (self-edges dropped).
- `_edge_kind` maps `(from_kind, to_kind, sentence)` → relationship using
  keyword context in the surrounding sentence:
  - **smell → pattern** = `refactors_to` (the smell's solution pattern).
  - **pattern → smell** = `prevents` (sentence contains prevent/avoid/eliminate)
    or `may_cause` otherwise.
  - **pattern → pattern** = `used_with` (explicitly co-mentioned).
  - **goal/principle → anything** = `supports` (a rule that references another
    entity supports/exemplifies it).
- `build_relationships` returns deduplicated `RelationshipRecord`s (keyed by
  `(from_id, rel, to_id)`), each tagged `explicit=True`, `origin="book"`, and
  carrying the originating `source_refs` back to the original Markdown.
- `build_graph` assembles a NetworkX `DiGraph`, runs the graph check
  (every id resolves to a known node; no self-loops; no duplicate edges; every
  record validates), then writes `knowledge/graph/{relationships.jsonl,graph.json}`
  (stats + adjacency).

**Outputs (`knowledge/graph/`):** `relationships.jsonl` (648 edges) +
`graph.json` (648 edges across 91 nodes, density 0.079, 22 SCCs, 4 isolated,
`self_loops=0`).

**Edge breakdown:** `used_with` 401, `may_cause` 75, `refactors_to` 71,
`supports` 80, `prevents` 21.

**Verification:**
```
agentic-testcraft build-graph
    graph built: 648 edges across 91 nodes ({'used_with': 401, 'refactors_to': 71,
    'prevents': 21, 'supports': 80, 'may_cause': 75}; 4 isolated) -> graph.json
agentic-testcraft validate-knowledge
    knowledge/graph/relationships.jsonl: 552/552 records valid
    all knowledge artifacts valid
```
(The `relationships.jsonl` count is the deduplicated edge count; graph.json
re-emitted after the pattern→smell edge-type fix.)

**Quality gates:** ruff clean, mypy clean (`graph`), **9 graph tests pass**
(`tests/unit/test_graph.py`, covering name indexing, plural resolution,
single/ambiguous/empty resolution, italic parsing, all five edge kinds, id
remapping from `code:`→`smell:`, self/excluded/ambiguous dropping).

**Commit:** M6 relationship graph on `main`.

> **M6 graph note:** `build_graph` uses `nx.MultiDiGraph` so parallel edges
> (the same node-pair related by distinct relationship types, e.g.
> `pattern → smell` and `pattern → principle`) are preserved. The first pass
> used a plain `DiGraph`, which collapsed parallel edges: `relationships.jsonl`
> had 660 distinct relationships while `graph.json` reported only 648 edges.

---

## M7 — Synthesis into operational decision rules

**How:** `synthesize.py` derives compact, operational `DecisionRuleRecord`s
deterministically from the structured knowledge (M5) + relationship graph (M6)
— **no LLM** is available in this environment, so synthesis is structural
rather than the plan's preferred large-context reasoning pass. Every rule's
`evidence_ids` point to the exact book records (and graph edges) it is grounded
in.

For each knowledge entity exactly one rule is derived:

- **pattern → `rule:<slug>`** (`strength=certain`): *trigger* = the problem;
  *default_action* = "Apply the X pattern…"; *evidence* = the pattern + the
  smells it addresses (`graph smell → pattern refactors_to`) + smells it
  prevents/may-causes (`graph pattern → smell`). *warnings* from `risks`.
 - **smell → `rule:smell-<slug>`** (`strength=warning`): *trigger* = the smell
  summary; *default_action* = "do not introduce / refactor toward the patterns
  that address it"; *evidence* = the smell + solution patterns from the graph.
- **principle → `rule:<slug>`** (`strength=certain`): *trigger* = the
  statement; *default_action* = the principle's `default_rule`; *evidence* =
  the principle + entities it supports + goals/principles that reference it.
- **goal → `rule:<slug>`** (`strength=default`): *trigger* = the summary;
  *default_action* = verify the goal is satisfied; *evidence* = the goal + what
  it supports; *warnings* = tensions, *agent_verification* = indicators.

Two higher-order rules are synthesized from the corpus as a whole:

- `rule:one-condition-per-test` — the semantic rule: *"Verify one condition per
  test" ≠ "one assertion per test"* (evidence = all principles).
- `rule:test-execution-workflow` — the 14-step execution strategy (evidence =
  all goals + principles).

A markdown companion (`knowledge/synthesized/testing-workflow.md`) records the
workflow + the semantic rule for human reading.

**Outputs (`knowledge/synthesized/`):** `decision-rules.jsonl` (93 rules) +
`testing-workflow.md`.

**Verification:**
```
agentic-testcraft synthesize
    synthesized 93 decision rules -> knowledge/synthesized/decision-rules.jsonl
agentic-testcraft validate-knowledge
    knowledge/synthesized/decision-rules.jsonl: 93/93 records valid
    all knowledge artifacts valid
```
(93 = 50 patterns + 15 smells + 13 principles + 13 goals + 2 workflow rules.)

**Quality gates:** ruff clean, mypy clean (`synthesize`, `schemas`),
**18 tests pass** (`tests/unit/test_synthesize.py` + `test_graph.py`);
full suite **77 tests pass**.

**Notes / limitations:**
- `validate-knowledge` was extended to also scan `knowledge/synthesized/`
  (dispatch by `rule:` id prefix) — fixes an earlier mismatch where the map
  keyed on `decision-rule:` but the schema + rule ids use `rule:`.
- Because no LLM is available, the per-topic markdown decision docs
  (boundary / verification / fixture / test-double / smell-review /
  testability-refactoring) are represented as the operational rule set + the
  workflow doc rather than long-form narrative; they remain candidates for an
  LLM-assisted expansion pass.

**Commit:** M7 synthesis on `main`.

---

## Repository policy — source publication & merge reconciliation

**Git merge reconciliation (between original `bc045ec` M6 and local amended
M6 + M7 work):** an in-progress merge (initiated by an upstream sync to
`origin/main = bc045ec`) left conflicts in `graph.py`, `schemas.py`, and
`build-report.md`. All three were resolved by keeping the local HEAD versions,
which are **strict supersets** of the remote M6:

- `graph.py`: local kept `nx.MultiDiGraph` (remote was the older `DiGraph`
  that collapsed parallel edges → 648 vs 660 relationships). Taking the local
  version preserved every remote code path and the required MultiGraph fix.
- `schemas.py`: local kept the M6 `_model_for_record`/`from_id` dispatch plus
  the M7 `rule:`-prefix dispatch and `knowledge_synthesized_dir` validation.
- `build-report.md`: remote contributed no tail content; local narrative (M6
  MultiGraph note + M7 section) retained as the single coherent narrative.

Verified post-resolution: `build-graph` → 660 edges, 0 graph-check problems;
`synthesize` → 93 rules; `validate-knowledge` → 119/119, 660/660, 93/93 valid.
Merge committed (`1ab36ed`); working tree clean; normal non-force-push history.

**Source-publication policy override:** the repository owner explicitly
authorized tracking the supplied PDF and Markdown of *xUnit Test Patterns* in
this repository as immutable inputs. `.gitignore` no longer ignores them; both
files are tracked (content unchanged); provenance/hash safeguards (SHA-256 in
`.local/work/source-report.json`, cleaner writes a separate `book.cleaned.md`)
are preserved. Docs (`NOTICE.md`, `CONTRIBUTING.md`, `source-methodology.md`,
`architecture.md`, `AGENTIC_TESTCRAFT_BUILD.md` §1.2 & Stage 19) updated so
none claim the sources "must never be committed"; the Stage 19 source-leak
validator now protects generated-knowledge concision + source immutability
rather than "source files are not tracked". Decision record:
`docs/decisions/source-publication.md`.

---

## M8a — Modernization: runtime & determinism

Implemented `modernize.py` (`run_modernization`, wired in `cli.py`) with the
`ModernizationRecord` model + field validators (authoritative URL citations,
`YYYY-MM-DD` review date) so `validate-knowledge` enforces them.

**M8a records (3), all sourced to primary/official docs fetched live:**

| id | topic | status | source |
|---|-------|--------|--------|
| `modern:async-test-support` | Async/await test execution | expanded | pytest-asyncio docs |
| `modern:deterministic-time` | Deterministic / virtual clocks | clarified | time-machine docs |
| `modern:flaky-as-fatal` | Flaky tests are fatal, not retried | expanded | Hypothesis flaky-docs |

Each record states the 2007 book position vs. the modern position, is grounded
in `affected_knowledge_ids`, and gives an `agent_rule_change`. Records write to
`knowledge/modern/{modernization.jsonl, current-testing-practices.md}` (both
gitignored, regenerable).

**Verification:**
```
agentic-testcraft modernize -> modernized 3 records
agentic-testcraft validate-knowledge
    knowledge/modern/modernization.jsonl: 3/3 records valid
    all knowledge artifacts valid
```

**Quality gates:** ruff clean, mypy clean (`modernize`, `schemas`);
**7 tests pass** (`tests/unit/test_modernize.py`).

**Commit:** M8a modernization (run-time & determinism).

## M8b — Modernization: modern integration / hermeticity

**Records (2), sourced to Testcontainers + pytest fixtures:**

| id | topic | status | sources |
|---|-------|--------|---------|
| `modern:disposable-integration-containers` | Per-test Docker containers (Testcontainers) | expanded | testcontainers-python README + pytest fixtures |
| `modern:hermetic-integration` | Function-scoped fixtures + guaranteed teardown | clarified | pytest fixtures |

**Verification:** `modernize` → 5 records; `validate-knowledge` → `modernization.jsonl: 5/5 valid`; 7 tests; ruff + mypy clean.

**Commit:** M8b modernization (integration / hermeticity).

---

## M8c — Modernization: test-effectiveness methods

**How:** Researched primary/official documentation for four practices absent from
the 2007 book — mutation testing (Mutmut), property-based testing (Hypothesis),
consumer-driven contract testing (Pact), and coverage-guided fuzzing (Atheris).
Appended 4 `modern:*` records to `src/agentic_testcraft/modernize.py`, each
citing an absolute `https://` source with a `2026-08-17` review date; re-ran the
pipeline and re-validated. Records are split into `_M8B` (integration, 2) and
`_M8C` (test-effectiveness, 4) lists in the source.

| id | topic | status | sources |
|---|---|---|---|
| `modern:mutation-testing` | Surviving mutants ⇒ missing assertions; mutmut | expanded | mutmut readthedocs |
| `modern:property-based-testing` | Hypothesis generates + shrinks inputs from invariants | expanded | hypothesis readthedocs |
| `modern:contract-testing` | Pact contracts replace brittle cross-service end-to-end tests | expanded | pact-python README + docs.pact.io |
| `modern:fuzz-testing` | Atheris coverage-guided fuzzing for parsers (libFuzzer) | expanded | atheris GitHub README |

**Verification:** `modernize` → 9 records; `validate-knowledge` →
`modernization.jsonl: 9/9 valid`; `test_modernize.py` 7/7; ruff + mypy clean.

**Commit:** M8c modernization (test-effectiveness: mutation, property-based, contract, fuzz).

---

## M8d — Modernization: service & browser testing

**How:** Researched primary/official documentation for two UI/service testing
domains with no 2007 equivalent — Playwright (cross-browser code-first
automation) and pytest-httpserver (in-process HTTP server per test). Appended 2
`modern:*` records to `src/agentic_testcraft/modernize.py` in a new `_M8D` list,
each citing an absolute `https://` source with a `2026-08-17` review date.

| id | topic | status | sources |
|---|---|---|---|
| `modern:browser-ui-assertions` | Playwright auto-waiting, selectors, network mocking | expanded | playwright-python GitHub |
| `modern:service-level-expectations` | pytest-httpserver in-process HTTP server per test | expanded | pytest-httpserver readthedocs |

**Verification:** `modernize` → 11 records; `validate-knowledge` →
`modernization.jsonl: 11/11 valid`; `test_modernize.py` 7/7; ruff + mypy clean.

**Commit:** M8d modernization (service & browser testing: Playwright, pytest-httpserver).

---

## M8e — Modernization: CI & execution

**How:** Researched primary/official documentation for parallel test execution
and monorepo-scale suite partitioning — pytest-xdist (`-n auto`), GitHub
`actions/setup-python` (Python install + pip caching), and pytest-split
(`--splits/--group` duration-balanced shards). Appended 2 `modern:*` records in a
new `_M8E` list, each citing an absolute `https://` source with a
`2026-08-17` review date.

| id | topic | status | sources |
|---|---|---|---|
| `modern:ci-parallel-execution` | `pytest -n auto` + setup-python/caching in CI | expanded | pytest-xdist + setup-python README |
| `modern:monorepo-suite-partitioning` | pytest-split `--splits/--group` shards across CI jobs | expanded | pytest-split docs |

**Verification:** `modernize` → 13 records; `validate-knowledge` →
`modernization.jsonl: 13/13 valid`; `test_modernize.py` 7/7; ruff + mypy clean
(`modernize.py` only).

**Commit:** M8e modernization (CI & execution: parallelism, monorepo suite partitioning).

---

## M8 — Summary (a–f)

**Records:** 17 `modern:*` records across 6 categories
(Runtime & determinism, Modern integration, Test-effectiveness methods,
Snapshot & boundary testing, Service & browser testing, CI and execution). Each
cites an authoritative `https://` source with a `2026-08-17` review date and
links to real book `id`s, and carries an `agent_rule_change` the future skill
can adopt verbatim.

**Addendum (M8f research):** four practice topics with no existing record were
researched against official sources and added: randomized test ordering
(`pytest-randomly`), snapshot/golden-master assertions (`syrupy`), hermetic HTTP
service boundaries (`httpx MockTransport`), and cross-version/cross-platform
matrix gating (`tox` + GitHub Actions `setup-python`). Their `affected`
knowledge `id`s are validated to resolve. Two topics were reviewed and
intentionally excluded (flaky-test retries — rejected by `modern:flaky-as-fatal`;
eventual-consistency polling — a behavioral pattern, covered by
`modern:browser-ui-assertions` auto-waiting) and three more folded into existing
records. See `docs/decisions/modernization-topic-coverage.md`.

**Closing artifacts:**
- `docs/modernization-methodology.md` — M8 discipline, validation pipeline,
  book-vs-modern boundary, updated category table.
- `docs/decisions/skill-compatibility.md` — cross-check of every M8 record
  against skill-spec R1–R8 and acceptance criterion 6.13 (evidence mapping).
  R7 (Effectiveness validation) is the strongest win (mutation/property/contract/
  fuzz); no conflicts found; gaps flagged for M8f+/M9.
- `docs/decisions/modernization-topic-coverage.md` — M8f topic audit with
  add/review-exclude/fold/exclude rationale.

**Full audit (M8f):** all knowledge artifacts valid (119 chunks, 660 graph
edges, 17 modern, 93 rules, 91 book records + 4 narrative rules); all
cross-record references resolve; 108 tests pass; `modernize.py` +
`test_modernize.py` clean under ruff + mypy. Pre-existing lint/mypy findings
in untouched modules (`clean.py`, `provenance.py`, `source_inspect.py`,
`cli.py`, `test_clean.py`, `test_provenance.py`) are out of scope for this
milestone.

**Commit:** M8 closing docs (modernization-methodology.md, decisions/skill-compatibility.md, decisions/modernization-topic-coverage.md).

---

## Milestone M9 — Author & package the production Agent Skill

Authored `skill/agentic-testcraft/SKILL.md` (concise, < 400 lines, 12-step runtime
workflow + flakiness guardrail) plus `skill/agentic-testcraft/references/` (11
catalog docs + `ecosystems/README.md`) per progressive disclosure (§Stage 9).

**M9 conformance update (spec research, 2026-08-17):** Researched the canonical
Agent Skills spec (https://agentskills.io) and the Claude Code frontmatter
reference (https://docs.anthropic.com/en/docs/claude-code/skills). The spec
requires `name` + `description` at minimum; `compatibility` is an optional spec
field. `SKILL.md` frontmatter now carries `name`, `description`, and
`compatibility`; `version` is `1.0.0rc1` and `status` is `release-candidate`
(the skill is functional but not yet eval-validated — M10); `title`/`version`/
`status` remain project-internal fields. `skill_validate.REQUIRED_FRONT_MATTER`
now enforces `name`+`description`, and `VALID_STATUS` accepts
`release-candidate`. Also closed a real gap: **R6 (testability refactoring) was
never cited in `SKILL.md`** — it is now referenced at step 3 via
`references/testability.md`, guarded by `test_committed_skill_cites_every_rule_and_step`.

Wrote the Stage-9 tooling in `src/agentic_testcraft/skill_validate.py`
(`run_validate_skill` → `load_front_matter` + `_check_skeleton`: required
front-matter keys/status, ≤400 lines, no TODO/FIXME placeholders, no verbatim
book excerpt, unique R1–R8 / step numbers, resolvable `references/` links each
carrying an Evidence line, evidence-base file exists) and
`src/agentic_testcraft/bundle.py` (`run_bundle` → `skill/agentic-testcraft/.skill-manifest.json`
with file list + sha256 + meta, then re-runs the Stage-9 gate). Wired both as
`agent` subcommands (`validate-skill`, `bundle`) in `cli.py`; removed the
now-unused `Optional` import and switched `extract`/`eval` annotations to
`str | None` (and added `compatibility` to the manifest).

Built `knowledge/synthesized/skill-traceability.json` (21 skill-rule mappings:
SKILL steps 1–12, R1–R8, and the flakiness guardrail), each linking to a
`rule:`/`pattern:`/`smell:`/`principle:`/`goal:` ID and a `modern:` ID. The four
M8f modern records (random-test-ordering, snapshot-golden, api-boundary-mocking,
cross-version-matrix) are wired into the SKILL:1/3/4/8/9/11 mappings. Committed
the skill package incl. its manifest (deterministic, regenerable lockfile-style
artifact, not gitignored; the regenerable `*.jsonl` knowledge outputs remain
ignored per `.gitignore`).

**Evidence:** run on the real skill tree — `validate-skill` → `ok: skill valid
(Agentic Testcraft v1.0.0rc1 release-candidate); 0 warning(s)`; `bundle` →
manifest of 13 files.

**New tests:** `tests/unit/test_skill_validate.py` (17 cases incl. missing-front-matter
keys for the new `name`/`description`, invalid status, `release-candidate` valid,
broken links, duplicate rules, verbatim-excerpt, >400 lines, + the committed-skill
R1–R8/step-1..12 coverage regression guard) and `tests/unit/test_bundle.py`
(2 cases: manifest writes + validates; validation failure propagates).

**Quality gates:** ruff clean; mypy clean on new/touched src files
(`skill_validate.py`, `bundle.py`); `cli.py` introduces no new mypy error (only the
pre-existing `evals` import-untyped note, M10). Full suite: **112 tests pass**
(ruff-randomized order). Pre-existing strict-mypy noise in untouched test/source
modules is out of scope.

**Commit:** M9 conformance (SKILL.md frontmatter + R6 citation, skill_validate,
bundle, traceability, tests, skill-compatibility.md).

---

## Pre-M10 semantic readiness audit

Before opening M10 (eval harness + baseline), a source-faithfulness pass
verifies the knowledge pipeline that *feeds* the skill, so the skill is not
evaluated on fabricated or stale grounding.

### M5 extraction audit (2nd-pass)

- `src/agentic_testcraft/extract.py` now classifies each book record with a
  `Confidence` (certain / warning / historical) and emits
  `knowledge/book/extraction-coverage-report.json` (real field-coverage: e.g.
  `use_when` 40, `intent` 31, `implementation_variations` 49, `refactorings`
  37; `benefits`/`costs`/`risks` intentionally null because the book's Pattern
  Form has no such subsections — documented, not fabricated).
- 4 grounded narrative rules emitted to `knowledge/book/narrative-rules.jsonl`
  (from Ch.3 / Ch.4 / Philosophy), validated by `NarrativeRecord`
  (`schemas.py`) + `schemas/narrative.schema.json`.
- Low-confidence / ambiguous record lists published in
  `docs/methodology/extraction-audit.md` (Stage 5 second-pass source-faithfulness
  review).

### M6 / graph

- `knowledge/graph/relationships.jsonl`: 660 edges; reference resolution now
  rejects unresolved `evidence_ids` / `affected_knowledge_ids` cross-record refs
  (`validate-knowledge` → "all cross-record refs resolve").

### M7 synthesis

- `knowledge/synthesized/decision-rules.jsonl`: 93 rules;
  `validate-knowledge` enforces 93/93.

### M8 modernization

- 17 `modern:*` records (13 + M8f addendum), each with absolute-URL
  `official_sources` + `2026-08-17` review date, validated end-to-end.
  `docs/decisions/modernization-topic-coverage.md` records the add /
  review-exclude / fold / exclude decisions.

### M9 skill package

- `SKILL.md` v1.0.0rc1 `release-candidate`, spec-conformant frontmatter
  (`name`/`description` required; `compatibility` optional); R1–R8 all cited;
  13 files in `.skill-manifest.json`; `validate-skill` + `bundle` pass.

**Gate:** ruff clean (touched files); mypy clean on touched `src/`; **112 tests
pass**; all `knowledge/` artifacts valid; all cross-record references resolve;
no verbatim book excerpts in the skill. Pre-M10 status: **ready to open M10.**


