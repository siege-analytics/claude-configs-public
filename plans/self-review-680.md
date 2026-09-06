---
ticket_refs:
  - siege-analytics/claude-configs-public#680
  - siege-analytics/claude-configs-public#668
  - siege-analytics/claude-configs-public#655
---

# Self-review: PR for #680 (dedupe infra tickets)

## Assumptions

Working as: software engineer
Domain: probe helper (_probe_file_infra_ticket, dedupe branch)
Goal source: siege-analytics/claude-configs-public#680 (Part-of: #668 / #655)
Pre-author-inventory: verified _probe_file_infra_ticket at HEAD (post-#677 fix) has no dedupe; consumer per-Automation-block invocation from ticket #661's scaffold hook calls the probe once per AC. Repo is public; five identical infra tickets per 5-AC decomposition on a machine without the tool.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: eliminates a P0 duplicate-public-issue class. Before this PR, a ticket decomposed into N pytest-backed ACs filed N identical `infra: install pytest for <ticket>` public issues on machines without pytest. After this PR, the probe searches for an existing OPEN issue with the same title before filing; a match returns the existing URL with `reused=true` and does not file a new one.

## Trivial-against-state declaration

Reason: single-function extension (added a search-first branch before the existing create branch); 1 new test scenario.
Evidence: `git diff --stat` shows scripts/probe/_common.sh (dedupe branch added before the #677 gh-invoke), scripts/probe/_test_probe_common.sh (extended gh stub + AC9 scenario), plans/self-review-680.md.
Falsification: not trivial if the gh-search subcommand behaves differently than assumed. Verified against `gh issue list --help` shape: `--search 'in:title "..."'` is a documented syntax; `--json number,title --jq` filters to matching title.

## Trivial-investigation declaration

Reason: #680 named the exact design (search-first, reuse if match, gh view for URL). No discovery required.
Cannot produce error: the dedupe branch only ADDS a return path when a match is found. When no match, the flow falls through to the existing create branch (post-#677). Idempotent: repeated probe invocations on the same missing tool all resolve to the same reused URL.
Evidence: `bash scripts/probe/_test_probe_common.sh` returns "9 passed, 0 failed" (was 8/0 pre-#680).
Falsification: not trivial if the dedupe-branch fires on a stale/closed ticket. Verified: gh issue list uses --state open so closed tickets are ignored (a re-opened ticket would legitimately be the target).

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n scripts/probe/_common.sh` -> exit 0
- Gate 2 (tests): `bash scripts/probe/_test_probe_common.sh` -> "9 passed, 0 failed" (5 pre-#677 + 3 for #679 + 1 for #680)
- Gate 3 (docs): the inline comment on the dedupe branch names #680 and the failure mode (per-Automation-block invocation)
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): the gh subcommand stubs in AC9 return real-shaped payloads (issue number, URL); the assertion is on the probe stdout and the assertion that gh issue create is never called.
- writing-code:7 (no silent swallow): dedupe branch on failure (gh list returns error) fails-open — flow falls through to create. That's not a silent swallow because the create branch has its own #677 escalation-failed handling.
- writing-tests:1 (tests fail on revert): AC9 asserts BOTH the reused URL AND that create was never called (the stub returns exit 99 with an error message if create fires); reverting the dedupe branch fires create and fails the test.
- writing-claims:8 (specific counts): "9/9 pass at HEAD" — verified via test-run output.

## Lead review

- Junior solved the stated goal: probe-side AC1 (second call reuses first infra ticket) delivered. AC2 (no duplicate filed across two sequential probe runs) is covered by AC9's stub assertion.
- Junior over-scoped: no. Did not touch the consumer-side cache (#661 scaffold hook) per ticket's own "separate ticket, out of scope here".
- Junior under-scoped: no. Consumer-side cache is a separate track under DESCOPE per PR #692.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1.

## Quantified claims

Claim: "9/9 tests pass."
Verified-by: `bash scripts/probe/_test_probe_common.sh` returns "Summary: 9 passed, 0 failed."

Claim: "dedupe branch prevents gh issue create when match exists."
Verified-by: AC9's stub returns exit 99 with error message if gh issue create is called; test-run does not observe the error, meaning create was not called.

## Post-mortem applicability

Not applicable. First-time fix for P0 finding; no prior shipped behavior to revert.
