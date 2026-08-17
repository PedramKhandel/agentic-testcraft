# Decision: Authorized publication of source book files

| Field | Value |
|-------|-------|
| Status | **Accepted** (owner-authorized) |
| Applies to | this repository only (`agentic-testcraft`) |
| Decisions | `docs/decisions/` |

## Context

The build plan (`AGENTIC_TESTCRAFT_BUILD.md`, section 1.2 "Public-repository
safety") defaults to a conservative posture: the copyrighted source book
(*xUnit Test Patterns: Refactoring Test Code*, Gerard Meszaros, 2007) should
**not** be committed to a public repository, and the source files should be
gitignored and supplied locally by the operator.

This default exists to avoid redistributing copyrighted material without
explicit redistribution rights.

## Decision

The repository owner has **explicitly confirmed** that they have permission to
publish and keep the supplied PDF and Markdown editions of the source book
**in this Git repository**, and that their presence here is intentional and
authorized.

Accordingly, in **this repository only**:

- the source PDF and Markdown are **tracked in version control**;
- they are treated as **immutable inputs** (never modified in place); and
- the conservative "do not commit the source book" default from the build plan
  is **superseded** by this explicit, repository-specific authorization.

## Consequences

- `.gitignore` no longer ignores `xUnit Test Patterns*.pdf` / `*.md` at the repo
  root.
- The files are `git add`-ed and committed as immutable reference inputs.
- `NOTICE.md`, `CONTRIBUTING.md`, `docs/source-methodology.md`,
  `docs/architecture.md`, and the relevant sections of
  `AGENTIC_TESTCRAFT_BUILD.md` (1.2 and Stage 19) are updated so they no
  longer claim the source files must never be committed.
- All other public-repository safety rules — **do not commit long verbatim
  extracts**, **do not reconstruct the book through chunk files**, and the
  Stage 19 source-leak/prevention checks over **generated knowledge** — remain
  in force.
- Provenance safeguards are preserved: the source is still hashed
  (`source-report.json`), the cleaner still writes a separate
  `book.cleaned.md` (never overwriting the source), and `source_refs` still
  point generated knowledge back to original source lines.

## Non-authoritative scope

This decision does **not** grant, assert, or document any rights to the book.
The rights holder retains all rights to the underlying work. Repository
artifacts (cleaned text, structured knowledge, decision rules, the final Agent
Skill) remain transformed knowledge tooling, not substitutes for the book.

Per the owner's instruction, no licensing terms, license numbers, rights-holder
statements, or legal claims beyond what the owner stated have been invented or
recorded here.
