# Testability refactoring

## Goal

Make production code testable **without** test-only branches and **without**
changing production behavior. Prefer behavior-preserving changes.

## Seams (in order of preference)

1. **Dependency Injection / Lookup** — pass the DOC in or look it up through an
   interface; the test supplies a double. (Preferred; keeps the SUT honest.)
2. **Humble Object** — extract logic into a synchronous, easily-tested component
   and leave a thin adapter around the framework/IO boundary.
3. **Test Hook** — add a minimal, always-in production hook to substitute a DOC.
   Last resort; never an `if testing` fork.
4. **Test-Specific Subclass** — override behavior for testing, only when the
   subclass replaces a DOC (not the SUT itself).

## Rules

- Extract testable logic out of hard-to-test components (GUI, async callbacks,
  static/global state, tight coupling).
- Never put test logic into production code; any test hook must be pluggable
  and test-only at runtime, absent in production behavior.
- After refactoring, run the **existing** tests first; a regression here means
  the refactor was not behavior-preserving.

Evidence: pattern:humble-object, pattern:dependency-injection, pattern:dependency-lookup, pattern:test-hook, pattern:test-specific-subclass; principle:keep-test-logic-out-of-production-code, principle:don-t-modify-the-sut, principle:minimize-untestable-code, smell:hard-to-test-code.
