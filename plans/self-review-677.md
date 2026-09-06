---
ticket_refs:
  - siege-analytics/claude-configs-public#677
  - siege-analytics/claude-configs-public#668
  - siege-analytics/claude-configs-public#655
---

# Self-review: PR for #677 (#668 P0-2: gh failure silently kills probe)

## Assumptions

Working as: software engineer
Domain: probe helper (scripts/probe/_common.sh, _probe_file_infra_ticket function)
Goal source: siege-analytics/claude-configs-public#677 (Part-of: #668 / #655)
Pre-author-inventory: `grep -n 'gh issue create' scripts/probe/_common.sh` returned line 140. The previous code used `local url` on its own line followed by `url=$(gh ... 2>/dev/null | tail -1)`. Under `set -e` (which _common.sh:29 sets), a non-zero gh aborted the function before _probe_emit_json ran; caller saw empty stdout -> probe="unknown" -> false-coverage. Verified by reading _common.sh's shebang + set line.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: eliminates a P0 false-coverage class where a live gh failure (auth, network, label missing, rate limit) produced empty probe stdout instead of a distinct status, letting the consumer render a stub with no BLOCKED_BY entry — the exact "false coverage" mode SKILL.md:15 says the probe exists to prevent. After this PR, gh failure emits `status=escalation-failed` with the gh stderr captured, and exits 79 (distinct from 78 blocked-on-infra).

## Trivial-against-state declaration

Reason: single-function edit in one shell file + one new test scenario in the sibling _test file. No data/config/topology surface.
Evidence: `git diff --stat` shows scripts/probe/_common.sh + scripts/probe/_test_probe_common.sh + self-review. The _common.sh change is scoped to _probe_file_infra_ticket's gh-invoke block.
Falsification: not trivial if the new status name conflicts with a value elsewhere. Verified: `grep -rn escalation-failed hooks/ scripts/ skills/` pre-fix returns nothing.

## Trivial-investigation declaration

Reason: #677 named the exact design (capture stdout+stderr into one buffer, keep exit code, emit distinct status/exit 79). No discovery required.
Cannot produce error: the added branch fires only on gh non-zero exit. Existing gh success path unchanged (still exits 78 with blocked-on-infra).
Evidence: `bash scripts/probe/_test_probe_common.sh` returns "5 passed, 0 failed" including the new AC5 scenario (gh failure produces escalation-failed / exit 79).
Falsification: not trivial if the new status emits invalid JSON. Verified by test AC5 which pipes probe_stdout to `python3 -c 'import json,sys; json.loads(sys.stdin.read())'` and asserts no ValueError.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n scripts/probe/_common.sh` -> exit 0; same for _test_probe_common.sh
- Gate 2 (tests): `bash scripts/probe/_test_probe_common.sh` -> "5 passed, 0 failed" (was 4/0 pre-#677)
- Gate 3 (docs): the new code block carries an inline comment naming the failure mode #677 documents
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical code): the escalation-failed emission was tested against a real stubbed gh in AC5. The JSON escaping via `python3 -c 'import sys, json; print(json.dumps(sys.stdin.read()[:500]))'` was tested by observing valid JSON output in the AC5 subshell.
- writing-code:7 (no silent swallow): the previous code redirected stderr to /dev/null (a silent swallow). The new code captures stderr in gh_out and echoes a truncated form via the reason field. No silent swallow.
- writing-tests:1 (tests fail on revert): AC5 asserts three properties (exit 79, status=escalation-failed, reason field present); reverting either the exit-code change or the status-string change fails the test.
- writing-tests:5 (every except-block exercised): no new except blocks; the shell code doesn't use except.
- writing-claims:8 (specific counts): "5/5 pass at HEAD" — verified by test-run output.

## Lead review

- Junior solved the stated goal: yes. AC1 satisfied (gh failure emits escalation-failed with exit 79 and reason from stderr). AC2 (consumer surfaces escalation-failed as Skipped:) requires a consumer change in #661's scaffold hook, which is a SEPARATE PR per the ticket's own "may need a companion PR" clause.
- Junior over-scoped: no. Did not touch #661's consumer.
- Junior under-scoped: AC2 not delivered; deferred to a follow-up on the #661 branch. Rationale: #661 is DESCOPED per PR #692 (the epic-682 rewrite that would have replaced this code). Under DESCOPE, per-defect bash fixes land on top; consumer updates ride the same track. Filing a follow-up ticket to track the AC2 delivery.
- Standards affirmatively met: writing-code:5 (real stubbed-gh test), writing-code:7 (no silent swallow), writing-tests:1 (per-assertion coverage).

## Quantified claims

Claim: "5/5 tests pass."
Verified-by: `bash scripts/probe/_test_probe_common.sh` returns "Summary: 5 passed, 0 failed."

Claim: "grep of escalation-failed pre-fix returns 0 sites."
Verified-by: `grep -rn escalation-failed hooks/ scripts/ skills/` pre-edit returned nothing.

Claim: "AC5 asserts JSON validity."
Verified-by: test scenario body pipes to python3 json.loads; a malformed JSON emission would raise and be reported as FAIL.

## Post-mortem applicability

Not applicable. First-time fix for a P0 finding named in a prior review; no prior shipped fix to revert.
