# Design note: #819/#820 self-review hook repairs

## Goal source

- #819: `hooks/git/self-review.sh` transformation-content regex self-matches when editing the hook itself.
- #820: `Pre-author-inventory:` field check blocks future work when HEAD references a pre-field-era self-review artifact.

## Design

### #819

Keep the transformation dry-run gate intact for SQL/DataFrame/write-code diffs, but skip the exact path `hooks/git/self-review.sh` during content-regex scanning. Editing this enforcement hook is already governed by enforcement-path checks, hostile review, deploy-stamp, and inventoried-shape evidence. It should not require data-pipeline dry-run evidence merely because it contains the regex literal that detects data-pipeline code.

### #820

Keep `Pre-author-inventory:` strict for current/untracked/current-era artifacts. Add a narrow grandfather path only when:

1. the artifact is tracked in the current repo;
2. the artifact is clean in both worktree and index;
3. the artifact's last commit timestamp predates the first commit in this repo that introduced `Pre-author-inventory:` enforcement in `hooks/git/self-review.sh`; and
4. the field is missing/empty.

In that prior-era case, warn and continue rather than retro-block unrelated future work.

## Non-goals

- Do not weaken `Pre-author-inventory:` for current self-review artifacts.
- Do not suppress transformation dry-run checks for real `.sql`, `.sql.j2`, DataFrame `.write`, `.saveAsTable`, or `.to_sql` changes outside `hooks/git/self-review.sh`.
- Do not change issue-reporting or deployment-drift gates.

## Validation plan

- Add isolated git-fixture tests for both regressions.
- Run the new focused test, shell syntax check, build check, and skill-reference sync check.

### Verified Shapes

**S1** ATTESTED: #819 failure shape is a commit whose only transformation regex match is the literal inside `hooks/git/self-review.sh`.
**S2** ATTESTED: #820 grandfather shape is a tracked self-review artifact whose last artifact commit predates the hook commit that introduced `Pre-author-inventory:` enforcement.
**S3** ATTESTED: #819 strict shape is a real transformation file containing DataFrame write behavior; it must still require dry-run evidence.
**S4** ATTESTED: #820 dirty historical shape is an edited historical artifact missing `Pre-author-inventory:`; it must block rather than grandfather.
**S5** ATTESTED: #820 current/untracked shape is a current review artifact missing `Pre-author-inventory:`; it must still block.

### Tiger 1

**Severity:** MEDIUM
Likelihood: medium
Mitigation: include both grandfather-pass and current-missing-field-block fixtures.
Trigger: the hook warns for current artifacts without inventory.
Fallback: revert grandfather branch and require explicit artifact migration.

### Tiger 2

**Severity:** LOW
Likelihood: low
Mitigation: skip only exact path `hooks/git/self-review.sh`, leaving real transformation extensions/content checks in place.
Trigger: real transformation code no longer demands dry-run evidence.
Fallback: add extension-gated content scan or explicit allowlist.
