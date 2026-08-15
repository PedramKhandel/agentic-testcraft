"""Command-line interface for the agentic-testcraft pipeline.

Commands are organised by the build-plan stages.  Each command is a thin
delegate to the corresponding stage module so that the CLI stays a stable
entry point while internals evolve.
"""
from __future__ import annotations

from typing import Optional

import typer

app = typer.Typer(
    name="agentic-testcraft",
    help=(
        "Build and validate the Agentic Testcraft skill: inspect sources, "
        "clean, split, extract structured knowledge, build a relationship graph, "
        "synthesize decision rules, modernize, validate the final skill, and run evals."
    ),
    no_args_is_help=True,
    add_completion=False,
)


def _err(msg: str, code: int = 1) -> None:
    import sys

    sys.stderr.write(f"error: {msg}\n")
    raise typer.Exit(code)


@app.command()
def inspect_sources() -> None:
    """Phase 0/M2: discover source files, compute hashes, emit a source report."""
    from .source_inspect import run_inspection

    run_inspection()


@app.command()
def clean() -> None:
    """Stage 2: run the deterministic Markdown cleaner with provenance maps."""
    from .clean import run_clean

    run_clean()


@app.command()
def split() -> None:
    """Stage 3: split cleaned book into semantic chunks."""
    from .structure import run_split

    run_split()


@app.command()
def validate_knowledge() -> None:
    """Stage 4/5: validate knowledge artifacts against schemas."""
    from .schemas import run_validate_knowledge

    run_validate_knowledge()


@app.command()
def extract(
    provider: str = typer.Option("native-agent", "--provider", "-p"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
) -> None:
    """Stage 5: extract structured knowledge from book chunks."""
    from .extract import run_extraction

    run_extraction(provider=provider, model=model)


@app.command()
def build_graph() -> None:
    """Stage 6: build the deterministic + semantic relationship graph."""
    from .graph import run_build_graph

    run_build_graph()


@app.command()
def synthesize() -> None:
    """Stage 7: synthesize structured knowledge into operational decision rules."""
    from .synthesize import run_synthesis

    run_synthesis()


@app.command()
def modernize() -> None:
    """Stage 8: modernize source-derived guidance with official sources."""
    from .modernize import run_modernization

    run_modernization()


@app.command(name="validate-skill")
def validate_skill() -> None:
    """Stage 9: static validate the final Agent Skill."""
    from .skill_validate import run_validate_skill

    run_validate_skill()


@app.command()
def eval(
    name: Optional[str] = typer.Argument(None, help="Case name; all if omitted"),
) -> None:
    """Stage 10+: run evaluations."""
    from .evals import run_evals

    run_evals(name=name)


if __name__ == "__main__":
    app()
