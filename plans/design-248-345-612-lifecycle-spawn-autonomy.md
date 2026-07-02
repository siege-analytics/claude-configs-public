---
ticket_refs:
  - siege-analytics/claude-configs-public#248
  - siege-analytics/claude-configs-public#345
  - siege-analytics/claude-configs-public#612
---

# Design - lifecycle, spawn isolation, and drive-handoff follow-up

## Problem

Three open governance tickets describe the same broad failure class: lifecycle state can drift from reality when enforcement is optional or located in the wrong runtime.

- #248: spawned write-capable sessions can share a Git working tree and race on HEAD/index/stash.
- #345: drive-handoff turns can fire existing autonomy mechanisms but produce no durable forward motion.
- #612: ticket status transitions are passive and live in update-ticket notes rather than the skills that perform lifecycle stages.

## Approach

1. Extend `hooks/agent-comms/spawn-guard.sh` so write-capable child sessions in a Git repository must either be read-only/no-file-edits or declare git worktree isolation.
2. Add spawn guard regression tests for write-capable Git child sessions without worktrees, with worktree instructions, and read-only review carve-out.
3. Add `skills/_ticket-lifecycle-rules.md` as an always-on lifecycle status rule cohort.
4. Update `skills/update-ticket/SKILL.md`, `skills/create-pr/SKILL.md`, and `skills/close-ticket/SKILL.md` so status transitions are driven at work start, PR open, testing/UAT handoff, blocked/unblocked, and close.
5. Update `skills/drive-while-away/SKILL.md` with expanded drive-handoff triggers, required work inventory, productive-turn bar, and end-of-turn self-check.
6. Update `hooks/resolver/standing-order-guard.sh` so standing-order injected prompts include the productive-turn bar.

## Acceptance mapping

- #248: parent-side spawn guard blocks unisolated write-capable Git child sessions before the child starts.
- #345: drive-handoff skill now recognizes broader operator handoff phrases and requires an inventory plus operator-visible artifact per fired turn.
- #612: ticket lifecycle transitions are rule-backed and wired into the skills that perform the transitions.

## Verification plan

- `bash hooks/_test/spawn_guard.test.sh`
- `bash hooks/_test/coordinator_status_guard.test.sh`
- `bash -n hooks/agent-comms/spawn-guard.sh hooks/resolver/standing-order-guard.sh`
- `python3 bin/sync-skill-references.py --check`
- `python3 bin/validate-hooks.py`
- `python3 bin/build.py`
- `python3 bin/validate-hooks.py dist/claude-code/`
- `python3 bin/validate-hooks.py dist/craft-agent/`
- `bash skills/detect-ai-fingerprints/scan.sh --working`
