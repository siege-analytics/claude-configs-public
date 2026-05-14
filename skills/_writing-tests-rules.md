---
description: Always-on. Test-writing discipline. Tests must exercise the production code, not the mock setup; mocks must use real exception classes and real-shape fixtures; skip messages must name how to unskip; no cargo-culted copy-modify across similar targets. Code-writing rules live in `_writing-code-rules.md`; claim-grounding lives in `_writing-claims-rules.md`.
---

# Writing Tests

These rules apply whenever the agent writes a test or a test fixture. Tests fail in distinctive ways: theater (the mock asserts itself was called), cargo-cult (the same test shape pasted across modules whose public surfaces differ), shape-correct stubs that hide real exception classes, skips that the project quietly accepts forever. The rules name the failure modes and bar them.

For test-runner enforcement (the affected-tests gate, which actually runs the tests before allowing a commit) see `[`commit`](commit/SKILL.md)` step 4. For mechanical scanning of test files for stylistic fingerprints, see `[`detect-ai-fingerprints`](detect-ai-fingerprints/SKILL.md)`.

## The test-writing rules

**writing-tests:1. Tests must fail if the production behaviour breaks, and tests must import the module they claim to test.**

Before merging any test, ask: "If I reverted the implementation, would this test go red?" If the answer is no or unsure, the test verifies the mock setup, not the code. Delete or rewrite.

Necessary condition: tests must import the module they claim to test. A test that re-implements the production algorithm in the test body is theater regardless of what it asserts. Check at PR time: grep for `from <project-namespace>` in any `test_*.py` file claiming to cover production code.

**Retroactive-fix corollary (v2.3.1).** When a Tier-3 rule is applied retroactively to landed code, tests that asserted the now-banned behaviour fail and must be updated, not deleted. The author's writing-tests:1 check ("would this go red on revert?") passed at original-author time because the test was designed for the now-banned implementation; correctness against the implementation does not equal correctness against the rule. Author-time correctness != rule-time correctness; rules win on conflict.

The fix-exercise commit that touches such a test must (a) rename the test to reflect the corrected assertion (`test_returns_none_on_exception` -> `test_propagates_transport_errors_instead_of_swallowing`); (b) cite the rule that drove the test change in the test docstring or commit message body, so the audit trail shows test-vs-rule resolution explicitly; (c) NOT delete the test outright. The test's intent ("behaviour X happens") becomes "rule-compliant behaviour X' happens" at the same coverage level.

The corollary's three-step recipe (rename / cite rule / preserve test) has been validated reproducibly: instances at siege_utilities PR #478 (engine-abstraction silent-swallow, two test renames) and PR #484 (credential security domain silent-swallow, two test renames) confirm the discipline transfers across module shapes. Worth noting: the corollary is self-validating before it ships as a rule. Operators converged on the recipe in PR #484 against the unshipped rule, suggesting the discipline is intuitive enough that experienced operators apply it without the rule needing to exist.

**Self-validation strengthening (v2.4.0).** Recurrence 2 of the self-validation observation now confirmed: PR #489 (v2.3.1 fix exercise) is the third independent instance of an experienced operator applying the rename / cite-rule / preserve recipe organically without consulting rule text. Three samples across three module shapes (engine-abstraction, credential-security, output-generator) cross the three-samples-before-ship threshold for the framing itself: operators with the framework internalized converge on the recipe in real fix exercises against unshipped or shipped rules. The discipline is intuitive, not learned. The body extension's "experienced operators apply it organically" framing is empirically validated; future rule designs should consider this signal when deciding whether a candidate corollary needs explicit ratification or can ship as a body extension to an existing rule.

**writing-tests:2. No cargo-culted patterns across modules.**

When writing tests for multiple similar targets (five API connectors, three storage backends), do not copy-modify the same shape across them. Look at each target's actual public surface and write tests that exercise its specific behaviour. The Vista Social retry logic deserves retry tests; the Snowflake connector does not need fake retry tests just because Vista Social had them.

This rule applies primarily to writing tests but also applies to writing modules with similar shapes. When the failure mode is "production modules with the same scaffolding regardless of what they actually do," see `[`writing-code`](_writing-code-rules.md)` for the code-side application of the same discipline.

**writing-tests:3. Skip messages must name the remediation.**

`pytest.skip("X not installed")` is not actionable. `pytest.skip("install X in this interpreter to run, see docs/setup.md")` is. A skip that does not tell the reader what to do to unskip is a skip the project quietly accepts forever. Same for `pytest.xfail`, `unittest.skipIf`, and any conditional `return` that bypasses a test body: name what the reader changes to make the test run.

