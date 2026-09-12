---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment posted (issue body)
---

# Design: Scope the enforcement gates (task-relevance + project overlay + runtime awareness)

Ticket: #873. Source of truth: this repo (Siege umbrella).

## Problem (corrected after investigation)

The gates are not unscoped. They resolve by session/repo/ticket in
`hooks/lib/resolve-think-gate.py`. The real defects are six:

- D1 No task-relevance axis. Gates answer "which task's gate applies", never
  "is this action in scope for a gate at all". `branch-state-guard.sh` fires
  unconditionally; `universal-mutation-gate.sh` blocks every non-safelisted
  command regardless of the active task.
- D2 Project overlay exists for skills/rules but not gates. The gate layer knows
  only `repo_slug` (repo basename), never `project`. The only gate reading
  PROJECT.md (KB check) fails closed when PROJECT.md is present and the signal
  lacks a `kb` section.
- D3 Session identity is runtime-fragile. The resolver keys on `CRAFT_SESSION_ID`;
  outside Craft or with env unset, session-scoping silently disables and
  resolution collapses to the workspace singleton, causing cross-task and
  cross-project bleed.
- D4 Fail-closed over-blocks reads. Safelist false-positives: `git -C rev-parse`,
  chained reads, `for` loops. (Git -C fixed in PR #880.)
- D5 No runtime awareness. The same hook is advisory in Claude Code but fatal in
  Craft (`continue:false` honored as a hard halt). Root cause of craft-agents#49.
- D6 Gate identity is hardcoded. `BLOCK_PATTERNS` greps literal strings;
  filenames are literal; path logic is duplicated across resolver and guards.

## Design spine

Extend the existing umbrella/project-override model (Siege general `skills/` +
`projects/<slug>/` overlays, repo-bound activation, no cross-project inheritance,
declared weakening only) to the gate layer. Do not invent a parallel system.

Enforcement stance: gates become advisory (narrate, no `continue:false`) and log
every would-have-blocked event for audit; hard-blocking lives only at PreToolUse
mutation points, scoped by task-relevance and project match.

## Rollout (one sub-issue and PR per stage)

- P0 (#874) detect_runtime() + gate registry/manifest abstraction (D5, D6).
- P1 (#875) UserPromptSubmit guards advisory + audit log; safelist read fixes
  (D4; git -C shipped in #880).
- P2 (#876) session-identity fail-safe + singleton-fallback hardening (D3).
- P3 (#877) resolve_project() + project-scoped gate files (D2).
- P4 (#878) gate_applies(action_class, project, runtime) task-relevance (D1).
- P5 (#879) KB-consultation advisory-until-project-opts-in (D2).

## Risks

- Relaxing guards could under-enforce. Mitigation: advisory still narrates; only
  the wrong hard-block is removed; every would-have-blocked is logged.
- The resolver is load-bearing (every gate calls it). Mitigation: unit tests in
  hooks/_test/; one PR per stage so a regression is bisectable.
- Project detection wrong leads to wrong overlay. Mitigation: reuse the
  build-validated PROJECT.md repo uniqueness; default to umbrella on ambiguity.
