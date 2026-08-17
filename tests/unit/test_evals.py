"""Unit tests for the M10a evaluation harness (src/agentic_testcraft/evals.py)."""
from __future__ import annotations

import re
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentic_testcraft.evals import (
    CASE_CATALOG,
    EVAL_APP,
    METRIC_KEYS,
    RUBRIC_DIMS,
    EvalResult,
    RunMetadata,
    _dump_simple_toml,
    _parse_outcome,
    case_ids,
    get_case,
    init_cases,
    load_cases,
    score_run,
    setup_case,
)

EXPECTED_CASE_COUNT = 26

GOOD_TESTS = textwrap.dedent("""\
    from sut import add
    import pytest

    @pytest.mark.parametrize("a,b,exp", [(1, 2, 3), (0, 0, 0), (-1, 1, 0), (-5, -5, -10)])
    def test_add(a, b, exp):
        assert add(a, b) == exp
""")


def _now() -> datetime:
    return datetime.now(UTC)


def test_catalog_has_expected_count_and_unique_ids() -> None:
    ids = case_ids()
    assert len(ids) == EXPECTED_CASE_COUNT
    assert len(set(ids)) == EXPECTED_CASE_COUNT
    for cid in ids:
        assert re.fullmatch(r"[a-z0-9-]{2,40}", cid)


def test_catalog_cases_are_valid() -> None:
    assert load_cases() == CASE_CATALOG  # equal content
    assert load_cases() is not CASE_CATALOG  # load_cases returns a copy
    for c in CASE_CATALOG:
        assert c.sut_src.strip()
        assert 1 <= len(c.defects) <= 2
        defect_ids = [d.defect_id for d in c.defects]
        assert len(set(defect_ids)) == len(defect_ids)
        for d in c.defects:
            assert d.defect_id
            assert d.description
            assert d.sut_src.strip()  # every seeded variant is real testable source
        assert set(c.key_metrics) <= set(METRIC_KEYS)
        assert set(c.rubric_focus) <= set(RUBRIC_DIMS)


def test_get_case_known_and_unknown() -> None:
    assert get_case("pure-function").case_id == "pure-function"
    with pytest.raises(KeyError):
        get_case("does-not-exist")


def test_init_cases_materializes_valid_toml(tmp_path: Path) -> None:
    base = init_cases(tmp_path / "cases")
    case_dir = base / "pure-function"
    assert case_dir.is_dir()
    assert (case_dir / "tests").is_dir()
    assert (case_dir / "task.md").is_file()
    toml_path = case_dir / "case.toml"
    assert toml_path.is_file()
    import tomllib

    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    assert data["case_id"] == "pure-function"
    assert data["category"] == "logic"
    assert data["defects"] == ["negation"]
    assert data["key_metrics"] == ["seeded_defects_caught", "mutation_score"]


def test_dump_simple_toml_roundtrip() -> None:
    data = {"a": "x\ny", "b": [1, 2], "c": []}
    text = _dump_simple_toml(data)
    assert "a = \"x\\ny\"" in text
    assert "b = [\"1\", \"2\"]" in text


def test_setup_case_base_writes_sut_tests_and_task(tmp_path: Path) -> None:
    sb = setup_case("pure-function", dest=tmp_path / "base")
    assert (sb / "sut.py").is_file()
    assert (sb / "tests").is_dir()
    assert (sb / "task.md").is_file()
    sut = (sb / "sut.py").read_text(encoding="utf-8")
    assert "def add" in sut
    assert "a - b" not in sut  # base SUT returns a + b


def test_setup_case_defect_swaps_sut(tmp_path: Path) -> None:
    base = setup_case("pure-function", dest=tmp_path / "base")
    defect = setup_case("pure-function", defect_id="negation", dest=tmp_path / "def")
    base_src = (base / "sut.py").read_text(encoding="utf-8")
    defect_src = (defect / "sut.py").read_text(encoding="utf-8")
    assert base_src != defect_src
    assert "a + b" in base_src
    assert "a - b" in defect_src


def test_setup_case_unknown_defect_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        setup_case("pure-function", defect_id="nope", dest=tmp_path / "x")


def test_parse_outcome_handles_both_orderings() -> None:
    assert _parse_outcome("3 passed, 1 failed in 0.12s") == (3, 1, 0.12)
    assert _parse_outcome("1 failed, 3 passed in 0.5s") == (3, 1, 0.5)
    assert _parse_outcome("5 passed in 1.0s") == (5, 0, 1.0)
    assert _parse_outcome("no tests ran") == (0, 0, 0.0)


def test_score_run_catches_seeded_defect(tmp_path: Path) -> None:
    tests_dir = tmp_path / "agent-tests"
    tests_dir.mkdir()
    (tests_dir / "test_add.py").write_text(GOOD_TESTS, encoding="utf-8")
    meta = RunMetadata(
        case_id="pure-function",
        condition="skill",
        agent="test",
        model="stub",
        started_at=_now(),
    )
    result = score_run("pure-function", tests_dir, "skill", meta)
    assert result.case_id == "pure-function"
    assert result.passed is True
    assert result.defect_caught == {"negation": True}
    assert result.metrics["seeded_defects_caught"] == 1
    assert result.metrics["mutation_score"] == 1.0
    assert result.metrics["generated_tests_pass"] is True
    assert result.metrics["explicit_sleeps"] == 0
    assert result.metrics["sut_mocked"] is False
    assert "randomized_order_execution" in result.metrics
    assert result.errors == []


def test_score_run_weak_tests_do_not_catch_defect(tmp_path: Path) -> None:
    tests_dir = tmp_path / "weak-tests"
    tests_dir.mkdir()
    (tests_dir / "test_add.py").write_text(
        "from sut import add\n\n\ndef test_add_returns_something():\n    assert isinstance(add(1, 2), int)\n",
        encoding="utf-8",
    )
    meta = RunMetadata(
        case_id="pure-function",
        condition="baseline",
        agent="test",
        model="stub",
        started_at=_now(),
    )
    result = score_run("pure-function", tests_dir, "baseline", meta)
    # weak assertion passes on the correct SUT but does NOT catch the negation defect
    assert result.passed is True
    assert result.defect_caught == {"negation": False}
    assert result.metrics["mutation_score"] == 0.0


def test_eval_app_exposes_commands() -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(EVAL_APP, ["--help"])
    assert result.exit_code == 0
    for name in ("list-cases", "init-cases", "setup", "score", "report"):
        assert name in result.output


def test_eval_result_schema_roundtrip() -> None:
    meta = RunMetadata(
        case_id="pure-function",
        condition="skill",
        agent="test",
        model="stub",
        started_at=_now(),
    )
    r = EvalResult(case_id="pure-function", condition="skill", run_meta=meta)
    dumped = r.model_dump()
    assert dumped["run_meta"]["condition"] == "skill"
    assert dumped["defect_caught"] == {}
    # round-trips through JSON (used by the `score` and `report` CLI paths)
    back = EvalResult.model_validate_json(r.model_dump_json())
    assert back == r
    assert back.case_id == "pure-function"
