---
ticket_refs:
  - siege-analytics/claude-configs-public#609
---

# Investigation Fact Sheet - #609 coordinator status guard

Task: Add a hard guard for coordinator status transitions lacking evidence.
Ticket: siege-analytics/claude-configs-public#609
Investigated: 2026-07-01
Approach: `plans/design-609-coordinator-status-guard.md`

## Prior Knowledge

- Issue #609 read. It reports coordinator status drift in session `260701-warm-bobcat`, with completion/blocker ambiguity across #31 and #165 flows.
- Related PRs #31 and #165 were read. Both are merged historical PRs with CodeRabbit rate-limit comments; the specific comment IDs cited in #609 were not accessible through the `siege-analytics/claude-configs-public` issue comment API, returning 404.
- Existing resolver and hooks were searched for coordinator/status/lane transition enforcement. No existing hook blocks `gh issue comment` / `gh issue close` status transitions on evidence prerequisites.
- Existing hook harness `hooks/_test/run_scenarios.sh` was read and supports pass/block assertions by exit code.

## Knowledge Loci

- **Bash hook settings:** `hooks/settings-snippet.json`, Bash PreToolUse hook list. This is the install surface for hook-capable Claude Code runtimes. GPT/Codex child sessions do not run these hooks, so they require parent-side spawn/routing enforcement.
- **Hook documentation:** `hooks/README.md`, hook table.
- **Hook tests:** `hooks/_test/*.test.sh` plus `hooks/_test/run_scenarios.sh`.
- **New enforcement hook:** `hooks/bash/coordinator-status-guard.sh`.

## Impact Chain

### Upstream

- Agent emits side-effecting Bash commands such as `gh issue comment`, `gh issue close`, `gh pr comment`, or `gh pr review`.
- Hook receives JSON from PreToolUse with `tool_input.command`, consistent with existing Bash hooks.

### This Task

- Parse the command, extract inline `--body` or `--body-file` content, identify coordinator/status transition language, and block unsafe transitions.

### Downstream

- Unsafe coordinator status updates are stopped before they reach GitHub.
- Ordinary non-status issue comments still pass.
- Consumer package builds copy the hook and settings to hook-capable packages.
- Parent-side spawn guarding prevents unbound GPT/Codex child sessions and cross-review routing requires children to return findings through the hook-bound parent.

## Verified Shapes

- **New hook parser** (`hooks/bash/coordinator-status-guard.sh:15-18`)
  - SCHEMATIC: reads hook JSON and extracts `tool_input.command` through `hooks/lib/extract-json.py`.
  - SEMANTIC: empty or unparsable commands pass fail-open like existing hooks.

- **Transition scope** (`hooks/bash/coordinator-status-guard.sh:32-86`)
  - SCHEMATIC: applies to `gh issue` / `gh pr` comment/edit/close/reopen/ready/review commands.
  - SEMANTIC: ordinary comments pass unless they contain coordinator/state markers.

- **Evidence rules** (`hooks/bash/coordinator-status-guard.sh:88-115`)
  - SCHEMATIC: completion with blockers blocks; blocked without reason blocks; completion/close/ready requires owner signoff, merge/branch, rollout evidence.
  - SEMANTIC: missing evidence returns exit 2 with a concrete failure reason.

- **Settings wiring** (`hooks/settings-snippet.json`, Bash PreToolUse list)
  - SCHEMATIC: coordinator status guard is inserted after destructive guard and before catalog guard.
  - SEMANTIC: hook-capable consumer packages include it through existing build copy logic.

- **Spawn-session wiring** (`hooks/settings-snippet.json`, `mcp__session__spawn_session` PreToolUse matcher)
  - SCHEMATIC: `hooks/agent-comms/spawn-guard.sh` blocks unbound child spawns before the child runtime exists.
  - SEMANTIC: parent sessions must name permission, model, reasoning, sources, and rules binding for child sessions.

- **Unit tests** (`hooks/_test/coordinator_status_guard.test.sh:15-50`)
  - SCHEMATIC: seven scenarios cover block/pass boundaries.
  - SEMANTIC: validates the #609 acceptance cases directly.

## Coherence

The Bash hook targets the GitHub issue/PR mutation surface for hook-capable runtimes. GPT/Codex child sessions are not hook-capable here, so the coherent closure requires parent-side spawn guarding and cross-review routing that prevents direct child ticket posting. The test scenarios cover unsafe completion, explicit blocked-state behavior, and child spawn contract failures.

## Hypothesis and Falsification

Hypothesis: status-transition commands that imply completion without required evidence will exit 2 before reaching GitHub, while ordinary non-status comments and evidence-backed transitions pass.

Falsification:

- `hooks/_test/coordinator_status_guard.test.sh` fails.
- `validate-hooks.py` reports a hook missing from settings or syntax-invalid.
- A command like `gh issue comment 31 --body 'Status: complete. Lane done.'` exits 0.
- A non-status comment like `gh issue comment 165 --body 'I am investigating...'` exits 2.
- A review `spawn_session` lacking RULES_BUNDLE/RESOLVER binding exits 0.
