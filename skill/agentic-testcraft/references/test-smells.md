# Test smells (review checklist)

## The catalog (15)

| Smell | Short form | Evidence |
|---|---|---|
| Obscure Test | hidden cause/effect between fixture and verification | smell:obscure-test |
| Conditional Test Logic | control flow inside the test | smell:conditional-test-logic |
| Hard-to-Test Code | the *production* code resists testing | smell:hard-to-test-code |
| Test Code Duplication | same test logic repeated | smell:test-code-duplication |
| Test Logic in Production | `if testing` forks in the SUT | smell:test-logic-in-production |
| Assertion Roulette | can't tell which assertion failed | smell:assertion-roulette |
| Erratic Test | flaky order/timing/shared-state failures | smell:erratic-test |
| Fragile Test | breaks on unrelated SUT changes | smell:fragile-test |
| Frequent Debugging | failures need interactive debugging | smell:frequent-debugging |
| Manual Intervention | a person must act each run | smell:manual-intervention |
| Slow Tests | test run too slow to run after every save | smell:slow-tests |
| Buggy Tests | the tests themselves contain bugs | smell:buggy-tests |
| Developers Not Writing Tests | no automation at all | smell:developers-not-writing-tests |
| High Test Maintenance Cost | upkeep effort dominates | smell:high-test-maintenance-cost |
| Production Bugs | too many bugs reach formal tests/production | smell:production-bugs |

## Step-10 review checklist (must check before completion)

- [ ] Obscure Test · [ ] Conditional Test Logic · [ ] Test Code Duplication
- [ ] Assertion Roulette · [ ] Erratic/Flaky Test · [ ] Fragile Test
- [ ] General/Overgrown Fixture · [ ] Mystery Guest
- [ ] excessive interaction verification · [ ] unnecessary mocks · overspecified behavior
- [ ] slow setup · hidden shared state · [ ] Buggy Tests

## Remedies (by smell)

- **Obscure/Obscured intent** → Intent-Revealing Names, extract helpers, Custom Assertion.
- **Assertion Roulette** → one condition per test, or an assertion message per check.
- **Erratic/Fragile** → fresh/immutable fixtures, reset shared state, freeze time,
  avoid shared DB; treat flakiness as fatal (no retries).
- **Slow** → run smallest scope first, parallelize (`-n auto`), shard (`--splits`).
- **Over-specified/over-mocked** → state verification over interaction; drop mocks
  whose contract isn't the requirement.

Evidence: smells (all); principles keep-tests-independent, isolate-the-sut, minimize-test-overlap; modern:flaky-as-fatal, modern:ci-parallel-execution, modern:monorepo-suite-partitioning.
