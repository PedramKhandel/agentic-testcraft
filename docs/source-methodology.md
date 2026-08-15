# Source-handling methodology

This document describes how the copyrighted source book
(*xUnit Test Patterns*, Gerard Meszaros, 2007) is handled locally and turned
into provenance-linked, paraphrased knowledge. **No part of the book is
redistributed by this repository.**

## Immutable inputs

The PDF and the converted Markdown live at the repository root. They are
treated as **immutable inputs**:

- their SHA-256 hashes are recorded in `.local/work/source-report.json`;
- they are listed in `.gitignore` and are never committed;
- the cleaner writes a *new* `book.cleaned.md`; it never overwrites the source.

## Discovery

`src/agentic_testcraft/source_inspect.py` discovers the inputs by globbing
`xUnit Test Patterns*.md` / `*.pdf` at the repo root (no hard-coded names),
then records filename, byte size, SHA-256, line count, approximate token count,
heading distribution, and artifact frequencies. The PDF is used only as a
reference: page count, text-extractability check, and spot verification of
suspect conversions.

## Cleaning (Stage 2)

`src/agentic_testcraft/clean.py` applies a small set of **deterministic,
named, unit-tested** rules. Nothing here is LLM-driven. Each rule has a name,
rationale, and synthetic-snippet tests under `tests/unit/test_clean.py`.

| Rule | Applies to | Rationale |
|------|-----------|-----------|
| `strip_html_comment` | `<!-- ... -->` | Extraction comments carry no semantic content. |
| `unwrap_sup` | `<sup>...</sup>` | Restore superscripted text (e.g. title) inline. |
| `remove_strikethrough_artifacts` | `~~-~~`, `~~I~~`, `~~-o~~`, `~~—~~` | PDF struck marks restored; the 2-char hyphen+letter form is rejoined between words. Genuine multi-word strikethrough is preserved. |
| `join_f_ligatures` | `[a-z]{2,}fi ` and `[a-z]{2+}fl ` | f-ligature word splits (e.g. "specifi cation"). **Only** `fi`/`fl` are joined: `ff`, `er`, `st`, `ds`, `ft` are genuine word boundaries ("sniff test", "number of") and must not be joined. |
| `strip_heading_bold` | `###### **Name**` | Bold is redundant inside a heading. |
| `strip_trailing_whitespace` | trailing spaces | Cosmetic normalisation. |
| `convert_break` | `<br>` | Convert HTML breaks to newlines (preserves figure text). |
| (removal) | `www.it-ebooks.info`, `Chapter N …` headers | Page-level watermark/header lines removed. |

### Why only `fi`/`fl`?

Empirical analysis of the source showed:
- `fi` splits: 1667 (all artifacts: "specification", "verification", …)
- `fl` splits: ~52 (all artifacts: "reflection", "conflict", "influence", …)
- `ff` / `er` / `st` splits: 3458+ (all genuine word boundaries: "sniff test",
  "number of", "test suite"). Joining these would be a **disaster**, so they
  are deliberately excluded.

### Picture / figure handling

Figure text wrapped in `<!-- Start of picture text -->` … `<!-- End of picture text -->`
is preserved (comments are stripped, `<br>` becomes newlines) because diagrams
encode relationships used by extraction.

## Provenance tracking

Cleaning produces a **line-level provenance map** (`.local/work/line-map.jsonl`):

```json
{"clean_line": 900, "source_lines": [1044], "transformations": ["join_f_ligatures"]}
```

Because `<br>` splitting can make one source line produce several clean lines,
entries may list multiple source lines or several clean lines may share a
source line. There is deliberately **no assumption of 1:1 correspondence**.

## Semantic splitting (Stage 3)

Splitting is by **concept**, not token count. The book is split on its heading
hierarchy:

- `H5` headings delineate major chapters/sections (e.g. *Fixture Setup Patterns*).
- `H6` headings delineate individual patterns/smells/Goals and their
  subsections (`How It Works`, `Symptoms`, `When to Use`, …).

An entry boundary is detected by matching a heading against the chapter's
catalog of names; subsection keywords (`Variation:`, `Example:`, `How It
Works`, `Symptoms`, …) belong to the current entry. Each chunk carries its
source range (clean + original Markdown lines and PDF page spans where
mappable).

## Extraction constraints (Stage 5)

1. Extract **only** what the supplied source supports — never general model
   knowledge.
2. Preserve the author's terminology where semantically important.
3. Paraphrase instead of copying long passages.
4. Do **not** modernize while extracting (modernization is Stage 8).
5. Do **not** "improve" or "correct" the author's advice.
6. Distinguish explicit claims from cautious inference.
7. Attach source-range IDs to every record.
8. Emit only schema-constrained JSONL.

## Source-leak prevention (Stage 19)

A validator checks that no tracked file reproduces long runs from the
gitignored source and that the source files themselves are not tracked.
