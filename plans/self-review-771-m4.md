---
ticket_refs:
  - siege-analytics/claude-configs-public#771
---

# Self-review: PR for #771 m-4 (writing-code:15 alias handling + bare-name)

## Assumptions

Working as: software engineer
Domain: writing-code:15 detector — imports resolution
Goal source: siege-analytics/claude-configs-public#771 m-4
Pre-author-inventory: `_matches_unbounded_io` operated on bare Attribute chains. `import subprocess as sp; sp.run(...)` produced chain `('sp', 'run')` which is not in UNBOUNDED_IO_SURFACES. Bare-name calls `from urllib.request import urlopen; urlopen(...)` produced ast.Name calls that the detector rejected outright. Aliased `from subprocess import Popen as P; P().wait()` failed the M-2 special case because the popen_name check compared `P` to `"Popen"` literally.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: Round 2 m-4, session 260906-fit-whale.
Project-contribution: `_extract_import_aliases` builds per-module module_aliases + from_imports maps. `_matches_unbounded_io` now accepts them, rewrites chain leading segment through module_aliases, resolves bare Name via from_imports, and resolves aliased Popen via from_imports in the M-2 special case.

## Trivial-against-state declaration

Category: local-only
Cannot produce error: additive helper + optional-kwargs on `_matches_unbounded_io` + 6 new fixtures.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_code_15.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST walk of Import/ImportFrom nodes.
Evidence: no external contact.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate evidence:
- Gate 1 (syntax): python3 ast.parse -> ok
- Gate 2 (tests): bash test_writing_code_15.sh -> "18 passed, 0 failed" (12 prior + 6 m-4 lock-ins). Regressions: writing-code:7 8/8, writing-code:8 12/12, writing-tests:5 20/20, scan_sh_exit_code 10/10, is_test_path 13/13, rule_citations PASS.
- Gate 3 (docs): `_extract_import_aliases` docstring documents the two maps + shapes each handles. `_matches_unbounded_io` docstring extended to name m-4 by ticket and the two resolution paths (chain-leading rewrite + bare-Name lookup).
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5: verified against 4 fire cases + 2 silent regression checks.
- writing-code:7: no except handlers added.
- writing-tests:1: reverting alias resolution makes fixtures (m), (o), (p) go silent → fail.
- writing-claims:8: "18 passed" verified.

## Lead review

- Junior solved the stated goal: yes. Aliased imports + bare-name from-imports + aliased Popen all resolve.
- Junior over-scoped: no. Instance-method resolution (`p = Popen(); p.wait()`) is out of scope — requires flow analysis (variable-binding tracker), which is a distinct problem. Filed as a future ticket if surfaced.
- Junior under-scoped: complex re-exports (`from urllib import request; request.urlopen(...)`) resolve because `_attr_chain` produces `('request', 'urlopen')` which matches. But `import urllib; urllib.request.urlopen(...)` also matches via the existing chain rightmost-two check. Covered.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "18/18 pass on writing-code:15 (12 prior + 6 m-4 lock-ins)."
Verified-by: bash test_writing_code_15.sh -> "Results: 18 passed, 0 failed", rc=0.

Claim: "no false positives on unrelated modules' bare-name from-imports."
Verified-by: fixture (q) uses `from myapi import get; get(...)` — silent under new detector.
