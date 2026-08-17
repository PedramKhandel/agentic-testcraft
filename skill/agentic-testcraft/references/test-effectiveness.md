# Test-effectiveness methods

Apply these when **risk and tooling justify it** (rule R7). Do not apply
mechanically to every trivial change.

| Method | When | Modern tool | Evidence |
|---|---|---|---|
| Mutation testing | Verify the suite actually catches faults | `mutmut` (`mutmut run`; kill surviving mutants) | modern:mutation-testing |
| Property-based testing | Broad input space with invariants | `hypothesis` (generate + shrink + example DB) | modern:property-based-testing |
| Contract testing | Cross-service HTTP boundaries | `pact-python` (consumer contracts; Pact Broker) | modern:contract-testing |
| Fuzz testing | Parsers/validators on untrusted input | `atheris` (coverage-guided, libFuzzer) or Hypothesis | modern:fuzz-testing |

## How to act

- **Mutation**: a surviving mutant is a *missing assertion*, not a passing test.
  Add a failing test that kills it; gate on mutation score in CI.
- **Property**: state the invariant; let the tool generate inputs and shrink
  failures; add the minimal reproducer as a permanent regression.
- **Contract**: replace brittle end-to-end cross-service tests with consumer
  contracts verified against the provider in CI; retire the duplicates.
- **Fuzz**: treat any raised exception as a defect to fix; prefer coverage-guided
  fuzzers; Hypothesis where a native fuzzer isn't available.

## Platform notes

`mutmut` and `atheris` are Linux/macOS-primary (Windows via WSL); use
Hypothesis as the cross-platform fallback for property/fuzz-style checks where
needed. Keep rules platform-agnostic.

Evidence (modern): modern:mutation-testing, modern:property-based-testing,
modern:contract-testing, modern:fuzz-testing; (book) principle:verify-one-condition-per-test, goal:bug-repellent, goal:tests-as-safety-net.
