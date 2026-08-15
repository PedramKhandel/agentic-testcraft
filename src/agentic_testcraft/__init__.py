"""Agentic Testcraft: a coding-agent skill for better automated testing.

This package implements a deterministic pipeline that transforms structured
knowledge of testing practice (primarily inspired by *xUnit Test Patterns*)
into operational decision rules, then packages those rules as a portable
Agent Skill.

Knowledge layers
----------------
A. ``knowledge/book``      — source-faithful, provenance-linked book knowledge
B. ``knowledge/modern``     — current practice from official/primary sources
C. ``knowledge/synthesized``— compact agent-decision rules with evidence links
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.1.0"
