"""Central configuration and path resolution for the agentic-testcraft pipeline.

All paths flow from this module so that tests can override locations without
touching the rest of the codebase. Configuration may be supplied via an optional
``agentic-testcraft.yaml`` file, with environment variables taking precedence
for anything security-sensitive.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


def repo_root() -> Path:
    """Return the repository root (the cwd containing this package's parents)."""
    # src/agentic_testcraft/config.py -> repo root is three levels up
    return Path(__file__).resolve().parents[2]


REPO_ROOT = repo_root()


class Paths(BaseModel):
    """Resolved locations used by the build pipeline."""

    repo_root: Path = Field(default_factory=repo_root)
    source_dir: Path = Field(default_factory=lambda: REPO_ROOT)
    local_dir: Path = Field(default_factory=lambda: REPO_ROOT / ".local")
    work_dir: Path = Field(default_factory=lambda: REPO_ROOT / ".local" / "work")
    source_work_dir: Path = Field(default_factory=lambda: REPO_ROOT / ".local" / "source")
    chunks_dir: Path = Field(default_factory=lambda: REPO_ROOT / ".local" / "chunks")
    extraction_dir: Path = Field(default_factory=lambda: REPO_ROOT / ".local" / "extraction")
    renders_dir: Path = Field(default_factory=lambda: REPO_ROOT / ".local" / "renders")
    logs_dir: Path = Field(default_factory=lambda: REPO_ROOT / ".local" / "logs")
    knowledge_book_dir: Path = Field(default_factory=lambda: REPO_ROOT / "knowledge" / "book")
    knowledge_modern_dir: Path = Field(default_factory=lambda: REPO_ROOT / "knowledge" / "modern")
    knowledge_synthesized_dir: Path = Field(default_factory=lambda: REPO_ROOT / "knowledge" / "synthesized")
    knowledge_graph_dir: Path = Field(default_factory=lambda: REPO_ROOT / "knowledge" / "graph")
    schema_dir: Path = Field(default_factory=lambda: REPO_ROOT / "schemas")
    docs_dir: Path = Field(default_factory=lambda: REPO_ROOT / "docs")
    evals_dir: Path = Field(default_factory=lambda: REPO_ROOT / "evals")
    skill_dir: Path = Field(default_factory=lambda: REPO_ROOT / "skill" / "agentic-testcraft")

    def ensure_local_dirs(self) -> None:
        for p in (
            self.work_dir,
            self.source_work_dir,
            self.chunks_dir,
            self.extraction_dir,
            self.renders_dir,
            self.logs_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)

    def ensure_knowledge_dirs(self) -> None:
        for p in (
            self.knowledge_book_dir,
            self.knowledge_modern_dir,
            self.knowledge_synthesized_dir,
            self.knowledge_graph_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)


DEFAULT_PATHS = Paths()


def env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    """Runtime settings. Secrets come ONLY from the environment."""

    paths: Paths = Field(default_factory=lambda: DEFAULT_PATHS)

    # LLM / provider configuration (read from env; never committed)
    llm_provider: str = Field(default_factory=lambda: os.environ.get("AT_LLM_PROVIDER", "native-agent"))
    llm_model: str = Field(default_factory=lambda: os.environ.get("AT_LLM_MODEL", "unset"))
    # API keys must never be stored or logged
    llm_api_key: str | None = Field(default=None, exclude=True)

    # Deterministic extraction caching behaviour
    extraction_cache: bool = Field(default=True)

    def ensure_dirs(self) -> None:
        self.paths.ensure_local_dirs()
        self.paths.ensure_knowledge_dirs()


def load_settings() -> Settings:
    """Load settings, preferring env overrides over a checked-in yaml."""
    return Settings()
