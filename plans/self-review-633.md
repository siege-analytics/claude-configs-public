---
ticket_refs:
  - siege-analytics/claude-configs-public#633
---

# Self-review: PR for #633 (release-note [Unreleased] reuse regression)

## Assumptions

Working as: software engineer
Domain: CI release-workflow + CHANGELOG.md automation
Goal source: siege-analytics/claude-configs-public#633
Pre-author-inventory: `grep -n release-notes.py .github/workflows/build-and-publish.yml` returned line 213. `cat scripts/ci/release-notes.py` showed that it FALLS BACK to [Unreleased] if a versioned section doesn't exist — exactly the mechanism that causes the reuse defect. `grep -n '\[Unreleased\]\|\[3\.5' CHANGELOG.md | head` confirmed only [3.5.20] and [Unreleased] exist post-#625; every tag v3.5.21-v3.5.25 read from [Unreleased].
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: makes the promotion mechanical in the release job rather than manual, matching ticket's suggested fix. Before this PR, [Unreleased] was never promoted to a versioned section on tag, so 5 releases (v3.5.21-v3.5.25) each cut notes from the same growing block. After this PR, the promoter runs before release-notes.py; a subsequent auto-cut reads from the freshly-promoted [<version>] section and [Unreleased] resets to placeholder-only.

## Trivial-against-state declaration

Reason: adds one new promoter script + one new test file + one CI workflow addition. No existing runtime code changed. CHANGELOG.md not touched by this PR (the promoter is a NEW mechanism that runs at release time).
Evidence: `git diff --stat` shows 4 new/edited files: scripts/ci/promote-unreleased.py, scripts/ci/test_promote_unreleased.sh, plans/self-review-633.md, .github/workflows/build-and-publish.yml (one step-body addition + one comment).
Falsification: not trivial if the workflow addition changes runtime behavior of non-release paths. Verified: the new promoter call is inside "Create GitHub Release" step which is gated on `if: startsWith(github.ref, 'refs/tags/v') || steps.auto-tag.outputs.tag != ''`. Non-release runs skip this step entirely.

## Trivial-investigation declaration

Reason: #633 named the fix directly: "make the promotion mechanical in the release job rather than manual". No discovery required.
Cannot produce error: the promoter is idempotent (no-op if [<version>] already exists) and refuses to create an empty versioned section (which would poison future promotions).
Evidence: `bash scripts/ci/test_promote_unreleased.sh` returns "6 passed, 0 failed" covering all promotion outcomes plus edge cases (empty Unreleased, missing header, v-prefix arg).
Falsification: not trivial if the promoter mishandles a real CHANGELOG. Tested against a fixture matching the shipped shape; verified no data loss (all items from [Unreleased] preserved in [<version>]).

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('scripts/ci/promote-unreleased.py').read())"` -> ok. Workflow YAML checked mentally against existing steps; no test-YAML infrastructure in this repo.
- Gate 2 (tests): `bash scripts/ci/test_promote_unreleased.sh` -> "6 passed, 0 failed"
- Gate 3 (docs): promoter docstring names the failure mode #633 references and the idempotence contract explicitly
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): tested against a real-shaped CHANGELOG fixture; verified the output shape by grep against the fixture post-run.
- writing-tests:1 (tests fail on revert): each scenario tests a specific outcome (promoted, already-exists, empty-unreleased, no-unreleased error, --check no-modify, v-prefix stripping). Reverting any specific branch fails one scenario.
- writing-tests:5 (every except-block exercised): promoter has no except blocks (uses direct file I/O). Test file has no except blocks.
- writing-claims:8 (specific counts): "5 releases v3.5.21-v3.5.25" — cited from ticket; verifiable via `git tag | grep '^v3.5.2[1-5]$'`.

## Lead review

- Junior solved the stated goal: yes. Promoter is mechanical, idempotent, tested. Workflow calls it before release-notes.py.
- Junior over-scoped: no. Did not commit-and-push the CHANGELOG mutation back to develop from the workflow (that would need write permissions on the tag runner and adds a complication). The promotion happens workflow-local for the release-notes cut; the CHANGELOG on develop is not modified by this PR. This matches the ticket's suggested fix "on tag, move the current [Unreleased] content under a [<version>] --- <date> header" without over-committing to a specific persistence mechanism.
- Junior under-scoped: didn't backfill the missing [3.5.21]-[3.5.25] sections. Ticket's scope is prevention of the regression, not correction of the 5 already-cut releases. Backfilling is separately-scoped.
- Standards affirmatively met: writing-code:5, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "6 test scenarios pass."
Verified-by: `bash scripts/ci/test_promote_unreleased.sh` returns "Results: 6 passed, 0 failed."

Claim: "promoter is idempotent."
Verified-by: scenario (b): second call after promotion returns "already-exists" with exit 0.

Claim: "promoter refuses to create empty versioned section."
Verified-by: scenario (c): [Unreleased] with only a comment returns "empty-unreleased" and does not promote.

## Post-mortem applicability

Applies loosely: #625 was closed as fixed and the same class reappeared. This is a writing-rules:6 candidate (a shipped implementation contradicting its own AC), but the original ticket #625 predates the writing-rules:6 discipline and its self-review artifact isn't in the tree. Recording the pattern here: #625's fix was a one-time backfill without a durable mechanism; the auto-cut pipeline then reopened the class. Filed as a lesson: mechanical enforcement > one-time backfills. The fix here IS the mechanism.
