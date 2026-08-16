"""Unit tests for Stage 7 synthesis (operational decision rules)."""
from __future__ import annotations

from agentic_testcraft.schemas import DecisionRuleRecord
from agentic_testcraft.synthesize import (
    _slug,
    build_decision_rules,
    derive_goal_rule,
    derive_pattern_rule,
    derive_principle_rule,
    derive_smell_rule,
    derive_workflow_rules,
)


def _pat(slug, name="Foo Pattern", problem="How do we do X?", solution="Use Foo.", **kw):
    return {
        "id": f"pattern:{slug}", "name": name, "origin": "book", "confidence": "default",
        "aliases": [], "source_refs": [], "category": "",
        "problem": problem, "solution": solution, "intent": None, "context": None,
        "forces": [], "use_when": kw.get("use_when"), "avoid_when": kw.get("avoid_when"),
        "benefits": [], "costs": [], "risks": kw.get("risks", []),
        "implementation_variations": [], "related_patterns": [],
        "prevents_smells": [], "may_cause_smells": [],
        "refactorings": [], "agent_decision_rule": None, "agent_actions": [],
        "common_misinterpretations": [],
        "historical_or_framework_specific_notes": None,
    }


def _smell(slug, name=None, summary=None, symptoms=None, causes=None):
    return {
        "id": f"smell:{slug}", "name": name or slug.replace("-", " ").title(),
        "origin": "book", "confidence": "default", "aliases": [], "source_refs": [],
        "summary": summary or f"It is hard to {slug}.",
        "symptoms": symptoms or [], "impact": [], "causes": causes or [],
        "detection_heuristics": [], "false_positive_risks": [],
        "related_smells": [], "recommended_patterns": [],
        "agent_review_checks": [],
    }


def _principle(slug, statement="Always verify behavior.", **kw):
    return {
        "id": f"principle:{slug}", "name": slug.replace("-", " ").title(),
        "origin": "book", "confidence": "default", "aliases": [], "source_refs": [],
        "statement": statement, "rationale": "", "default_rule": kw.get("default_rule", ""),
        "exceptions": kw.get("exceptions", []), "tradeoffs": [],
        "failure_modes_if_ignored": kw.get("failures", []),
        "related_patterns": [], "related_smells": [],
        "agent_checks": kw.get("checks", []),
    }


def _goal(slug, summary="Reduce bugs.", **kw):
    return {
        "id": f"goal:{slug}", "name": slug.replace("-", " ").title(),
        "origin": "book", "confidence": "default", "aliases": [], "source_refs": [],
        "summary": summary, "why_it_matters": "", "indicators": kw.get("indicators", []),
        "tensions": kw.get("tensions", []), "related_principles": [],
    }


def test_slug():
    assert _slug("Foo Pattern") == "foo-pattern"
    assert _slug("  ") == "item"


def test_pattern_rule_evidence_from_graph():
    pat = _pat("foo")
    edges = [
        {"from_id": "smell:bar", "relationship": "refactors_to", "to_id": "pattern:foo"},
        {"from_id": "pattern:foo", "relationship": "may_cause", "to_id": "smell:baz"},
    ]
    r = derive_pattern_rule(pat, edges)
    assert r["id"] == "rule:foo-pattern"
    assert r["strength"] == "certain"
    assert r["origin"] == "book"
    # evidence = pattern + smells addressed (refactors_to) + may_cause
    assert r["evidence_ids"] == ["pattern:foo", "smell:bar", "smell:baz"]
    assert r["default_action"].startswith("Apply the Foo Pattern")
    assert {"condition": "a smell this pattern addresses is detected",
            "action": "introduce the pattern and refactor to remove the smell"} in r["decision_logic"]
    DecisionRuleRecord(**r)


def test_pattern_rule_avoid_when_exception_and_risks():
    pat = _pat("foo", avoid_when="when X is immutable", risks=["risky", "risky2"])
    r = derive_pattern_rule(pat, [])
    assert r["exceptions"] == ["when X is immutable"]
    assert r["warnings"] == ["risky", "risky2"]
    DecisionRuleRecord(**r)


