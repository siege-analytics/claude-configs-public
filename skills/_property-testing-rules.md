---
description: Always-on property-testing standards from the Hypothesis documentation. Apply when writing tests for functions with numeric, string, or collection inputs.
---

# Property Testing Standards

Apply these principles from the [Hypothesis](https://hypothesis.readthedocs.io/) documentation to test code.

## When to use property tests

- Any function that transforms data (normalize, aggregate, project, interpolate) is a candidate. If you can state "for all valid inputs, the output satisfies X," write a property test.
- Property tests complement, not replace, example-based tests. Use examples for specific known edge cases. Use properties for invariants that hold across the input space.
- Prefer property tests when the input domain is large or combinatorial (GEOIDs, CRS codes, date ranges, coordinate pairs).

## Writing good properties

- **Round-trip:** if `encode(decode(x)) == x`, test that. Serialization, CRS transform-and-back, geocode-then-reverse are all round-trip candidates.
- **Invariant preservation:** normalization functions should be idempotent (`normalize(normalize(x)) == normalize(x)`). Aggregation should not increase count. Spatial union should contain all inputs.
- **Oracle comparison:** when a simple-but-slow reference implementation exists, assert the optimized version matches it on random inputs.
- **No-crash / no-hang:** at minimum, the function should not raise an unexpected exception or run forever on any valid input. `@given(...)` with just `assume()` guards and no assertion still catches crashes.

## Strategies

- Use built-in strategies (`st.integers()`, `st.text()`, `st.floats()`) with domain-appropriate bounds. A latitude strategy is `st.floats(min_value=-90, max_value=90)`.
- Build composite strategies with `@st.composite` for domain objects (GeoDataFrames, Census API responses, election results).
- Use `st.sampled_from()` for enums and known-set inputs (state FIPS codes, geography levels).

## Shrinking and debugging

- When a property test fails, Hypothesis automatically shrinks the input to the minimal failing case. Read the minimal example before debugging — it usually reveals the boundary condition.
- Use `@example(...)` to pin known regressions so they run on every invocation, not just when Hypothesis happens to generate them.

## Integration with pytest

- Use a `hypothesis` profile in `conftest.py` with `max_examples=100` for CI and `max_examples=1000` for local thorough runs.
- Mark slow property tests with `@pytest.mark.slow` so CI can run a fast subset.
- Suppress the Hypothesis health check for tests that need expensive setup (database, network fixtures) using `@settings(suppress_health_check=[...])`.


---

## Attribution

Principles distilled from the [Hypothesis documentation](https://hypothesis.readthedocs.io/). Hypothesis is licensed under the Mozilla Public License 2.0.
