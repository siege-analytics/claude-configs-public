---
ticket_refs:
  - siege-analytics/claude-configs-public#1089: read classifier proves kubectl -n get delete, ss -K and gh --web
---

# Self-review: #1089 kubectl global flags, ss -K, gh --web

## Assumptions

Pre-author-inventory: on develop bdc97f8, `read-only-command.py` returned 0 for `kubectl -n get delete pod x`, `kubectl --context get delete pod x`, `kubectl -n logs exec -it pod -- sh`, `ss -K dst …` and `gh search repos x --web`. On the full gate, `gh pr view 1 --web` and `gh pr list -w` were also allowed with no task gate, through the legacy safelist.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1089
Pre-mortem-artifact: plans/pre-mortem-1089-kubectl-ss-gh-web.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1089
Project-contribution: closes three no-gate paths: a disguised kubectl delete/exec, socket kills, and browser launches.

- The independent review of the #1051 slim branch found these when that branch delegated read proof to this classifier. Its findings are recorded on #1089.

## Peer review

- **writing-code:**
  - `kubectl_ok` walks past known global options and their values. An unknown option before the subcommand makes the command unproven.
  - `ss` leaves the plain verbs; `-K`/`--kill` is a veto.
  - `gh` with `--web`/`-w` is unproven, and a veto so the legacy safelist cannot admit it.
- **writing-tests:** `read_allowlist` passes 246/246 here, and 6 of the new cases fail on develop.
- **Gate evidence:**
  - hook suites 38/38 after `bin/build.py`;
  - review_risk_test PASS;
  - generated-source-authority current.
- **Replay:** 2,845 commands, in both states: 0 verdict changes.

## Lead review

- **Solves #1089:** yes.
- **Out of scope:** the legacy gate's blanket `'kubectl '` indicator, which is unchanged.

## Quantified claims

- New must-block cases: 8. New allow and proof cases: 7.
- Replay verdict changes: 0.
