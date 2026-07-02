---
ticket_refs:
  - siege-analytics/claude-configs-public#609
---

# Design - #609 coordinator status transition evidence guard

## Problem

Coordinator sessions can update issue/PR comments or close issues with prose that implies completion while owner signoff, merge evidence, branch target evidence, deploy/UAT, backfill, or reindex prerequisites remain unresolved. GPT/Codex sessions are a high-risk runtime because they can run `gh` commands directly, but they do not run Claude Code hooks. Coverage therefore needs both the Claude Code Bash guard and parent-side spawn/review routing controls that bind unhooked children in prose and prevent them from posting directly.

## Scope

Add a hard PreToolUse guard for Bash `gh issue` / `gh pr` status-transition commands and matching `gh api` issue-comment / issue-edit operations. The guard should block only state-transition-shaped updates, not ordinary investigation comments.

## Approach

1. Add `hooks/bash/coordinator-status-guard.sh`.
2. Wire it into `hooks/settings-snippet.json` under Bash PreToolUse for hook-capable Claude Code package users. Non-hook GPT/Codex children require parent-side `spawn_session` guarding and parent-mediated posting.
3. Add `hooks/_test/coordinator_status_guard.test.sh` with block/pass scenarios for:
   - completion without evidence,
   - completion mixed with unresolved blockers,
   - blocked state without explicit failure reason,
   - blocked state with reason,
   - completion with required evidence,
   - issue close without evidence,
   - ordinary non-status comment,
   - absolute-path and shell-wrapper `gh` invocations,
   - stdin/unreadable `--body-file` Codex pipeline patterns, including `/dev/stdin` and fd aliases,
   - shell-expanded inline `--body` values such as command substitutions, environment variables, positional parameters, and indirect variables,
   - `gh api` issue comment/close operations that bypass the `gh issue` / `gh pr` subcommands, including method-before-endpoint forms and file/input payload bodies,
   - editor/web-supplied bodies for `gh issue` / `gh pr` comment and review operations, including boolean equals flag forms,
   - future-plan gate comments that say gates/deployment/UAT/hotfix movement will be checked later instead of providing current evidence,
   - negative or pending owner-signoff evidence.
4. Add `hooks/agent-comms/spawn-guard.sh` and wire it to `mcp__session__spawn_session` so parent sessions cannot spawn unbound GPT/Codex reviewers.
5. Update `cross-review` routing so child reviewers receive RULES_BUNDLE/RESOLVER context and return findings to the hook-bound parent instead of posting ticket comments directly.
6. Document the hooks in `hooks/README.md`.

## Required evidence model

Completion/close/ready transitions require all three evidence classes:

- owner/maintainer/operator signoff or approval thread evidence,
- merge or branch-target evidence,
- deploy/UAT/rollout/backfill/reindex evidence or N/A.

Blocked transitions must remain explicit: blocked-state updates need a concrete failure reason, and completion claims cannot coexist with unresolved blocker language.

## Verification plan

- `bash hooks/_test/coordinator_status_guard.test.sh`
- `bash -n hooks/bash/coordinator-status-guard.sh hooks/_test/coordinator_status_guard.test.sh`
- `python3 bin/validate-hooks.py`
- `python3 bin/build.py`
- `python3 bin/validate-hooks.py dist/claude-code/`
- `python3 bin/validate-hooks.py dist/craft-agent/`
