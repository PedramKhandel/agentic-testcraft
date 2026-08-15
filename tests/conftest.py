"""Shared pytest fixtures and path configuration."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is importable even when not installed editable.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
