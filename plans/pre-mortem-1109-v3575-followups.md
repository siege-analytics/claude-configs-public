---
ticket_refs:
  - siege-analytics/claude-configs-public#1109: command-text fail-closed and unwrapping, ln link-relative targets, macOS test portability
---

## Pre-Mortem
Task: the five CodeRabbit findings from the v3.5.74 release PR.
Ticket: siege-analytics/claude-configs-public#1109

### Tigers

#### Tiger 1: unquoting single words brings back the #55/#1095 false positives (Severity: medium)

Only a quoted span with no whitespace is kept as code. Messages and bodies contain spaces, so they are still dropped. Two separately quoted words, `echo "git" "commit"`, would now read as a commit. That fails closed: one retry.

Mitigation:
- commit_detector's ignore cases pass: the issue body, the grep pattern, and the heredoc documentation.
- sensitive_files' allow cases pass.

#### Tiger 2: the fail-closed fallback over-matches more often (Severity: low)

The fallback runs only when the helper exits non-zero, which a clean run never does. The helper now exits 3 on any exception instead of 1.

#### Tiger 3: the link-relative `ln` reading blocks legitimate scratch links (Severity: low)

Both readings stay inside `data/` for a link whose ends are in `data/`. The `ln notes.txt n2` and `ln -s notes.txt n3` allows still pass.

### Launch-Blocking Assessment

None identified, provided the suites stay green.
