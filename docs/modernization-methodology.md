# M8 Modernization Methodology

How the "transform the book into a framework-independent Agent Skill" effort
modernizes the source-derived `knowledge/` into guidance that is usable by a
coding agent today.

## Discipline

- **No LLM is available in this environment**, so modernization is produced
  from direct research of authoritative primary/official documentation only
  (Read the Docs, GitHub READMEs, official docs sites, PyPI metadata).
- Each practice is captured as a compact `ModernizationRecord` (`schemas.py`)
  that contrasts the **book position** (what 2007 says) with the **modern
  position** (what current tooling says), cites one or more
  `official_sources` (absolute `https://` URLs), states a `status`
  (`unchanged`/`clarified`/`expanded`/`narrowed`/`superseded`/`historical`), a
  `rationale`, the real `affected_knowledge_ids` (book `id`s from M5), and an
  optional `agent_rule_change`.
- Every record carries the review date (`REVIEW_DATE`, `YYYY-MM-DD`) recorded in
  the artifact so staleness is detectable.

## Validation pipeline (fail fast)

1. Each record is constructed through the `ModernizationRecord` pydantic model
  (`modernize._rec`), which enforces absolute-URL sources and `YYYY-MM-DD`
  review dates via `field_validator`s.
2. `run_modernization` re-validates every record before writing
  `knowledge/modern/modernization.jsonl` and the markdown digest
  `knowledge/modern/current-testing-practices.md`.
3. `validate-knowledge` re-checks the written JSONL end-to-end.
4. `tests/unit/test_modernize.py` enforces uniqueness, id/URL/date format, and
  the validator rejection paths.

## Source provenance & safety

- The original PDF + Markdown sources are tracked as immutable inputs (see
  `docs/decisions/source-publication.md`). The cleaner writes a *separate*
  `book.cleaned.md`; it never overwrites the sources. Each book knowledge record
  carries a `source_refs[].file_sha256` pinning the exact source bytes.
- Modern records cite **official** documentation by URL; the URL + review date
  make a modern claim auditable and replaceable. Generated `knowledge/` is
  git-ignored and fully regenerable from committed source (`clean → extract →
  graph → synthesize → modernize`).

## Organization

Records are grouped by *category* for the digest:

| Category | M8 records |
|---|---|
| Runtime and determinism | async/await test execution (pytest-asyncio / IsolatedAsyncioTestCase), deterministic time (time-machine), flaky tests treated as fatal (Hypothesis), random test ordering & per-test seeds (pytest-randomly) |
| Modern integration | disposable integration dependencies (Testcontainers), hermetic function-scoped fixtures |
| Test-effectiveness methods | mutation testing (mutmut), property-based testing (Hypothesis), consumer-driven contract testing (Pact), coverage-guided fuzz testing (atheris) |
| Snapshot & boundary testing | snapshot/golden-master assertions (syrupy), hermetic HTTP service boundary testing (httpx MockTransport) |
| Service & browser testing | code-first browser automation (Playwright), in-process HTTP server (pytest-httpserver) |
| CI and execution | parallel execution (`-n auto`, pytest-xdist), monorepo suite partitioning (`pytest-split`), cross-version/cross-platform matrix (tox + GitHub Actions) |

## Book-vs-modern boundary

Book-derived principles remain distinguishable in the final knowledge graph via
the `origin` field (`"book"` vs `"modern"`). A `modern:*` record is a
*clarification/expansion* of — not a replacement for — a book principle: it
tells the agent which 2007 guidance is still valid, which is narrowed by newer
tooling, and which is superseded. The compiled skill consumes the synthesized
`rule:`-prefixed decision rules and may reference a modernizing record as
evidence.
