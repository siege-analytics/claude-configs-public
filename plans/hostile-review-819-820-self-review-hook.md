# Hostile review: #819/#820 self-review hook repairs

Reviewer source: independent secondary model, Sonnet-class with extended reasoning.

## Initial review

Verdict: BLOCK.

Findings:

- HIGH: #820 grandfathering used only the committed artifact timestamp while validating the working-tree file, so a dirty edit to a historical artifact could omit `Pre-author-inventory:` and still be grandfathered.
- MEDIUM: tests did not cover dirty-working-tree or untracked missing-inventory artifacts.
- LOW: tests did not include a real transformation file proving `Pre-ship-dry-run` remains required outside the self-review hook self-match.

## Fixes after initial review

- Grandfathering now requires the artifact to be clean in both worktree and index.
- Added dirty historical artifact block coverage.
- Added untracked/current artifact block coverage.
- Added real transformation file block coverage.

## Final review

Verdict: PASS.

Confirmed:

- #820 grandfathering is limited to clean tracked historical artifacts whose last commit predates `Pre-author-inventory:` enforcement.
- Dirty worktree/index historical artifacts, untracked artifacts, and current-era artifacts still block.
- #819 skips only `hooks/git/self-review.sh` for the transformation regex self-match.
- Real transformation files still require `Pre-ship-dry-run`.
- Added tests cover the pass/block shapes for both #819 and #820.
