"""Unit tests for the Stage 9 skill packaging (bundle) step."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_testcraft.bundle import run_bundle

MINIMAL_FRONT = """\
---
title: Demo Skill
version: 1.0.0
status: stable
evidence_base: knowledge/synthesized/skill-traceability.json
---
"""


def _make_skill(tmp_path: Path) -> Path:
    skill = tmp_path / "skill" / "agentic-testcraft"
    refs = skill / "references"
    refs.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        MINIMAL_FRONT
        + "\n# Demo\n\n### 1. Inspect\nbody\nreferences/test-smells.md\n",
        encoding="utf-8",
    )
    (refs / "test-smells.md").write_text("# smells\n\nEvidence: smell:erratic-test\n", encoding="utf-8")
    # evidence file resolved relative to skill_dir.parent.parent (repo root)
    ev = skill.parent.parent / "knowledge" / "synthesized" / "skill-traceability.json"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("{}", encoding="utf-8")
    return skill


def test_bundle_writes_manifest_and_validates(tmp_path):
    skill = _make_skill(tmp_path)
    report = run_bundle(skill_dir=skill)

    assert report["ok"] is True
    assert isinstance(report["file_count"], int)
    assert report["file_count"] >= 2
    manifest = skill / ".skill-manifest.json"
    assert manifest.is_file()

    import json
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["title"] == "Demo Skill"
    assert data["version"] == "1.0.0"
    assert data["status"] == "stable"
    # manifest excludes itself from the file list
    assert all(f["path"] != ".skill-manifest.json" for f in data["files"])


def test_bundle_reports_validation_failure(tmp_path):
    skill = _make_skill(tmp_path)
    (skill / "SKILL.md").write_text("NO FRONT MATTER " * 500 + "\n", encoding="utf-8")
    from agentic_testcraft.skill_validate import SkillValidationError
    with pytest.raises(SkillValidationError, match="skill validation failed"):
        run_bundle(skill_dir=skill)
