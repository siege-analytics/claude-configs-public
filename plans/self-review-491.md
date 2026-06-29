---
ticket_refs:
  - siege-analytics/claude-configs-public#491
---
## Self-Review: #491 — pre-push historical commit blocking

## Assumptions
Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #491
Goal source verification: ticket body describes historical commits blocking promotion push
Plan reference: #491 ticket body
Pre-author-inventory: session log from #1125 showing 6 historical commits blocked
Investigate-artifact: investigate-gate.json (ticket siege-analytics/claude-configs-public#491)
Pre-mortem-artifact: plans/pre-mortem-491.md (workspace)

## Peer review

writing-code: one-line change to pre-push-self-review.sh — change normal push range from `REMOTE_SHA..LOCAL_SHA` to `LOCAL_SHA --not --remotes`.

### Syntax check
- `bash -n hooks/git/pre-push-self-review.sh` → exit 0

### Logic verification
- New branch case (line 42): already uses `--not --remotes` — unchanged
- Rebase case (line 47): already uses `--not --remotes` — unchanged
- Normal push case (line 49): changed to `--not --remotes` — now uniform with other cases
- `--not --remotes` excludes commits reachable from ANY remote ref, so commits already on origin/develop won't be re-checked when arriving on main via merge
- Feature branch pushes: new commits are NOT on any remote, so they're still checked. Correct.
- Merge commits: already skipped at line 56. Correct.

## Lead review

One-line change, same `--not --remotes` pattern already used for two other cases. The change makes all three cases use the same range logic, which is simpler and avoids the historical commit re-validation problem.

Blast radius: only affects normal pushes. New branches and rebases already use this logic.

## Findings

No findings.

## Quantified claims
- "1 line changed" — git diff confirms

## Rework ledger

No rework cycles.

## Evidence-predates-work
Artifact: plans/self-review-491.md
First-added commit: (same commit)
Work commit: (pending)
