---
ticket_refs:
  - siege-analytics/claude-configs-public#766
---

# Self-review: PR for #766 B-1 + m-7 (scan.sh dispatcher fixes)

## Assumptions

Working as: software engineer
Domain: bash dispatcher script skills/detect-ai-fingerprints/scan.sh
Goal source: siege-analytics/claude-configs-public#766 findings B-1 (blocker) + m-7 (minor)
Pre-author-inventory: scan.sh:380 grep-cE regex tallies violations from scan_ast.py's output; grew organically as new detectors landed (writing-code:7 in v2.3.1.1, writing-code:9 in v2.2.0, writing-code:15 in v2.6.0). Recent detectors writing-code:4 (django), writing-code:8, writing-tests:5 landed without matching regex updates. Scan.sh:391 comment carried a `See issue #60` history-reference that matches its own writing-code:2 regex.

Investigate-artifact: TRIVIAL (see below)
Pre-mortem-artifact: TRIVIAL (see below)
Hostile-review-artifact: Claude Opus 4.7 Round 2 review, session 260906-fit-whale, delivered B-1 as blocker + m-7 as minor. Both reproduced locally.
Project-contribution: closes the exit-code drift that caused scan.sh to return 0 when writing-code:4, writing-code:8, or writing-tests:5 emitted; adds a regression test that pins the rule set to the counter regex; removes the self-flagging comment.

## Trivial-against-state declaration

Category: local-only
Cannot produce error: one-line regex change in scan.sh + one comment removal + one new test file. No runtime code path touched in production consumers.
Evidence: `git diff --stat` shows scan.sh + new test_scan_sh_exit_code.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: bash regex + shell test; no external state (data, config, cluster, plan, version) contacted.
Evidence: `git diff --stat` shows only skills/detect-ai-fingerprints/scan.sh, skills/detect-ai-fingerprints/test_scan_sh_exit_code.sh, plans/self-review-766-b1-m7.md.
Falsification: NOT trivial if any external resource is read or written. Verified: test uses mktemp -d only.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n scan.sh` -> ok; `bash -n test_scan_sh_exit_code.sh` -> ok
- Gate 2 (tests): `bash test_scan_sh_exit_code.sh` -> "10 passed, 0 failed" (7 rule-tokens match + 3 non-rule negatives don't). Regressions: writing-code:8 test unchanged 12/12; writing-tests:5 unchanged 12/12; rule-citations unchanged PASS.
- Gate 3 (docs): counter-regex line now carries an inline comment naming the rule set the AST scanner emits and citing B-1 by ticket.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:2 (no history references in code comments): the `See issue #60` comment is removed. m-7 is closed.
- writing-code:5 (no hypothetical): regex change verified by test against actual emission tokens.
- writing-tests:1 (tests fail on revert): reverting the regex expansion breaks 3 of the 7 rule-token match cases in the new test.
- writing-claims:8 (specific counts): "10 passed, 0 failed" verified inline.

## Lead review

- Junior solved the stated goal: yes. Blocker B-1 fixed; minor m-7 fixed; a regression test pins the rule set to the counter regex so future rule additions surface the drift.
- Junior over-scoped: no. M-1, M-2, M-3 are separate PRs under epic #766.
- Junior under-scoped: the regression test extracts the regex from scan.sh via grep-and-sed. That's fragile if the scan.sh line format changes (e.g., someone renames `ast_n` to something else). Author-time decision: a robust test would parse scan.sh via bash's own parser, which is out of proportion for the risk. If the extraction fails, the test emits `bad "extract counter regex"` diagnostic and exits early — not a silent regression.
- Standards affirmatively met: writing-code:2, writing-code:5, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "10/10 pass in the new test (7 rule tokens + 3 non-rule negatives)."
Verified-by: `bash skills/detect-ai-fingerprints/test_scan_sh_exit_code.sh` -> "Results: 10 passed, 0 failed", rc=0.

Claim: "no regression on the three existing scanner test scripts."
Verified-by: `bash test_writing_code_8.sh` -> 12/12 unchanged; `bash test_writing_tests_5.sh` -> 12/12 unchanged; `bash test_rule_citations.sh` -> PASS unchanged.

## Post-error revision

Triggered by: Claude Opus 4.7 hostile review Round 2, session 260906-fit-whale, 2026-09-06, finding B-1.
Observed: `printf 'f.py:1:writing-code-8: x\nf.py:2:writing-tests-5: y\n' | grep -cE ':writing-(code-(7|9|15)|releases-3)'` returns 0 — the two emissions match no group. Callers taking scan.sh's exit code as authoritative (commit hooks, CI gates) treated these emissions as clean.
Falsified assumption: prior PRs (#752 writing-code:8, #754 writing-tests:5) added detector functions to scan_ast.py + updated scan_ast.py's own docstring, but did NOT update scan.sh's counting regex. The assumption was that the scanner and its dispatcher would evolve together via review discipline; the review discipline for those two PRs did not extend to scan.sh.
Revised model: any PR that adds a new rule token to scan_ast.py's emission surface must ALSO touch scan.sh's counting regex, and this cross-file coupling must be enforced by a test rather than by hoping the reviewer catches it. This PR adds `test_scan_sh_exit_code.sh` as that enforcement. Future rule additions will need to add a new fixture-and-expected line to that test, which surfaces the coupling.
Implication: retroactively verify scan.sh's other regex touchpoints (prose checks, ignore globs, ast_files build) also stay in sync with scan_ast.py. Not in scope for this PR; a follow-up sweep is filed under #766 F1e.
