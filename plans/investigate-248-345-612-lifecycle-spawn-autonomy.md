---
ticket_refs:
  - siege-analytics/claude-configs-public#248
  - siege-analytics/claude-configs-public#345
  - siege-analytics/claude-configs-public#612
---

# Investigation - lifecycle, spawn isolation, and drive-handoff follow-up

## Prior knowledge

- #248 requests worktree isolation for spawned sessions to prevent shared Git working tree races.
- #345 requests drive-handoff resolver/skill behavior that produces operator-visible work rather than silent status checks.
- #612 requests proactive ticket lifecycle status transitions at the action points that begin work, open PRs, hand to testing/UAT, block/unblock, and close.
- Existing `spawn-guard.sh` from #609 already checks permission/model/reasoning/source/rules binding for spawned sessions.
- Existing `drive-while-away` already covers basic handoff scheduling but did not require a durable work inventory or productive artifact per fired turn.
- Existing `update-ticket`, `create-pr`, and `close-ticket` mention ticket updates, but no always-on lifecycle rule cohort existed.

## Verified shapes

- `hooks/agent-comms/spawn-guard.sh`
  - Existing tool schema fields: `permissionMode`, `model`, `thinkingLevel`, `enabledSourceSlugs`, `workingDirectory`, `prompt`.
  - New shape: for write-like prompts in a Git working directory, block unless worktree isolation is declared or the prompt is read-only/no-file-edits.

- `hooks/_test/spawn_guard.test.sh`
  - Existing guard scenario harness supports pass/block outcomes by exit code.
  - New scenarios cover Git write child without worktree, Git write child with worktree instruction, and read-only review carve-out.

- `skills/drive-while-away/SKILL.md`
  - Existing trigger list recognized direct drive/monitor phrases.
  - New trigger list includes common implicit handoff phrases from #345.
  - New per-fire behavior requires operator-visible artifact or explicit blocker.

- `hooks/resolver/standing-order-guard.sh`
  - Existing injected prompt made standing orders persistent on every `UserPromptSubmit`.
  - New injected text adds productive-turn requirement so standing-order fires cannot be pure status checks.

- `skills/_ticket-lifecycle-rules.md`
  - New always-on rule cohort defines lifecycle states and platform fallback comments.

- `skills/update-ticket/SKILL.md`, `skills/create-pr/SKILL.md`, `skills/close-ticket/SKILL.md`
  - Updated action skills now own the lifecycle status transitions they trigger.

## Coherence

The common mechanism is moving enforcement to the action boundary:

- parent session spawn call, before an unisolated child exists;
- drive-mode setup and fired-turn prompt, before the agent can yield without producing work;
- ticket lifecycle action skill, before status drift can become stale project-board state.

This preserves platform agnosticism: where a platform lacks mutable status fields, the rule requires an explicit `Status: <state>` comment with evidence.

## Falsification

This change is false if any of these hold:

- A write-capable `spawn_session` in a Git repo without worktree/read-only language exits 0 in `spawn_guard.test.sh`.
- A drive-handoff fired turn can comply while producing only a pure `nothing changed` status check.
- A PR creation workflow can comply without either moving the ticket to In Review or writing a `Status: In Review` fallback comment.
- Hook validation or package validation fails after build.
