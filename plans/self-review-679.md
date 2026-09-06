---
ticket_refs:
  - siege-analytics/claude-configs-public#679
  - siege-analytics/claude-configs-public#668
  - siege-analytics/claude-configs-public#655
---

# Self-review: PR for #679 (tool_install_policy parse) + P1-6 + P2-1 closeouts

## Assumptions

Working as: software engineer
Domain: probe policy resolver (scripts/probe/_common.sh, _probe_resolve_policy)
Goal source: siege-analytics/claude-configs-public#679 (Part-of: #668 / #655)
Pre-author-inventory: `grep -n _probe_resolve_policy scripts/probe/_common.sh` returned lines 36 and 185; the extractor at line 48 stripped only the `tool_install_policy:` prefix without cleaning trailing content. Confirmed the failure by writing `tool_install_policy: allow  # ephemeral CI runner\n` to a fixture PROJECT.md and observing `resolved: [allow  # ephemeral CI runner]` from a bare-parse trace.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: eliminates a P0 silent-downgrade class where a user copying the SKILL.md-documented value verbatim (with inline comment) got a policy that fell through to block instead of allowing. Also closes #668 P1-6 (invalid value silently downgrades) with a stderr diagnostic + explicit block treatment, and #668 P2-1 (CRLF breaks parsing) via `tr -d '\r'`.

## Trivial-against-state declaration

Reason: single-function edit in one shell file + 3 new test scenarios. No data/config/topology surface.
Evidence: `git diff --stat` shows scripts/probe/_common.sh (7 line change to the extractor) + scripts/probe/_test_probe_common.sh (3 new test functions + 3 lines invoking them) + self-review. Only _probe_resolve_policy is touched in _common.sh.
Falsification: not trivial if the new sed pipeline mishandles a legit value. Verified by AC7 (CRLF), AC8 (invalid value with warning), and AC6 (comment-with-value).

## Trivial-investigation declaration

Reason: #679 named the exact design (extended sed pipeline + allowlist validation with stderr diagnostic). Composes-with fields named #668 P1-6 and P2-1 for the same extractor fix. No discovery required.
Cannot produce error: the extractor edit only NARROWS the accepted value set. Any value that would previously have passed as `allow` still passes; comment-suffixed / CRLF / whitespace-trailed forms now also pass; unrecognised values that used to silently degrade now warn loudly.
Evidence: `bash scripts/probe/_test_probe_common.sh` returns "8 passed, 0 failed" (was 5/0 pre-#679).
Falsification: not trivial if the sed pipeline strips content that a legit value would contain. Verified: no policy value legitimately contains `#`, `\r`, or trailing whitespace.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n scripts/probe/_common.sh` -> exit 0; same for _test_probe_common.sh
- Gate 2 (tests): `bash scripts/probe/_test_probe_common.sh` -> "8 passed, 0 failed" (5 pre-#679 + 3 new AC6/7/8)
- Gate 3 (docs): the inline comment on the sed pipeline names #679, #668 P0-4, #668 P2-1, and #668 P1-6 so a future reader sees which findings the edit closes
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): each new test writes a real fixture PROJECT.md, sources _common.sh, calls _probe_resolve_policy, and asserts on the resolved value. Not extrapolated.
- writing-code:7 (no silent swallow): the P1-6 half now emits a stderr diagnostic before treating unrecognised values as block. Not silent.
- writing-tests:1 (tests fail on revert): removing the `s/[[:space:]]*#.*$//` pipeline stage fails AC6 (comment-suffixed value would resolve as `allow  # ...`); removing `tr -d '\r'` fails AC7; removing the case validate-then-warn branch fails AC8.
- writing-claims:8 (specific counts): "8/8 pass at HEAD" — verified via test-run output.

## Lead review

- Junior solved the stated goal: yes. AC1 (comment) + AC2 (CRLF) + closeouts on P1-6 (invalid value diagnostic) and P2-1 (CRLF, same fix).
- Junior over-scoped: no. Did not extend the fix to other config files.
- Junior under-scoped: no. The composes-with list from the ticket (#668 P1-6 and P2-1) is covered.
- Standards affirmatively met: writing-code:5 (real fixture verification), writing-code:7 (loud on invalid), writing-tests:1 (per-mode assertions).

## Quantified claims

Claim: "8/8 tests pass."
Verified-by: `bash scripts/probe/_test_probe_common.sh` returns "Summary: 8 passed, 0 failed."

Claim: "policy=allow with inline comment parses to allow (not silent block)."
Verified-by: AC6 test scenario writes exactly `tool_install_policy: allow  # ephemeral CI runner\n` and asserts the resolved value is `allow`. Manual trace before test-run confirmed the pre-fix behavior was `[allow  # ephemeral CI runner]` (unchanged content) which fell through the case to block.

Claim: "CRLF line endings do not break parsing."
Verified-by: AC7 writes `tool_install_policy: prompt\r\n` and asserts resolved value is `prompt`.

## Post-mortem applicability

Not applicable. First-time fix for a P0/P1/P2 cluster named in a prior review; no prior shipped fix to revert.

Composes-with per ticket: closes #668 P0-4 (this ticket), #668 P1-6 (invalid value silently downgrades — covered by AC8 diagnostic), and #668 P2-1 (CRLF — covered by AC7). All three landed in one PR because they share the extractor.
