---
ticket_refs:
  - siege-analytics/claude-configs-public#787
---

# Self-review: PR for #787 R3-F1 (writing-code:9 scoped visitor)

## Assumptions

Working as: software engineer
Domain: writing-code:9 detector (silently-dropped parameters)
Goal source: siege-analytics/claude-configs-public#787 R3-F1
Pre-author-inventory: `collect_referenced` walked the ENTIRE function subtree via `ast.walk` and added:
- any `ast.Name` (regardless of Load/Store context; regardless of whether it's in a nested scope)
- any `ast.keyword.arg` name (kwarg NAME literal)
- any `**` spread as `has_kwargs_spread`

Three failure modes:
- F1a: `fn(timeout=10)` inside a wrapper made `timeout` a "kwarg name match" → silent though timeout was dropped.
- F1b: `**kwargs` param + `**kwargs` spread silenced NAMED defaulted parameters (which are bound by name, not in `**kwargs`).
- F1c: nested `def inner(x): return x` inside `def outer(x=1): ...` made outer's `x` appear referenced (the inner name is Store then Load in inner's scope).

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL

## Trivial-against-state declaration

Category: local-only
Cannot produce error: rewrite of `collect_referenced` into scoped `_collect_load_names_in_scope` + updated caller + 5 lock-in fixtures.
Evidence: `git diff --stat`.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST recursion.
Evidence: no external contact.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate 1 (syntax): python3 ast.parse -> ok.
Gate 2 (tests): test_writing_code_9 12/12 (7 prior + 5 R3-F1 lock-ins). Regressions: all 9 other suites unchanged.

Shelf compliance:
- writing-code:5: 5 fixtures verified against real AST inputs.
- writing-code:7: no except handlers.
- writing-tests:1 (tests fail on revert): reverting the scoped walk makes (h), (i), (j) silent.
- writing-claims:8: "12 passed" verified.

## Lead review

- New helper `_collect_load_names_in_scope` returns (names_load_referenced_in_current_scope, captures_locals). The `captures_locals` escape hatch preserves the rare-but-legit `**locals()` forwarder pattern.
- Back-compat: old `collect_referenced` retained as a shim returning empty keywords/spread sets so any external caller that grep'd for the symbol still resolves (but sees no false silencers).
- Comprehension handling: the first generator's iterable is evaluated in the outer scope, so names there count. Rest of comprehension (target + subsequent iterables) is inner-scope and excluded.
- Escape hatch for `**locals()` — rare but appears in decorator libraries; conservative silencing prevents false positives.

Standards met: writing-code:5, writing-tests:1, writing-claims:8.

## Quantified claims

"12/12 pass" — bash test_writing_code_9.sh returns Results: 12 passed, 0 failed, rc=0.