def test_smell_rule_evidence_from_graph():
    sm = _smell("bar", symptoms=["flaky", "slow"], causes=["root cause"])
    edges = [{"from_id": "smell:bar", "relationship": "refactors_to", "to_id": "pattern:foo-pattern"}]
    r = derive_smell_rule(sm, edges)
    assert r["id"] == "rule:smell-bar"
    assert r["strength"] == "warning"
    # evidence = smell id + patterns that address it (from graph)
    assert r["evidence_ids"] == ["smell:bar", "pattern:foo-pattern"]
    assert r["warnings"] == ["root cause"]
    assert r["agent_verification"] == ["flaky", "slow"]
    assert r["default_action"].startswith("Do not introduce or leave 'Bar' in place")
    DecisionRuleRecord(**r)


def test_smell_rule_empty_causes_not_none():
    sm = _smell("bar")  # no symptoms, no causes -> must not raise
    r = derive_smell_rule(sm, [])
    assert isinstance(r["warnings"], list)
    assert isinstance(r["agent_verification"], list)
    assert isinstance(r["decision_logic"][0]["condition"], str)
    DecisionRuleRecord(**r)


def test_principle_rule_evidence_both_directions():
    pr = _principle("verify-behavior", default_rule="Do not mock what you can avoid.",
                    exceptions=["when no real impl exists"],
                    failures=["tests break on refactors"], checks=["check one outcome"])
    edges = [
        {"from_id": "principle:verify-behavior", "relationship": "supports", "to_id": "pattern:p1"},
        {"from_id": "goal:regression", "relationship": "supports", "to_id": "principle:verify-behavior"},
    ]
    r = derive_principle_rule(pr, edges)
    assert r["id"] == "rule:verify-behavior"
    assert r["strength"] == "certain"
    assert r["exceptions"] == ["when no real impl exists"]
    assert r["warnings"] == ["tests break on refactors"]
    assert r["agent_verification"] == ["check one outcome"]
    # principle + pattern it supports + goal that references it
    assert set(r["evidence_ids"]) == {"principle:verify-behavior", "pattern:p1", "goal:regression"}
    DecisionRuleRecord(**r)


def test_goal_rule():
    g = _goal("regression", indicators=["fast feedback"], tensions=["flaky tests"],
              why_it_matters="Keeps main green.")
    edges = [{"from_id": "goal:regression", "relationship": "supports", "to_id": "smell:flaky-tests"}]
    r = derive_goal_rule(g, edges)
    assert r["id"] == "rule:regression"
    assert r["strength"] == "default"
    assert "smell:flaky-tests" in r["evidence_ids"]
    assert r["agent_verification"] == ["fast feedback"]
    assert r["warnings"] == ["flaky tests"]
    assert r["decision_logic"][0]["condition"] == "flaky tests"
    DecisionRuleRecord(**r)


def test_workflow_rules_count_and_content():
    by_id = {
        "principle:foo": _principle("foo"), "principle:bar": _principle("bar"),
        "goal:baz": _goal("baz"), "goal:qux": _goal("qux"),
    }
    rules = derive_workflow_rules(by_id)
    assert len(rules) == 2
    ids = {r["id"] for r in rules}
    assert "rule:one-condition-per-test" in ids
    assert "rule:test-execution-workflow" in ids
    cond = next(r for r in rules if r["id"] == "rule:one-condition-per-test")
    assert cond["strength"] == "certain"
    assert "principle:foo" in cond["evidence_ids"]
    assert "principle:bar" in cond["evidence_ids"]
    wf = next(r for r in rules if r["id"] == "rule:test-execution-workflow")
    assert wf["strength"] == "preference"
    for r in rules:
        DecisionRuleRecord(**r)


def test_build_decision_rules_count_and_dedup():
    recs = [
        _pat("foo-pattern"),
        _smell("bar"),
        _principle("verify-behavior"),
        _goal("regression"),
    ]
    edges = [{"from_id": "smell:bar", "relationship": "refactors_to", "to_id": "pattern:foo-pattern"}]
    by_id = {r["id"]: r for r in recs}
    rules = build_decision_rules(recs, edges, by_id)
    # 4 entity rules + 2 workflow rules
    assert len(rules) == 6
    for r in rules:
        DecisionRuleRecord(**r)
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids))
