---
ticket_refs:
  - siege-analytics/claude-configs-public#1075: sync-workspace-hooks.sh hangs from a terminal; the verify-enforcement probe reads the caller's stdin
---

# Self-review: #1075 verify-enforcement probe must not read the caller's stdin

## Assumptions

Pre-author-inventory: a fresh clone of v3.5.69 (main 2cebfc3) was installed into a mock local Craft workspace with `bin/sync-workspace-hooks.sh --yes`. Under an open stdin, `ca-enforcement-gate.sh` sat in `pipe_read` with a child `cat` on fd 0 for 31 minutes. With `< /dev/null`, the same install finished in 4 s with probes passing and drift clean.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1075
Pre-mortem-artifact: plans/pre-mortem-1075-verify-enforcement-stdin.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1075
Project-contribution: workspace installs from a terminal complete, instead of hanging at enforcement verification.

- The gate reads its payload with `cat` (`hooks/resolver/ca-enforcement-gate.sh:122`). That is correct for a hook and is unchanged.

## Peer review

- **writing-code:** a one-token change at the call site. It gives the probe the input CI already gives it.
- **writing-tests:** the new `verify_enforcement` case fails without the fix (exit 124) and passes with it, in 29 s for the whole suite.

## Lead review

- **Solves #1075:** yes.
- **Not done:** an audit of other installer steps for stdin reads. None appeared in the end-to-end install.

## Quantified claims

- `verify_enforcement`: 39/39 with the fix; 38/39 without it (the new case).
- Install time: 4 s with stdin closed, against a hang of 31+ minutes with it open.
