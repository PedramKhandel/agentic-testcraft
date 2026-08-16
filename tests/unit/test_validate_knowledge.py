"""Unit tests for the Stage-4 knowledge validator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentic_testcraft.schemas import (
    ChunkRecord,
    StructureReport,
    _model_for_id,
    run_validate_knowledge,
)

FILE_SHA = "a" * 64


def _chunk(**over) -> dict:
    base = {
        "id": "pattern:assertion-method",
        "kind": "pattern",
        "chapter_kind": "pattern_chapter",
        "chapter_title": "xUnit Basics Patterns",
        "title": "Assertion Method",
        "category": "",
        "clean_start_line": 1,
        "clean_end_line": 10,
        "source_refs": [
            {
                "source_id": "book",
                "file_sha256": FILE_SHA,
                "markdown_start_line": 1,
                "markdown_end_line": 10,
            }
        ],
        "subsections": ["How It Works"],
        "aliases": [],
    }
    base.update(over)
    return base


def test_chunk_record_accepts_valid():
    rec = ChunkRecord(**_chunk())
    assert rec.id == "pattern:assertion-method"
    assert rec.kind == "pattern"


def test_chunk_record_rejects_bad_kind():
    with pytest.raises(ValidationError):
        ChunkRecord(**_chunk(kind="nope"))


def test_chunk_record_rejects_inverted_bounds():
    with pytest.raises(ValidationError):
        ChunkRecord(**_chunk(clean_start_line=20, clean_end_line=5))


def test_chunk_record_requires_source_ref():
    with pytest.raises(ValidationError):
        ChunkRecord(**_chunk(source_refs=[]))


def test_chunk_record_rejects_extra_field():
    with pytest.raises(ValidationError):
        ChunkRecord(**{**_chunk(), "bogus": 1})


def test_structure_report_accepts_valid():
    r = StructureReport(
        file_sha256=FILE_SHA,
        chunk_count=119,
        by_kind={"pattern": 50},
        by_chapter_kind={"pattern_chapter": 10},
        completeness_problems=[],
    )
    assert r.chunk_count == 119


def test_structure_report_rejects_bad_sha():
    with pytest.raises(ValidationError):
        StructureReport(
            file_sha256="not-a-hash",
            chunk_count=0,
            by_kind={},
            by_chapter_kind={},
            completeness_problems=[],
        )


def test_model_dispatch_by_id_prefix():
    assert _model_for_id("pattern:x") is not None
    assert _model_for_id("smell:y") is not None
    assert _model_for_id("relationship:z") is not None
    assert _model_for_id("unknown:w") is None


def test_validate_knowledge_passes_on_real_artifacts():
    # Validates the actual M3 outputs committed/generated in .local/work.
    run_validate_knowledge()


def test_validate_knowledge_fails_on_corrupt_manifest(monkeypatch, tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "chunk-manifest.jsonl").write_text(
        json.dumps(_chunk(id="pattern:bad", kind="BOGUS")) + "\n",
        encoding="utf-8",
    )
    (work / "structure.json").write_text(
        json.dumps(
            {
                "file_sha256": FILE_SHA,
                "chunk_count": 1,
                "by_kind": {},
                "by_chapter_kind": {},
                "completeness_problems": [],
            }
        ),
        encoding="utf-8",
    )
    # load_settings() shares the DEFAULT_PATHS instance, so repoint its work_dir.
    import agentic_testcraft.config as cfg

    monkeypatch.setattr(cfg.DEFAULT_PATHS, "work_dir", work)
    with pytest.raises(SystemExit):
        run_validate_knowledge()
