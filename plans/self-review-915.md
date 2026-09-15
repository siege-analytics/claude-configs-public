---
ticket_refs:
  - siege-analytics/claude-configs-public#915: comment posted
---

# Self-review: siege-analytics/claude-configs-public#915

## Assumptions

Goal source: siege-analytics/claude-configs-public#915
Goal source verification: PASS: ticket siege-analytics/claude-configs-public#915 is fit for execution / title: "hub-concurrency-gate: threads never auto-drain, forcing manual JSON surgery; block message oversells unshipped board-backlog remediation" / sections: Context, Goal, Acceptance — present / evidence: at least one falsifiable token in body / /think link: present / assumptions block: present
Working as: software engineer
Pre-author-inventory: NONE
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/915#issuecomment-5675253634
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/915#issuecomment-5675260648
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/915#issuecomment-5675318155
Project-contribution: closes a gap #898 itself left open at P1 ship time (the inactivity-window drain candidate), reducing the operational friction every hub in this repo's consumer workspaces hits the first time it needs to reach a 4th peer for a quick exchange -- not just this ticket's own reproduction.

## Trivial-against-state declaration

Trivial-against-state: local-only
Reason: this change is pure hook logic operating on a session-scoped local JSON state file; it has no dependency on shared cluster state, external services, databases, or Kubernetes/Spark-style infrastructure.
Evidence: `grep -nE "kubectl|spark|psql|docker|helm" hooks/agent-comms/hub-concurrency-gate.sh` returns no matches; the only I/O is `open()`/`os.replace()` on a path resolved from `$HUB_THREADS_FILE` / `$CRAFT_SESSION_DIR` / a workspace-relative session path -- all local filesystem, no network calls.
Falsification: NOT local-only if the hook is later changed to read/write anything over a network call, a shared cluster resource, or a multi-writer shared file outside the session's own scope.

## Pre-implementation comprehension

Add a time-based prune step to `hub-concurrency-gate.sh`: drop `open_threads` entries whose `last_activity` is older than `HUB_THREAD_STALE_SECONDS` (default 3600s) or missing/unparseable, before the cap/block decision, and persist the pruned state. Fix the block message so it stops implying `#899`/`#900` board-routing is available today. See `## Junior task description` posted to the ticket (comment `#issuecomment-5675261991`) for the original task framing.

## Senior adversarial checklist

See `## Senior adversarial checklist` posted to the ticket (comment `#issuecomment-5675261991`) -- seven checks, all resolved, including the two (#896 decision 1 and decision 2 non-reopening) most likely to be a hidden scope violation for this specific ticket.

## Peer review

Shelf checks:
- `writing-code:3` (no speculative abstractions) -- the fix adds exactly the mechanism needed (a time-based prune + env override mirroring the existing cap override pattern), nothing more; no board-integration scaffolding, no work-type taxonomy.
- `writing-code:5` (no hypothetical code) -- every claim about the hook's pre-fix behavior was verified by reading the actual file and running its actual test suite before editing (`bash hooks/_test/hub_concurrency_gate.test.sh` -> 14 passed, 0 failed, baseline).
- `writing-tests:1` (tests fail on revert) -- the critical regression test (continuation-not-blocked-by-own-staleness) was verified fail-before/pass-after empirically: reconstructed the buggy pre-fix-ordering in isolation, confirmed `exit 2` + dropped record, then confirmed the corrected ordering passes. Not just asserted -- executed both ways.
- `writing-claims:8` (specific counts cite the producing command) -- "26 passed, 0 failed" is the literal output of the test run below, not a recalled figure.
- `writing-rules:8` (shape-space enumeration for class-of-idiom claims) -- N/A; this fix targets one specific hook's one specific state-transition bug, not a class of idioms across files.

Gate evidence:
```
$ bash hooks/_test/hub_concurrency_gate.test.sh
...
Results: 26 passed, 0 failed
```
`bash -n hooks/agent-comms/hub-concurrency-gate.sh` -> exit 0 (syntax check clean; the embedded Python block is exercised by the test run itself, which is the stronger check).

## Lead review

- **Correctness (tech lead):** the hostile-review-caught ordering bug (pruning before the continuation check) was the one path that could have shipped wrong -- fixed, and the fix is now the thing under test, not just the happy path. Affirmed.
- **Scope discipline (tech lead):** verified against #896's "Decisions locked in" section line by line before writing a single line of code; the fix does not reopen decision 1 (no categorization) or decision 2 (flat cap, no tuning) -- it only changes an entry's time-to-live before it stops counting. Affirmed.
- **Test floor (software engineer):** 26/26, including two edge-case boundary tests and the regression test, all added in response to independent adversarial review rather than self-assessed as "probably fine." Affirmed.
- **Scope of the PR vs. the ticket (tech lead):** the doctrine-sync follow-up in `electinfo/electinfo_claude_skills`' `hub/SKILL.md` Part 5 is explicitly named as deferred, not silently dropped. Affirmed.
