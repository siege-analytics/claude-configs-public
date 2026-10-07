# Self-review — coordinator-status-guard read exemption (CCP#940)

## Assumptions

Working as: software engineer, tech lead
Goal source: #940
Pre-author-inventory: #940 — investigated coordinator-status-guard.sh: it engages for any gh issue|pr|api, builds `text = body or normalized_command`, and for a read with no --body falls back to the whole command string, so --json field names (state/mergedAt) match its vocabulary. Confirmed the gated-mutation surface (comment/close/reopen/ready/review/edit + api issue-comment/edit) and the read surface (view/list/diff/checks/status; api GET).
Investigate-artifact: #940
Pre-mortem-artifact: #940
Project-contribution: Restores normal read-based status inspection for every coordinator/session in this workspace — a completion/evidence gate no longer rejects `gh pr view --json ...`, removing a false-positive that forced git-ls-remote workarounds during the P1-P4 effort.

Key assumptions:
- Read subcommands carry no status claim and are outside the guard's domain. Verified against the guard's own docstring (status comments + closes).
- The api issue-comment/edit paths are reclassified to resource=issue BEFORE the api-read exemption, so writes are not exempted. Verified by the existing api scenarios all still blocking.

## Peer review

- **writing-tests:1 (red on revert).** Reverting the read-exemption flips the 7 new read scenarios to exit 2 (they'd be gated again), so they go red on revert. Confirmed by running the suite.
- **writing-code:7 (no silent swallow).** The exemption is an explicit `sys.exit(0)` for a named READ_ACTIONS set and a method/body-flag-inspected api-GET, not a broad catch.
- **Scope preservation.** The gated-mutation paths (comment/close/reopen/ready/review/edit; api issue-comment/edit) are untouched: all 38 pre-existing scenarios still pass, including close/review/future-gate blocks.
- Gate 1 (syntax): `bash -n` on hook + test -> exit 0.
- Gate 2 (tests): `bash hooks/_test/coordinator_status_guard.test.sh` -> 45 passed, 0 failed (38 pre-existing + 7 new read-exemption scenarios covering AC1/AC2 and api-GET).
- Gate 3/4 (docs/notebooks): N/A.

## Lead review

- **As tech lead:** minimal, targeted change — an early exit for reads placed after resource/action parsing, before the vocabulary scan. The api-GET exemption is conservative (only when no mutating method and no request-body/field flag), and the pre-existing api issue-comment/edit reclassification runs first so writes are never exempted. Blast radius LOW: no mutation path changed (proven by 0 regressions).
- **Pre-mortem (focused):** Tiger — exempting a write by mistake. Mitigated: READ_ACTIONS is a closed set of read verbs; api exemption requires absence of -X mutating verb AND absence of -f/--field/--raw-field/--input/-F. Paper Tiger — a read subcommand not in the set (e.g. a future `gh pr status`): handled (status is in the set); new verbs fail safe (gated, not exempted) until added. No launch-blocking risk.
- **As software engineer:** the new scenarios assert the exact false-positive from this session (`gh pr view --json state,mergedAt,mergeCommit` -> exit 0) plus siblings, so the regression that motivated the ticket is locked.
- No AI/assistant attribution anywhere.

## Quantified claims

- **45 scenarios pass, 0 fail** (38 pre-existing + 7 new). Evidence: suite output "Results: 45 passed, 0 failed".
- **0 pre-existing scenarios regressed.** Evidence: all 38 prior scenarios still present and passing in the same run.
- **2 files changed** (hook + its test). Evidence: `git status -s`.
- **1 early-exit added for reads** (pr/issue READ_ACTIONS) + **1 conservative api-GET exemption**. Evidence: the diff.
