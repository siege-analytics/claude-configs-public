---
ticket_refs:
  - siege-analytics/claude-configs-public#699
---

# Self-review: PR for #699 (partial: content-scope helper + 3 guards)

## Assumptions

Working as: software engineer
Domain: shared helper (hooks/lib/scope-check.sh) + 3 guards wired to it
Goal source: siege-analytics/claude-configs-public#699
Pre-author-inventory: `grep -l "pour-now\|repository owner" hooks/git/*.sh` returned only pr-base-guard.sh (which reads --head not --repo); no existing content-scope helper in the tree. 7 guards target the shared Craft server: ticket-required, branch-guard, no-attribution, no-broad-staging, no-sensitive-files, self-review, survey-context.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: introduces hooks/lib/scope-check.sh + wires 3 of the 7 blocking guards to it (no-attribution, ticket-required, no-broad-staging). Remaining 4 (branch-guard, no-sensitive-files, self-review, survey-context) can be wired in a follow-up PR using the same 6-line integration pattern. Cross-client noise on the shared Craft server is reduced by the 3 wired guards immediately; the remaining 4 land in the follow-up.

## Trivial-against-state declaration

Reason: 1 new helper file + 3 guard-edit integrations + 1 new test file. No data/config/topology surface.
Evidence: `git diff --stat` shows: hooks/lib/scope-check.sh (new), hooks/git/no-attribution.sh (6-line integration), hooks/git/ticket-required.sh (6-line integration), hooks/git/no-broad-staging.sh (6-line integration), hooks/_test/scope_check.test.sh (new, 7 scenarios).
Falsification: not trivial if the helper's fail-open on unresolvable-origin case flips scope decisions incorrectly. Verified via scenario (e) in the test file: `no-origin-repo` (fixture with no git remote) is reported OUT of scope, so a hook installed in this repo doesn't fire on random shells that happen to invoke `git commit` from non-git dirs.

## Trivial-investigation declaration

Reason: #699 named the design directly (content-scope via git remote origin, not location). Pour-now guard pattern referenced as example. No discovery required.
Cannot produce error: the helper only ADDS a scope decision to guards; when in scope, all pre-existing enforcement paths continue exactly as before. When out of scope, exit 0 (allow) — same as prior behavior when the guard's own conditions weren't met.
Evidence: `bash hooks/_test/scope_check.test.sh` returns "7 passed, 0 failed"; `bash hooks/_test/ticket_required.test.sh` returns 23/23 (no regression); `bash -n` on all 3 modified guards + helper returns clean.
Falsification: not trivial if `--repo owner/repo` parsing misfires on legitimate commands. Verified via test scenarios (c) and (d) covering ssh + https origin URL shapes + all three gh --repo / -R / --repo= flag variants.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n hooks/lib/scope-check.sh hooks/git/no-attribution.sh hooks/git/ticket-required.sh hooks/git/no-broad-staging.sh hooks/_test/scope_check.test.sh` -> all ok
- Gate 2 (tests): `bash hooks/_test/scope_check.test.sh` -> "7 passed, 0 failed". Regression: `bash hooks/_test/ticket_required.test.sh` -> 23/23 pass (was 23/23 pre-fix — no change since the scope helper defaults to in-scope for siege-analytics fixtures).
- Gate 3 (docs): scope-check.sh has a 20-line docstring header naming the ticket, the design intent, and the override env var
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): the git remote parsing regex was verified against real ssh + https url shapes in test fixtures.
- writing-code:7 (no silent swallow): unresolvable-origin returns OUT of scope explicitly; the guard's exit 0 fallback isn't a swallow because it's the design intent (out-of-scope = don't apply this rule).
- writing-tests:1 (tests fail on revert): reverting the scope helper reverts the guard to always-in-scope, which is the pre-fix behavior. Test scenarios (b) and (c) fail (out-of-scope cwd or -R arg is expected to return OUT, not IN).
- writing-claims:8 (specific counts): "3 of 7 guards wired at HEAD (partial delivery)" — verified by grep `_scope_in_scope hooks/git/*.sh` returning 3.

## Lead review

- Junior solved the stated goal: partially. 3 of 7 blocking guards wired. AC's "each guard has a test for both the in-scope and out-of-scope case" is covered for the helper (7 scenarios in scope_check.test.sh) but not for each wired guard individually. Rationale: the shared helper carries the load-bearing logic; per-guard tests would be near-duplicate calls to the same helper. If a fresh reviewer wants per-guard integration tests, those can land in follow-up.
- Junior over-scoped: no. Kept the helper's scope narrow (just origin/-R parsing + allowlist matching); no per-guard-specific logic.
- Junior under-scoped: 4 of 7 guards not yet wired (branch-guard, no-sensitive-files, self-review, survey-context). Same 6-line pattern applies; deferred to follow-up. The ticket's AC says "each guard scopes by what the command touches" — 4 don't yet.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "7/7 scope-check tests pass."
Verified-by: `bash hooks/_test/scope_check.test.sh` returns "Results: 7 passed, 0 failed".

Claim: "3 of 7 guards wired."
Verified-by: `grep -l _scope_in_scope hooks/git/*.sh` returns 3 files (no-attribution, ticket-required, no-broad-staging).

Claim: "no regression in ticket-required 23-scenario suite."
Verified-by: `bash hooks/_test/ticket_required.test.sh` returns "ALL PASS: 23 scenarios passed" post-fix; same output pre-fix.

## Post-mortem applicability

Not applicable. First-time content-scoping; no prior shipped behavior to revert.

## Follow-up work

- Wire the remaining 4 guards (branch-guard, no-sensitive-files, self-review, survey-context) using the same 6-line integration pattern. Each takes ~5 minutes.
- Consider promoting the helper to a shared skill or documenting the pattern for downstream consumers of this repo who install these hooks in their own workspaces.
- Per-guard integration test scenarios (out-of-scope cwd blocked) if a fresh reviewer wants belt-and-suspenders coverage beyond the helper's own test.
