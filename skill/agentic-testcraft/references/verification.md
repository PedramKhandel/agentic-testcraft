# Verification strategy

## Two modes

- **State verification** — assert the SUT's direct output/returned/mutated
  state after exercise (return values, object state, emitted events captured by
  a spy). *Default choice* when a stable public interface exposes the result.
- **Behavior/interaction verification** — assert a call the SUT made to a
  depended-on component (DOC). Use only when (a) the interaction itself is the
  observable requirement, or (b) no reliable post-state exists.

## Defaults and guardrails

- Default toward state verification through a stable public interface.
- Interaction verification must target *observable, contract-level* calls, not
  incidental internals. Asserting "an internal method was called" is a smell.
- Each assertion should have a message explaining the *outcome* being protected
  (Assertion Message), so a failure is locally diagnosable.

## Assertions

- Encode the expected outcome inside the test (Assertion Method / Custom
  Assertion); the runner goes green only when the outcome matches.
- Prefer a self-describing assertion so the red/green bar is trustworthy.

Evidence: principle:use-the-front-door-first, principle:don't-modify-the-sut, principle:verify-one-condition-per-test; pattern:state-verification, pattern:behavior-verification, pattern:assertion-method, pattern:assertion-message, pattern:custom-assertion; smell:assertion-roulette, smell:obscure-test.
