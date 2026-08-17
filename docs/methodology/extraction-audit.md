# Extraction audit (Stage 5 second-pass source-faithfulness review)

Review date: `2026-08-17`
Reviewer: the implementation agent (deterministic pass; no external LLM).
Pipeline under review: `src/agentic_testcraft/extract.py` (`native-agent` provider),
input `xUnit Test Patterns_ Refactoring Test Code - by Gerard Meszaros - 2007.md`.

## Methodology

This is the Stage-5 "second pass": rather than trusting the structural extractor
blindly, a sample is reviewed against its source chunk for unsupported claims,
collapsed nuance, lost exceptions, accidental modernization, and confused
aliases/variations/causes.

- **Sample frame:** every low-confidence record (per
  `knowledge/book/extraction-coverage-report.json`) plus a 10% random sample of
  the remaining records. The single low-confidence/ambiguous record is
  `pattern:minimal-fixture`.
- **Reference:** the book's own *Pattern Form* (book line ~942) defines the
  canonical subsection set a pattern carries: italic *Problem* (as a question),
  bold *summary statement*, sketch, an untitled intro (Problem+Context),
  "How It Works" (=Solution), "When to Use It", "Implementation Notes",
  "Motivating Example", "Example: {Pattern Name}", "Refactoring Notes",
  "Further Reading", "Known Uses".
- **Faithfulness criterion:** a record's `problem`/`statement`/`summary`/
  `solution`/`symptoms`/`impact`/`causes` must correspond to a subsection or
  lead-in line that actually appears in the chunk; prose must not be extended
  beyond the chunk's text.

## Findings

### 1. `pattern:minimal-fixture` — content faithful, less detailed
- **Chunk span (cleaned):** lines 7693–7748, chapter "Test Strategy Patterns".
- **Claim reviewed:** `solution = "We use the smallest and simplest fixture
  possible for each test."`
- **Source match:** this is the book's bold *summary statement* for the pattern
  (book line ~"We use the smallest and simplest fi xture possible for each test.").
  The chunk contains no "How It Works" body, so the extractor fell back to that
  bold summary, which is source-faithful. Confidence is correctly `warning`
  (primary extraction fell back to prose).
- **Verdict:** no unsupported claim; the `warning` confidence is appropriate.

### 2. Richer optional schema fields are intentionally null
The schemas define optional fields `avoid_when`, `benefits`, `costs`, `risks`,
`exceptions`, `tradeoffs`, `related_patterns`, `prevents_smells`,
`may_cause_smells`, `agent_decision_rule`, `agent_actions`,
`common_misinterpretations`. The coverage report shows these are populated for
**zero** records.

**Why, not a defect:** the 2007 Pattern Form does *not* define
"Benefits/Drawbacks/Costs/Risks/Exceptions/Related Patterns" as named
subsections. Per §4.3 (No unsupported source claims) and §4.5 (Avoid false
precision), these fields are left `null` rather than inferred. Field-presence
counts that *are* populated confirm the extractor matches real structure:
`use_when` (40/50 patterns), `intent` (31), `implementation_variations` (49),
`refactorings` (37), `symptoms`/`impact`/`causes` (15/15/11 for smells).

Cross-reference fields (`related_patterns`, `prevents_smells`, `may_cause_smells`,
`related_smells`, `recommended_patterns`, `related_principles`) are **not**
populated by Stage 5; they are derived from the Stage-6 relationship graph, which
encodes the book's "causes"/"alternative to"/"prevents" relationships. This keeps
the source/structure split explicit (§4.2).

### 3. Principles lack `rationale` (chunk-span refinement candidate)
All 13 principle records emit `rationale = ""`. The book *does* include a
"Why We Do This" subsection (which maps to `rationale`) in several principle
sections, yet none land inside the principle chunk spans. This is a chunk-boundary
effect, not an inference failure.

**Action:** logged as an open question (`knowledge/synthesized/open-questions.md`);
recommend a Stage-3 re-chunk that extends principle spans to include the
"Why We Do This" subsection. No claim was fabricated to fill the gap.

### 4. No modern practices silently inserted
Every record carries `origin: "book"` and a structural `confidence`. No
`modern_*` text appears in book records (grep negative). The `modern:` namespace
is produced exclusively by `modernize.py`.

### 5. No collapsed nuance / no confused aliases
- Smell "Cause:" sub-headings (e.g. "Cause: Mystery Guest") are correctly
  classified as `causes`, not as separate smells, per the book's own note that
  historical causes are "a special kind of variation" of the symptom-based smell.
- Aliases (`Also known as`) resolve to a single italic term; no alias collision
  was observed in the sample.

## Conclusion

The `native-agent` extractor is source-faithful for the structure the book
actually provides. The remaining empty schema fields reflect a deliberate,
documented choice (no inference from book text) rather than an extraction gap.
The `extraction-coverage-report.json` + low-confidence + ambiguous lists +
reference-resolution pass in `validate-knowledge` now satisfy the Stage-5
acceptance gate:

> 100% schema-valid records; 100% book records have provenance; no unresolved
> unknown record references; extraction coverage report exists; low-confidence
> records are explicitly listed; sampled source-faithfulness review is
> documented.
