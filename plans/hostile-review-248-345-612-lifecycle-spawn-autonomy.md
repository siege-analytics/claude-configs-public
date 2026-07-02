---
ticket_refs:
  - siege-analytics/claude-configs-public#248
  - siege-analytics/claude-configs-public#345
  - siege-analytics/claude-configs-public#612
---

# Hostile Review - lifecycle, spawn isolation, and drive-handoff follow-up

Reviewer: fresh Claude session `260702-warm-bamboo`
Mode: allow-all / read-only review contract
Task: Review staged diff for #248, #345, and #612.

## First verdict

`REQUEST_CHANGES`

Blocking finding: #248 worktree isolation guard only fired when `workingDirectory` was explicitly passed. Because `spawn_session` inherits the parent working directory when omitted, the default shared-tree case bypassed the guard.

Accepted fix:

- `spawn-guard.sh` now defaults omitted `workingDirectory` to `os.getcwd()`.
- Worktree check no longer short-circuits on empty `workingDirectory`.
- Added regression: `write-capable git child with inherited working directory blocks`.

## Re-review verdict

`APPROVE`

Reviewer independently verified:

- omitted `workingDirectory` write-like spawn now exits 2 in a Git repo,
- read-only omitted `workingDirectory` still exits 0,
- same write-like omitted payload from non-repo cwd exits 0,
- `spawn_guard.test.sh` passes 11 scenarios,
- `skills/RULES.md` indexes `_ticket-lifecycle-rules.md`.

## Verification at approval

- `bash hooks/_test/spawn_guard.test.sh` -> 11 passed, 0 failed
- `bash hooks/_test/coordinator_status_guard.test.sh` -> 38 passed, 0 failed
- `python3 bin/validate-hooks.py` -> all hooks valid; existing warnings only
- `python3 bin/build.py` -> succeeded
- `python3 bin/validate-hooks.py dist/claude-code/` -> all hooks valid; existing warnings only
- `python3 bin/validate-hooks.py dist/craft-agent/` -> all hooks valid; existing warnings only
- `python3 bin/sync-skill-references.py --check` -> clean
- `bash skills/detect-ai-fingerprints/scan.sh --working` -> clean
