# Decision trees

Quick reference for the two highest-leverage judgment calls. Detailed context in
the per-topic reference docs.

## Tree 1 — Where to cut the SUT boundary

```
Does the behavior stay in one unit/component?
  yes -> Unit test directly (Layer Test).
  no  -> Does the requirement cross a boundary (HTTP/DB/stream/external API)?
           yes -> Integration test at the real boundary
                  (Layer Test + real DOC); contract if cross-service.
           no  -> Add a seam (DI/Humble Object) so a unit test suffices,
                  OR test the smaller component in isolation.
```

## Tree 2 — Which test double

```
Why replace the dependency?
  need to control an indirect input  -> STUB
  need to observe calls after run    -> SPY
  the call is the requirement        -> MOCK
  need realistic lightweight semantics -> FAKE
  placeholder never used             -> DUMMY
  real dep. fast/deterministic/local/safe -> USE THE REAL ONE
```
Guard: never "dependency exists → mock it"; never mock the SUT; never assert
incidental internal calls.

## Tree 3 — Is this test smell worth fixing now

```
Does the suite still pass AND the change is trivial?
  yes -> Note the smell; proceed, but log it for a review pass.
  no  -> Fix before completion: extract helpers / add assertion messages /
         split the condition / remove shared mutable fixture.
Flaky? -> ALWAYS fix (remove external state dependence) — never retry/suppress.
Slow? -> Smallest scope first, then parallelize/shard.
```

Evidence: pattern:layer-test, pattern:back-door-manipulation, pattern:humble-object, pattern:dependency-injection; principle:isolate-the-sut, principle:use-the-front-door-first, principle:don-t-modify-the-sut; modern:contract-testing, modern:flaky-as-fatal, modern:ci-parallel-execution, modern:monorepo-suite-partitioning; smells (all).
