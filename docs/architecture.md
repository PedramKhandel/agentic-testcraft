# Architecture

A reference for how `agentic_testcraft` is structured, why, and what each stage
owns. Read top-to-bottom to understand data flow; the stage → module mapping
below lets you jump to the right code.

## Stages × modules

| Stage | Goal | Module(s) | Artifact (regenerated) |
|---|---|---|---|
| M0 | Bootstrap, tooling | `cli`, `config`, `provenance`, `schemas` | — |
| M1 | Skill spec | `docs/skill-spec.md` | — |
| M2 | Clean + provenance | `clean.py`, `source_inspect.py` | `.local/work/{book.cleaned.md, line-map.jsonl, *-report.json}` |
| M3 | Chunk | `structure.py`, `chunk.py` | `.local/work/chunk-manifest.jsonl`, `.local/work/structure.json` |
| M4 | Validate | `schemas.py` + `schemas/*.schema.json` | — |
| M5 | Extract | `extract.py` | `knowledge/book/*.jsonl` |
| M6 | Relate | `graph.py` | `knowledge/graph/{relationships.jsonl,graph.json}` |
| M7 | Synthesize | `synthesize.py` (planned) | `knowledge/modern/*.jsonl` |
| M8 | Modernize | `modernize.py` (planned) | `docs/modernization/*.md` |
| M9 | Package | `bundle.py` (planned) | dist artifact |
| M10 | Run | `run_skill.py` (planned) | — |

## Data flow

```
book.md / book.pdf  --(clean.py)-->  book.cleaned.md  (1:1 line map)
                              |
                              v
                  (structure.py)  -->  chunk-manifest.jsonl  (119 chunks)
                  (validate)        -->  structure.json
                              |
                              v
                  (extract.py)      -->  knowledge/book/*.jsonl   (91 records)
                              |
                              v
                  (graph.py)        -->  knowledge/graph/graph.json
                                            |
                                            +-- relationships.jsonl (648 edges)
                                            +-- graph.json (DiGraph + stats)
```

Every record anywhere carries `source_refs` (file_sha256 + markdown_start/end
line) so output is always traceable to its origin line in `book.cleaned.md`.

## Design rules

1. **No fabrication.** The `native-agent` extractor maps canonical subsection
   headings onto schema fields verbatim; no field is invented. If a section is
   absent it falls back to the chunk intro prose, still source-faithful.
2. **Deterministic.** All stages are pure functions of the cleaned book; no
   LLM randomness. Re-running `clean → split → extract → build-graph`
   reproduces identical artifacts (up to stable hash/uid prefixes).
3. **Validate on write.** Records are built through pydantic models and
   re-checked by `validate-knowledge`; invalid records cannot be written.
4. **Provenance everywhere.** Every artifact is traceable to original Markdown
   lines via `line-map.jsonl` and `source_refs`.
5. **Generated intermediates are gitignored.** `.local/`, `knowledge/`, and
   the derived `book.cleaned.md` are never committed (all regenerable from the
   tracked source). The source book files and `.schema.json` definitions are
   tracked (the book as immutable, owner-authorized inputs).

## Why a graph

M6 exists as a distinct stage because *Meszaros defines relationships by
name*: smells link to their "Solution Patterns", patterns warn about smells
they "may cause", and principles/goals are invoked from concrete examples.
A directed, source-explicit graph lets downstream stages (decision-rule
synthesis in M7, modernization in M8) ask *which patterns address a smell?*
or *which smells does this pattern risk?* without re-parsing the prose.

## Key identifiers

- Chunk ids: `pattern:<slug>`, `smell:<slug>`, `goal:<slug>`, `principle:<slug>`,
  `reference:<slug>` (smell-category chunks are remapped from `code:` /
  `behavior:` / `project:` to `smell:` so chunk ids match knowledge ids).
- Edge types: `refactors_to`, `prevents`, `may_cause`, `used_with`, `supports`.

## Running the pipeline

```
agentic-testcraft clean          # M2
agentic-testcraft split          # M3
agentic-testcraft validate-knowledge   # M4
agentic-testcraft extract        # M5
agentic-testcraft build-graph    # M6
```

Each command is idempotent and prints a one-line status summary.