Mechanical: `[`detect-ai-fingerprints`](detect-ai-fingerprints/SKILL.md)` scans `.py` files for `pytest.skip(...)` family calls whose message lacks an actionable verb plus an identifier-shaped token.

**writing-tests:4. Mock fidelity.**

When mocking an external library (a third-party package on PyPI or equivalent registry, with its own exception hierarchy and response shapes; not `unittest.mock` of stdlib internals):

- Use the library's real exception classes via `from <pkg>.exceptions import X`, not `Exception` reassignment.
- At least one test in the module must use a fixture built from a real response captured from the library (recorded once, committed as JSON), not a hand-rolled stub.
- Every `MagicMock()` and `Mock()` instantiation that stands in for an external-library object must pass either `spec=<RealClass>` (rejects calls to non-existent methods), `spec_set=<RealClass>` (stricter; rejects attribute writes too), or an explicit `# noqa: writing-tests:4-spec` inline comment with a rationale naming why the real class cannot be used.

The session's worst case: a Facebook test fed a plain dict where the SDK returns `AbstractObject`. The test read correctly; the mock just was not the real thing, so production-only `AttributeError` did not surface. `MagicMock(spec=AdAccount)` would have caught the divergence.

Forward-only on existing connector tests; new connector tests must comply.

**writing-tests:5. Every `except` block in production code is exercised by a test that forces it to fire.**

The test must induce the exception class the handler catches (via dependency injection, monkeypatching, or a real-but-failing input), then assert on the handler's behaviour: the return value, the re-raised exception, the audit-log entry, the typed-failure result. Smoke tests that exercise only the happy path do not count.

Two-line acceptance check at review time: grep for `except` in the diff; for each match, grep test files in the same PR for a test that either (i) names the same exception class via `pytest.raises(<ExcClass>)`, `assertRaises(<ExcClass>)`, or `with raises(<ExcClass>)`, or (ii) calls a fixture or monkeypatch that the test docstring or fixture body documents as inducing the handler's exception. Naming the exception class is the bar; happy-path tests that incidentally exercise the wrapped call do not count.

Forward-only on existing handlers. New `except` blocks in any PR must comply from day one. Existing untested handlers are eligible for promotion to `LESSONS.md` as discovery surfaces them; bulk-backfilling is out of scope.

Two carve-outs:
(a) `except` in `finally`-cleanup code that is purely best-effort (closes a file, removes a temp directory) where the failure is documented as ignorable in the handler comment.
(b) `except` in `__del__` or signal handlers where induction in a test is not safe.

Both carve-outs require a one-line comment naming why no test exists. Without the comment, the handler counts as untested.

The session's concrete instance: the gazetteer Census backend caught `requests.exceptions.RequestException` and fell back to TIGERWeb, but no test forced the Census request to fail. The fallback shape was assumed correct because the happy path returned the same data shape; in practice the fallback path returned a different schema. Mechanical detection is partial (cross-file evidence; tracked at upstream issue #56 for v1.6.2); judgment-enforced via `[`code-review`](code-review/SKILL.md)` until the scanner enhancement lands. Pairs with `[`writing-code`](_writing-code-rules.md)` writing-code:7 (silent error swallowing): writing-code:7 requires a defined handler shape; writing-tests:5 requires a test that proves the handler does what the shape claims.

## Override

These rules are mandatory. No `[test-skip]` override. The rule-7 grep ("test files importing their module under test") and the rule-15 skip-message check land in `[`detect-ai-fingerprints`](detect-ai-fingerprints/SKILL.md)` as mechanical enforcement; the mock-fidelity rule lands as `[`code-review`](code-review/SKILL.md)` judgment until project-namespace detection for the mechanical check is built.

## Cross-references

- `[`commit`](commit/SKILL.md)` step 4 (affected-tests gate) is the mechanical enforcement of writing-tests:1: tests covering the touched code must run and pass before the commit lands. See `[`writing-code`](_writing-code-rules.md)` writing-code:5 (no hypothetical code) for the rule the gate enforces.
- `[`writing-code`](_writing-code-rules.md)` writing-code:3 (no speculative abstractions) is the sibling discipline on the code side; helpers and base classes are introduced only when a second caller already exists. The test-side application here covers fixtures.
- `[`writing-claims`](_writing-claims-rules.md)` rules apply to claims a test makes about coverage ("this test covers all four connectors") and to commit/PR messages that describe what the tests do.

## Migration note (v2.0.x only)

This file is derived from rules 7, 8, 15, 16, and 19 of the deprecated `_no-ai-fingerprints-rules.md`, plus the R-23 mock-spec extension landed inside v2.0.0. Old rule 19 (untested exception handlers, shipped in v1.6.1) becomes writing-tests:5 here. See `CHANGELOG.md` for the v2.0.0 migration table. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in tests, fixtures, commits, or comments.
