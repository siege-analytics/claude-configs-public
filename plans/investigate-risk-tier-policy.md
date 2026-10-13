# Investigation: proportional review policy

## Fact sheet

Goal source: approved Skill Library Simplification Plan, Phase 5 / PR 6.
Base: `develop` at `261e4bb515ffc2c8d562a0b62a62fe90c4a9ae28`.

### Verified Shapes

- **PROBED — commit-msg:** `.githooks/commit-msg` required the same full artifact sections for every reviewed commit and allowed `[no-review]` before any path-based risk computation.
- **PROBED — runtime push gate:** `hooks/git/self-review.sh` required investigation and pre-mortem fields independent of change risk; `hooks/git/pre-push-self-review.sh` checked only a Self-Review trailer and did not classify risk.
- **PROBED — package topology:** hooks execute outside the source checkout, so classifier code and policy must ship in both consumer packages and the deployed Craft workspace.
- **ATTESTED — policy boundary:** Tier C must include enforcement, branch/release/deployment, credentials/auth/permissions, destructive operations, and review-policy changes. Unknown paths default to Tier B; mixed changes take the maximum.
- **PROBED — deletion/rename shape:** `git diff --name-only --diff-filter=ACMR` omits deletions and can collapse renames to the destination, allowing critical source paths to disappear from classification. Required shape is `--no-renames --diff-filter=ACDMRT`.

## Intended behavior

One canonical classifier computes the minimum tier from all changed source and destination paths. Authors may escalate but cannot downgrade. Tier A uses a short record; Tier B uses focused assumptions/test evidence; Tier C retains the full evidence chain. Legacy commits keep historical full validation rather than being retroactively invalidated.
