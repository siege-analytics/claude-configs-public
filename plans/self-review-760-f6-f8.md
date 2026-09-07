---
ticket_refs:
  - siege-analytics/claude-configs-public#760
---

# Self-review: PR for #760 F6-F8 (writing-tests:5 detector soundness) + F9 correction

## Assumptions

Working as: software engineer
Domain: Python AST scanner (skills/detect-ai-fingerprints/scan_ast.py) — writing-tests:5 detector
Goal source: siege-analytics/claude-configs-public#760 findings F6, F7, F8, F9 (Codex hostile review, 2026-09-06, session 260906-ivory-finch)
Pre-author-inventory: `check_writing_tests_5` and helpers `_test_files_for_source`, `_test_file_covers_exception`, `_is_carveout_handler` shipped in PR #754 with three unsoundness bugs (missed namespaced test layouts; substring grep on test file text accepted comment TODOs as coverage; bare `noqa: writing-tests-5` without a reason accepted as carve-out). F9 was a truthfulness gap in self-review-56 (claim: "no except blocks in the new code"; code has `except (OSError, UnicodeDecodeError): return False` in `_test_file_covers_exception`).

Investigate-artifact: TRIVIAL (see below)
Pre-mortem-artifact: TRIVIAL (see below)
Hostile-review-artifact: Codex session 260906-ivory-finch delivered the findings this PR fixes. All reproductions rerun locally before this fix.
Project-contribution: makes the writing-tests:5 detector actually enforce the rule as documented. Also converts the substring grep in `_test_file_covers_exception` to real AST parsing, which addresses F7 and F9 in the same edit — the AST version cannot be fooled by comments, and the read failure now emits a scanner diagnostic (writing-code:11 no-silent-process compliance).

## Trivial-against-state declaration

Category: local-only
Cannot produce error: single-file Python change + additive shell test scenarios.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_tests_5.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST scanner logic + additive test fixtures created and torn down in a mktemp scratch dir. No external service, DB, cluster, config touched.
Evidence: `git diff --stat` shows the three files. grep for `subprocess|requests|urllib|open(` in the diff shows only the existing `read_text` calls (which raise handled exceptions with stderr diagnostic).
Falsification: NOT trivial if any external resource is written or read outside the test's mktemp -d. Verified.

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('skills/detect-ai-fingerprints/scan_ast.py').read())"` -> ok
- Gate 2 (tests): `bash test_writing_tests_5.sh` -> "12 passed, 0 failed" (6 original + 6 new). Regressions: `bash test_writing_code_8.sh` -> unchanged 12/12, `bash test_rule_citations.sh` -> unchanged PASS.
- Gate 3 (docs): scanner code comments updated to reference F6/F7/F8 by ticket. `_test_file_covers_exception` docstring rewritten to name the AST semantics.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): each fix bound to a concrete Codex reproduction rerun locally.
- writing-code:7 (no silent swallow): the `except (OSError, UnicodeDecodeError)` in the new `_test_ast_covers_exception` now emits a `scan-ast-warning:` diagnostic to stderr before returning False. That satisfies writing-code:7's "audit-log the failure with full context" clause — the caller doesn't disappear silently, the user sees which test file was unreadable and why.
- writing-tests:1 (tests fail on revert): reverting the F6 fix causes fixture (g) to fire → fail; reverting F7 causes (h) to go silent → fail; reverting F8 causes (j) to go silent → fail. Each fix has a bound test.
- writing-claims:8 (specific counts): "12 passed" — verified inline; 6 old + 6 new.

## Lead review

- Junior solved the stated goal: yes. F6 = namespaced test path discovery. F7 = AST-based coverage check. F8 = require noqa reason via regex. F9 = replaced substring grep with AST, silent-swallow re-authored as loud diagnostic.
- Junior over-scoped: no. F11 (author-self-application: repo self-scan emits violations) is separately filed under this epic and needs operator input on ratchet-vs-bulk-fix.
- Junior under-scoped: `_test_ast_covers_exception` recognizes `raises`, `assertRaises`, and dotted forms (`pytest.raises`, `self.assertRaises`). It does NOT yet recognize alternative test frameworks (`nose.tools.raises` decorator; `hypothesis @given` custom exception assertions). Deferred to a follow-up ticket if a downstream consumer surfaces the need.
- Standards affirmatively met: writing-code:5, writing-code:7 (loud-log now), writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "12/12 test scenarios pass, 6 original + 6 new Codex lock-ins."
Verified-by: `bash skills/detect-ai-fingerprints/test_writing_tests_5.sh` returns "Results: 12 passed, 0 failed", rc=0.

Claim: "no regression on test_writing_code_8.sh or test_rule_citations.sh."
Verified-by: both scripts run unchanged.

## Post-error revision

Triggered by: Codex hostile review, session 260906-ivory-finch, 2026-09-06, findings F6-F8 + F9.
Observed: three reproductions surfaced unsoundness in the detector (comment coverage, missed test layout, bare noqa) and one factual falsification in self-review-56 ("no except blocks in the new code").
Falsified assumptions:
- self-review-56 claim: "no except blocks in the new code" — false. `_test_file_covers_exception` had `except (OSError, UnicodeDecodeError): return False`.
- self-review-56 line 49: "handles the common conventions ... more exotic layouts (pytest custom collect hooks, tox nested envs) are deferred" — namespaced `tests/pkg/sub/test_thing.py` isn't exotic, it's the standard pytest layout; the deferral was miscalibrated.
- self-review-56 Trivial-investigation: "detection design mirrors that shape" — the substring-grep detection did NOT mirror the rule shape (rule requires a call that INDUCES the exception; comment cannot induce anything).
- self-review-56 lead-review under-scoped: "auto-detecting finally-cleanup context adds complexity for a case where the author is already required to write a comment" — assumed the noqa marker WAS the required comment; rule text is stricter: the noqa needs a reason token.

Revised model:
- Test-file discovery must mirror source path relative to repo root, not just the immediate parent directory name.
- Coverage predicates over source text must be AST-based when the underlying rule requires an actionable call (comments and docstrings do not induce runtime state).
- Any regex that gates a rule via a `# noqa:` opt-out must additionally require a reason token — the opt-out IS a "this doesn't apply" claim per writing-rules:4.
- Scanner helpers that swallow exceptions on read failure must emit a diagnostic; the scanner itself is a writing-code:7 authority and must apply the rule to its own code.

Implication: retroactively update self-review-56.md is out of scope for this PR (self-reviews are historical artifacts). The Post-error revision block IS the correction of record. Any future author of similar rule detectors must: enumerate every documented rule shape (F5 category), design the coverage predicate at the AST level not the text level (F7 category), and gate opt-outs with reason-token regex (F8 category).
