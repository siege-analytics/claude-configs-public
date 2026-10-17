# Pre-mortem: proportional review policy

## Tiger 1 — Silent downgrade

**Severity:** CRITICAL
**Likelihood:** MEDIUM
**Failure:** An author labels enforcement work Tier A/B and skips pre-mortem or hostile review.
**Mitigation:** Compute the minimum tier from changed paths at commit and push; reject declarations below it; mixed changes take the maximum; classifier/policy changes classify themselves Tier C.
**Negative test:** Tier B declaration for `hooks/git/x.sh` is rejected.

## Tiger 2 — Delete or rename bypass

**Severity:** HIGH
**Likelihood:** MEDIUM
**Failure:** Removing a critical hook or renaming it to a documentation path hides the high-risk source path.
**Mitigation:** Disable rename detection and include A/C/D/M/R/T statuses so both sides are classified.
**Negative test:** staged delete and hook-to-README rename both compute Tier C.

## Tiger 3 — Installed hook cannot find classifier

**Severity:** HIGH
**Likelihood:** HIGH
**Failure:** Source tests pass but deployed workspace hooks fail closed because `bin/review-risk.py` or its policy was not shipped.
**Mitigation:** Package both files for Claude Code and Craft Agent, deploy them to the workspace, and assert their presence in CI and deployment fixtures.

## Tiger 4 — Retroactive history breakage

**Severity:** MEDIUM
**Likelihood:** HIGH
**Failure:** Old commits lacking `Review-Tier:` become impossible to push or inspect.
**Mitigation:** Runtime artifact inspection preserves legacy full validation with a warning. New commit-msg and pre-push paths remain strict.

## Tiger 5 — False Tier A on unknown runtime files

**Severity:** HIGH
**Likelihood:** MEDIUM
**Failure:** A novel extension/path avoids known patterns and receives trivial treatment.
**Mitigation:** Unknown paths default to Tier B; Tier A is limited to explicit prose/plans/generated evidence patterns.

Implementation may proceed: YES
