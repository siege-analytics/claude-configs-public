---
ticket_refs:
  - siege-analytics/claude-configs-public#248
  - siege-analytics/claude-configs-public#345
  - siege-analytics/claude-configs-public#612
---

# Pre-Mortem - lifecycle, spawn isolation, and drive-handoff follow-up

Fact sheet: `plans/investigate-248-345-612-lifecycle-spawn-autonomy.md`
Design: `plans/design-248-345-612-lifecycle-spawn-autonomy.md`

## Tigers

### Tiger 1: Worktree guard blocks read-only reviewers unnecessarily

- Evidence: review sessions often run in the parent repo path but should not edit files.
- Severity: MEDIUM
- Urgency: Launch-Blocking
- Mitigation: guard has read-only/no-file-edits carve-out and a test for read-only review without worktree.
- Status: Mitigated.

### Tiger 2: Lifecycle rules remain passive prose

- Evidence: #612 specifically reports passive update-ticket status handling.
- Severity: HIGH
- Urgency: Launch-Blocking
- Mitigation: add always-on rule cohort and wire action skills that perform PR creation, ticket update, and close. Platform fallback requires `Status: <state>` comments when fields cannot be changed.
- Status: Mitigated.

### Tiger 3: Drive-mode still produces pure status checks

- Evidence: #345 reports wakeups that checked status but produced no operator-visible work.
- Severity: HIGH
- Urgency: Launch-Blocking
- Mitigation: drive skill and standing-order injection now require an operator-visible artifact or explicit blocker before yielding.
- Status: Mitigated.

## Paper Tigers

### Paper Tiger 1: Hook cannot create a worktree itself

- Why handled: `spawn_session` hook validates the parent spawn contract before child creation. Platform-level automatic worktree creation remains ideal, but parent-side block prevents unisolated write-capable child spawns unless the prompt/workingDirectory is worktree-isolated or read-only.

## Elephants

### Elephant 1: Project-board API schemas vary

- What it is: GitHub Projects, Linear, Jira, and GitLab all expose status differently.
- Deferral: The rules remain platform-agnostic and require a `Status: <state>` comment fallback when no mutable field is available. A future platform-specific helper can automate individual APIs.
- Revisit trigger: repeated comments with fallback status where a mutable status field was available but not used.

## Launch decision

No unmitigated launch-blocking Tigers remain.
