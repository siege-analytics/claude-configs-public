---
ticket_refs:
  - siege-analytics/claude-configs-public#489
---
# Pre-mortem: #489 — Mechanical enforcement gates

## Risks

1. **gh API latency in UserPromptSubmit hook** — Severity: MEDIUM
   Components A and B call `gh api` every turn when status=implementing.
   This adds network latency to the hook pipeline.
   Mitigation: 15-second timeout; failure is silent (pass-through, not block).
   The hook already does subprocess calls for git diff; one more is incremental.

2. **Deploy-stamp false positive on amend commits** — Severity: LOW
   If the agent amends a commit after deploying, the stamp commit won't
   match HEAD. This is correct behavior (the deployment IS stale after an
   amend), but the agent may perceive it as a false positive.
   Mitigation: The error message clearly states "run build.py --deploy
   after your latest commit" — the fix is obvious.

3. **TRIVIAL threshold too aggressive** — Severity: MEDIUM
   20 lines of executable code may be too low for legitimate trivial changes
   (e.g., a rename across 5 files). But this is the starting threshold;
   it can be tuned after deployment experience.
   Mitigation: The threshold is a named constant (TRIVIAL_LINE_THRESHOLD)
   that can be adjusted.

4. **Rework detection false positives from commit messages** — Severity: LOW
   Grepping branch commit messages for "amend|fixup|retry" may match
   unrelated words. E.g., "amend the documentation" is not rework.
   Mitigation: Only checks commits on the current branch since merge-base
   with develop. Short-lived feature branches have few commits.

5. **Junior/Senior comment detection heuristics** — Severity: MEDIUM
   Keyword matching on ticket comments is fuzzy. The Junior could post
   a description that uses different phrasing for the 5 elements.
   Mitigation: Only requires 3 of 5 stems for Junior, 5 of 10 for Senior.
   These are warnings, not blocks — the agent sees them every turn until
   the comments are posted with recognizable structure.

6. **Pipeline-state-guard grows large** — Severity: LOW
   Adding gh API calls to an already-large Python block embedded in shell.
   Mitigation: The block is self-contained; the complexity is in the
   conditionals, not the control flow.
