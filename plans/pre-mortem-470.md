# Pre-mortem: Hostile-review-artifact enforcement (#470)

Ticket: #470

## Context

Add a `Hostile-review-artifact:` field check to `self-review.sh` so that
commits touching executable code require evidence of adversarial/hostile
review (cross-review or waiver declaration). Without this, agents self-
approve their own code without any external validation.

## Tigers

**Tiger 1: Bootstrapping — this commit touches .sh files**
**Severity:** MEDIUM
**Likelihood:** Certain — the diff IS executable code
**Mitigation:** Accept WAIVED with `## Hostile-review-waiver` declaration
for the initial bootstrapping commit. The waiver must explain why hostile
review cannot be obtained for the commit that introduces the hostile-review
check itself. Defer executable-file-type restriction to follow-up ticket.

**Tiger 2: False positives on non-executable changes**
**Severity:** LOW
**Likelihood:** Low — field only checked when artifact file exists
**Mitigation:** Field accepts WAIVED with declaration block, ticket comment
links, and file paths. Same pattern as Investigate-artifact/Pre-mortem-artifact.
Non-code-only commits use `[no-review]` which skips all artifact checks.

**Tiger 3: Pattern fragility in field detection**
**Severity:** LOW
**Likelihood:** Low — uses same grep pattern as existing artifact fields
**Mitigation:** Follow exact pattern from Investigate-artifact field check
(grep + sed, same quoting). No novel parsing.

## Implementation may proceed: yes

No launch-blocking Tigers. T1 is mitigated by the waiver mechanism.
