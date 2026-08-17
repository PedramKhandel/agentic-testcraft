# Test doubles

## Classification (route by need)

| Stub | Supplies a canned indirect input to drive behavior. |
| Spy  | Observes/records indirect outputs for later verification. |
| Mock | Verifies an expected interaction against a contract. |
| Fake | Lightweight, realistic working implementation. |
| Dummy| Pass-only placeholder, must never be used. |

## Decision tree

```
Why are you replacing the dependency?
  - need to control an indirect input  -> STUB
  - need to observe calls after run    -> SPY
  - the call is the requirement        -> MOCK
  - need realistic lightweight semantics -> FAKE
  - need a placeholder never used      -> DUMMY
  - real dep. is fast/deterministic/local/safe -> USE THE REAL ONE
```

## Defaults

- **Dummy/stub/fake over mock** unless the interaction is the requirement.
- Prefer the real dependency when it is fast, deterministic, local, and safe
  (e.g., an in-process HTTP server, a disposable container).
- Never mock the SUT; never assert incidental calls.
- Doubles are a *seam*; prefer dependency injection/lookup over static globals and
  over `if testing` forks. For legacy code, Humble Object seams first.

Evidence: principle:don-t-modify-the-sut, principle:design-for-testability, principle:keep-test-logic-out-of-production-code, principle:minimize-untestable-code; pattern:dummy-object, pattern:test-stub, pattern:spy, pattern:mock-object, pattern:fake-object, pattern:dependency-injection, pattern:dependency-lookup, pattern:test-hook, pattern:humble-object, pattern:test-specific-subclass, smell:overspecified-software.
