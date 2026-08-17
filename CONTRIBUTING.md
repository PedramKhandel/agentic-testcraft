# Contributing to Agentic Testcraft

Thank you for your interest. This repository builds a coding-agent skill for
better automated testing from a structured study of *xUnit Test Patterns*
(Gerard Meszaros, 2007).

## Developing locally

```bash
uv sync --extra dev
uv run python -m agentic_testcraft.cli --help
uv run pytest
```

## What belongs here

- Structured, paraphrased, provenance-linked knowledge artifacts.
- Deterministic pipeline tooling.
- The final Agent Skill (`skill/agentic-testcraft/`).
- Evaluation harnesses and regression cases.
- Documentation.

## What does NOT belong here

- The copyrighted book PDF and Markdown are tracked only as immutable,
  owner-authorized reference inputs; do not modify them or reconstruct the
  book from chunks.
- Long verbatim quotes from the book.
- API keys or other secrets.

## Commit policy

Follow the conventions in `AGENTIC_TESTCRAFT_BUILD.md`. Commit at quality gates.
Run the full source-leak validator before any release commit.
