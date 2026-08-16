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
