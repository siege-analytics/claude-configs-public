# Investigation: Hostile-review-artifact enforcement (#470)

Ticket: #470

## Task understanding

Add mechanical enforcement requiring a `Hostile-review-artifact:` field in
self-review artifacts when commits touch executable code. Without this,
agents can self-approve code changes with no external adversarial review.

## Pre-author inventory

### Verified Shapes

**self-review.sh artifact field checks (v1.3 pattern)**
- PROBED: `grep -n 'Investigate-artifact\|Pre-mortem-artifact' hooks/git/self-review.sh`
  → Lines 318-379: field extraction via grep+sed, TRIVIAL with declaration block,
    file-path existence check, ticket-link passthrough. Exact pattern to replicate.

**Existing version numbering in self-review.sh**
- PROBED: `grep -n '^# v[0-9]' hooks/git/self-review.sh`
  → v1 through v2.2 occupied. Next available: v2.3.

**DIFF_FILES variable availability at insertion point**
- PROBED: `grep -n 'DIFF_FILES' hooks/git/self-review.sh`
  → Line 575: `DIFF_FILES=$(git ... diff-tree ...)`. Available at line 897+ (insertion point).
  Used by v1.6 (line 581), v2.0 (line 780), v2.1 (line 838). Safe to reuse.

**Hostile-review waiver pattern**
- ATTESTED: No existing waiver pattern in self-review.sh for hostile review.
  Closest analog: Trivial-investigation declaration (v1.3, lines 337-362) with
  required fields in an awk-extracted block. Adapt to ## Hostile-review-waiver
  with Reason/Scope/Compensating-control fields.

## Findings

None — straightforward extension of existing pattern.
