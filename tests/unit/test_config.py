"""Tests for config path resolution."""
from __future__ import annotations

from agentic_testcraft.config import DEFAULT_PATHS, Paths, load_settings


def test_repo_root_resolves_to_repo():
    assert DEFAULT_PATHS.repo_root.name == "agentic-testcraft"


def test_path_names():
    p = Paths()
    assert p.local_dir.name == ".local"
    assert p.knowledge_book_dir.parts[-2:] == ("knowledge", "book")
    assert p.skill_dir.parts[-1] == "agentic-testcraft"


def test_settings_load_without_creds():
    s = load_settings()
    assert s.paths.repo_root == DEFAULT_PATHS.repo_root
    assert s.llm_provider == "native-agent"
