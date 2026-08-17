"""Stage 9: static validation of the production Agent Skill tree.

Runs the acceptance-criterion checks from AGENTIC_TESTCRAFT_BUILD.md ("Skill
validation") against the committed skill at `settings.paths.skill_dir`. Exits
non-zero if any check fails, so it can serve as a Stage-9 CI gate.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import typer

from .config import load_settings

REQUIRED_FRONT_MATTER: set[str] = {"title", "name", "description", "version", "status", "evidence_base"}
VALID_STATUS: set[str] = {"wip", "draft", "stable", "release-candidate"}
MAX_SKILL_LINES = 400
PLACEHOLDER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)
BOOK_QUOTE_RE = re.compile(
    r"bug repellent that keeps nasty little bugs|"
    r"we are running all the tests before every check-in|"
    r"xunit test patterns: refactoring test code",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"\[[^\]]*\]\((references/[^)\s]+(?:\.md)?)\)", re.MULTILINE)
FRONT_MATTER_RE = re.compile(r"^-{3}\s*\n(.*?)\n-{3}\s*\n", re.S)


class SkillValidationError(Exception):
    """Raised when the skill tree fails a Stage-9 check."""


def load_front_matter(text: str) -> dict[str, str]:
    """Parse the simple scalar YAML front matter this project emits."""
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip("'\"")
    return out


def _check_skeleton(
    text: str, skill_md: Path, skill_dir: Path, errors: list[str], warnings: list[str]
) -> dict[str, str]:
    fm = load_front_matter(text)
    if not fm:
        errors.append("SKILL.md: missing YAML front matter")
    else:
        missing = REQUIRED_FRONT_MATTER - set(fm)
        if missing:
            errors.append(f"SKILL.md: front matter missing keys: {sorted(missing)}")
        if "status" in fm and fm["status"] not in VALID_STATUS:
            errors.append(f"SKILL.md: invalid status {fm['status']!r}")
        if "evidence_base" in fm and fm["evidence_base"]:
            evidence_path = skill_dir.parent.parent / fm["evidence_base"]
            if not evidence_path.is_file():
                errors.append(
                    f"SKILL.md: evidence_base file not found: {fm['evidence_base']}"
                )

    # Size cap (< 400 lines).
    lines = text.count("\n") + 1
    if lines > MAX_SKILL_LINES:
        errors.append(f"SKILL.md: too large ({lines} lines > {MAX_SKILL_LINES})")

    # No stale placeholders.
    if PLACEHOLDER_RE.search(text):
        errors.append("SKILL.md: stale placeholder (TODO/FIXME/XXX/HACK)")

    # No verbatim book excerpt in the core file.
    if BOOK_QUOTE_RE.search(text):
        errors.append("SKILL.md: appears to contain a verbatim book excerpt")

    # Unique rule ids (R1..R8 and steps 1..12 each once).
    for label in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"):
        if text.count(f"### {label} ") > 1:
            errors.append(f"SKILL.md: duplicate rule {label}")
    for n in range(1, 13):
        if text.count(f"### {n}.") > 1:
            errors.append(f"SKILL.md: duplicate step {n}")

    # References resolve; each reference doc is non-empty and cites evidence.
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        errors.append("missing references/ directory")
    else:
        ref_docs = sorted(p for p in refs_dir.rglob("*.md"))
        if not ref_docs:
            errors.append("references/ directory is empty")
        for rd in ref_docs:
            content = rd.read_text(encoding="utf-8")
            if not content.strip():
                errors.append(f"empty reference doc: {rd.relative_to(skill_dir)}")
            if "evidence" not in content.lower():
                warnings.append(f"reference doc without Evidence line: {rd.relative_to(skill_dir)}")
        for m in LINK_RE.finditer(text):
            target = skill_md.parent / m.group(1)
            if not target.is_file():
                errors.append(f"SKILL.md: broken link -> {m.group(1)}")

    return fm


def run_validate_skill(skill_dir: Path | None = None) -> dict[str, Any]:
    """Validate the Agent Skill tree. Raises SkillValidationError on failure."""
    settings = load_settings()
    skill_dir = Path(skill_dir) if skill_dir else settings.paths.skill_dir
    errors: list[str] = []
    warnings: list[str] = []
    fm: dict[str, str] = {}

    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        fm = _check_skeleton(text, skill_md, skill_dir, errors, warnings)
    else:
        errors.append(f"missing {skill_dir / 'SKILL.md'}")

    report = {
        "skill_dir": str(skill_dir),
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
        "title": fm.get("title"),
        "version": fm.get("version"),
        "status": fm.get("status"),
    }
    if errors:
        raise SkillValidationError(
            "skill validation failed:\n  - " + "\n  - ".join(errors)
        )
    return report


def main() -> None:
    try:
        report = run_validate_skill()
    except SkillValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1) from None
    else:
        print(
            f"ok: skill valid (title={report['title']}, version={report['version']}, "
            f"status={report['status']}); {len(report['warnings'])} warning(s)"
        )


if __name__ == "__main__":
    main()
