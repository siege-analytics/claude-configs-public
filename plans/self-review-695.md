---
ticket_refs:
  - siege-analytics/claude-configs-public#695
---

# Self-review: PR for #695 (derived_from: check for cross-artifact drift)

## Assumptions

Working as: software engineer
Domain: scripts/discipline (Python checker + bash test)
Goal source: siege-analytics/claude-configs-public#695
Pre-author-inventory: `ls scripts/discipline/` returned 10+ files (after #691 also landed). No existing derived_from checker. #695 provided the frontmatter shape (`path` + `rev` pairs) and three-outcome design (current / superseded / unresolved).
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: makes cross-artifact drift mechanically checkable. Before this PR, PR #686's two artifacts were pinned to a superseded revision of the fact sheet in nine places for four hostile-review rounds and nobody noticed — because every review checked each artifact against itself. After this PR, an artifact declaring `derived_from:` entries can be checked with one command. Does NOT correct the nine sites (out of scope per ticket); provides the check the correction can be verified against.

## Trivial-against-state declaration

Reason: adds one new script + one new test file under scripts/discipline/. No existing code touched.
Evidence: `git diff --stat` shows 2 new files + 1 self-review. No modifications to existing files.
Falsification: not trivial if the new script conflicts with existing check-* scripts. Verified: `ls scripts/discipline/check-*` shows check-doc-anchors.py, check-post-error-revision.sh, check-self-review.sh, check-trivial-claim.sh, check-citations.py (my #691 addition), and now check-derived-from.py. No naming or behavior overlap.

## Trivial-investigation declaration

Reason: #695 named the design in the ticket body — frontmatter key, three outcomes, script location, non-decisions to defer. No discovery required.
Cannot produce error: reads frontmatter, runs git subprocess, prints outcomes. No writes.
Evidence: `bash scripts/discipline/test_check_derived_from.sh` returns "6 passed, 0 failed" including scenarios for all three outcomes.
Falsification: not trivial if the script produces "current" for an unresolved rev. Verified by scenario (d): rev exists but doesn't touch the path is reported as UNRESOLVED (the earlier version returned CURRENT because `log -1 rev -- path` returns an ancestor; fixed by using `show --name-only` which lists only rev's own changes).

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('scripts/discipline/check-derived-from.py').read())"` -> ok; `bash -n scripts/discipline/test_check_derived_from.sh` -> ok
- Gate 2 (tests): `bash scripts/discipline/test_check_derived_from.sh` -> "6 passed, 0 failed"
- Gate 3 (docs): script docstring at top of file explicitly states "drift is not staleness" per AC4
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): the script's `git show --format= --name-only` semantics were verified by running against the test-repo fixture. The initial implementation used `git log -1 rev -- path` which was a false-positive; scenario (d) caught it; fixed to `git show`.
- writing-tests:1 (tests fail on revert): each of the 6 test scenarios asserts a specific outcome; reverting any of the three outcome branches in classify() would fail one scenario.
- writing-tests:5 (every except-block exercised): the git subprocess timeout except handler in `git()` is not exercised by any test (would require breaking git). Called out; if timeout becomes a real failure mode, follow-up test.
- writing-claims:8 (specific counts): "6 scenarios pass" — verified by direct run above.

## Lead review

- Junior solved the stated goal: yes. Frontmatter parsing + three-outcome classification + fail-closed on any non-current outcome.
- Junior over-scoped: no. Did not correct the 9 sites in PR #686's artifacts (out of scope per ticket AC5: "Correcting the nine sites in epic #682 belongs to PR #686 and is not in scope here"). The ticket's AC5 mentions applying `derived_from:` entries to specific existing artifacts; deferred to PR #686 remediation.
- Junior under-scoped: did not add frontmatter to existing plans/ artifacts. Per AC5 discussion above, that's out-of-scope for this PR.
- Standards affirmatively met: writing-code:5 (verified against real git output), writing-tests:1 (per-outcome assertions), writing-claims:8.

## Quantified claims

Claim: "6 test scenarios pass."
Verified-by: `bash scripts/discipline/test_check_derived_from.sh` returns "Results: 6 passed, 0 failed."

Claim: "the script distinguishes three outcomes."
Verified-by: scenarios (a) current, (b) superseded, (c)+(d) unresolved (rev-not-exist, rev-exists-but-doesnt-touch-path) each pass under the three-outcome model.

Claim: "the script's output states drift is not staleness."
Verified-by: `grep -c 'Drift is not staleness' scripts/discipline/check-derived-from.py` returns >0 in both docstring and the main() output.

## Post-mortem applicability

Not applicable. First-time script commit; no prior shipped behavior to revert.
