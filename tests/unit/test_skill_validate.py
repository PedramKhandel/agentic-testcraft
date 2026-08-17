"""Unit tests for Stage 9 skill validation."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_testcraft.skill_validate import (
    SkillValidationError,
    load_front_matter,
    run_validate_skill,
)

MINIMAL_FRONT = """\
---
title: Demo Skill
name: demo-skill
description: A demo skill for validation tests.
version: 1.0.0
status: stable
evidence_base: knowledge/synthesized/skill-traceability.json
---
"""


def _write_skill(
    tmp_path: Path, body: str, refs: dict[str, str] | None = None, create_evidence: bool = True
) -> Path:
    skill = tmp_path / "skill"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    if refs:
        for name, content in refs.items():
            (skill / "references" / name).write_text(content, encoding="utf-8")
    if create_evidence:
        fm = load_front_matter(body)
        eb = fm.get("evidence_base")
        if eb:
            target = skill.parent.parent / eb
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}", encoding="utf-8")
    return skill


def test_load_front_matter_roundtrip():
    fm = load_front_matter(MINIMAL_FRONT + "\n# body\n")
    assert fm["title"] == "Demo Skill"
    assert fm["name"] == "demo-skill"
    assert fm["status"] == "stable"


def test_min_valid_skill_passes(tmp_path):
    body = (
        MINIMAL_FRONT
        + "\n# Demo Skill\n\n## Runtime workflow\n### 1. Inspect\nbody\n\n"
        "### 2. Define\nbody\nreferences/test-smells.md\n"
    )
    skill = _write_skill(tmp_path, body, {"test-smells.md": "# smells\n\nEvidence: smell:erratic-test\n"})
    report = run_validate_skill(skill_dir=skill)
    assert report["ok"] is True
    assert report["title"] == "Demo Skill"


@pytest.mark.parametrize("missing", ["title", "name", "description", "version", "status", "evidence_base"])
def test_missing_front_matter_key_fails(tmp_path, missing):
    fm = """\
---
title: Demo Skill
name: demo-skill
description: A demo skill for validation tests.
version: 1.0.0
status: stable
evidence_base: knowledge/synthesized/skill-traceability.json
---
"""
    # drop the missing key
    lines = [ln for ln in fm.splitlines() if not ln.startswith(f"{missing}:")]
    body = "\n".join(lines) + "\n\n# x\nreferences/test-smells.md\n"
    skill = _write_skill(tmp_path, body, {"test-smells.md": "Evidence: x\n"})
    with pytest.raises(SkillValidationError, match="missing keys"):
        run_validate_skill(skill_dir=skill)


def test_no_front_matter_fails(tmp_path):
    skill = _write_skill(tmp_path, "# No front matter\n", {"test-smells.md": "Evidence: x\n"})
    with pytest.raises(SkillValidationError, match="missing YAML front matter"):
        run_validate_skill(skill_dir=skill)


def test_invalid_status_fails(tmp_path):
    body = MINIMAL_FRONT.replace("status: stable", "status: bogus") + "\n# x\nreferences/test-smells.md\n"
    skill = _write_skill(tmp_path, body, {"test-smells.md": "Evidence: x\n"})
    with pytest.raises(SkillValidationError, match="invalid status"):
        run_validate_skill(skill_dir=skill)


def test_release_candidate_status_passes(tmp_path):
    body = (
        MINIMAL_FRONT.replace("version: 1.0.0", "version: 1.0.0rc1")
        .replace("status: stable", "status: release-candidate")
        + "\n# x\nreferences/test-smells.md\n"
    )
    skill = _write_skill(tmp_path, body, {"test-smells.md": "Evidence: x\n"})
    report = run_validate_skill(skill_dir=skill)
    assert report["ok"] is True
    assert report["status"] == "release-candidate"


def test_committed_skill_cites_every_rule_and_step():
    """Regression guard: the real skill must cite all of R1..R8 and steps 1..12.

    Catches regressions like the pre-M9 gap where R6 (testability refactoring) was
    never referenced in SKILL.md.
    """
    from agentic_testcraft.config import load_settings

    skill_dir = load_settings().paths.skill_dir
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    for r in range(1, 9):
        assert f"R{r}" in text, f"SKILL.md missing rule citation R{r}"
    for n in range(1, 13):
        assert f"### {n}." in text, f"SKILL.md missing workflow step {n}"


def test_stale_placeholder_fails(tmp_path):
    body = MINIMAL_FRONT + "\nTODO: finish this\n"
    skill = _write_skill(tmp_path, body, {"test-smells.md": "Evidence: x\n"})
    with pytest.raises(SkillValidationError, match="stale placeholder"):
        run_validate_skill(skill_dir=skill)


def test_broken_link_fails(tmp_path):
    body = MINIMAL_FRONT + "\nSee [smells](references/missing.md).\n"
    skill = _write_skill(tmp_path, body, {"test-smells.md": "Evidence: x\n"})
    with pytest.raises(SkillValidationError, match="broken link"):
        run_validate_skill(skill_dir=skill)


def test_evidence_base_missing_fails(tmp_path):
    body = MINIMAL_FRONT.replace(
        "evidence_base: knowledge/synthesized/skill-traceability.json",
        "evidence_base: does/not/exist.json",
    ) + "\n# x\n"
    skill = _write_skill(tmp_path, body, {"test-smells.md": "Evidence: x\n"}, create_evidence=False)
    with pytest.raises(SkillValidationError, match="evidence_base"):
        run_validate_skill(skill_dir=skill)


def test_duplicate_rule_fails(tmp_path):
    body = MINIMAL_FRONT + "\n### R1 -\n### R1 -\n"
    skill = _write_skill(tmp_path, body, {"test-smells.md": "Evidence: x\n"})
    with pytest.raises(SkillValidationError, match="duplicate rule R1"):
        run_validate_skill(skill_dir=skill)


def test_missing_skill_md_fails(tmp_path):
    with pytest.raises(SkillValidationError, match="missing"):
        run_validate_skill(skill_dir=tmp_path / "nope")


def test_empty_references_fails(tmp_path):
    skill = _write_skill(tmp_path, MINIMAL_FRONT + "\n# x\n", refs={}, create_evidence=True)
    with pytest.raises(SkillValidationError, match="references/ directory is empty"):
        run_validate_skill(skill_dir=skill)
