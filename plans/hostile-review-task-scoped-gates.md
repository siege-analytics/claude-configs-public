# Hostile review: task-scoped gates

Reviewer source: independent secondary model, Sonnet-class with extended reasoning.

## Verdict

Initial verdict: BLOCK.

Final author response: blocking findings were accepted and fixed before PR. The high-severity issues identified here are covered by expanded regression tests.

## Findings

### HIGH: post-resolver repo-local fallback revived rejected gates

The first implementation changed workspace-root fallback behavior but still used raw `$REPO_ROOT/.think-gate.json` after scoped resolver rejection in the resolver prompt gates. That could make a same-repo gate from another session affect the current task.

Resolution: prompt gates now use a missing sentinel after resolver rejection instead of raw `.think-gate.json` fallback.

Evidence: `bash hooks/_test/session_signal_resolution.test.sh` includes same-repo foreign-session local gate cases.

### HIGH: mutation gate raw local fallback remained unscoped

The first implementation suppressed workspace-root fallback in `universal-mutation-gate.sh`, but still allowed `CWD/.think-gate.json` to be used after scoped resolver rejection.

Resolution: the mutation gate skips raw local fallback when repo root and resolver are available.

Evidence: `bash hooks/_test/session_signal_resolution.test.sh` includes mutation rejection for same-repo foreign-session local gates.

### MEDIUM: env override was trusted directly

The first implementation passed `CLAUDE_THINK_GATE` into shell variables before scoped validation, so a stale env override could still become session-global or workspace-global state.

Resolution: `hooks/lib/resolve-think-gate.py` now validates env override, workspace scoped, repo-local, and legacy singleton gates against current repo/session metadata.

Evidence: `bash hooks/_test/session_signal_resolution.test.sh` includes env override rejection for a foreign-session gate.

### LOW: hub source-selection rule allowed unrecorded rationale

Resolution: `session-coordination:7` now requires the source-selection rationale to be recorded in the spoke prompt, hub plan, or operator checkpoint.

### LOW: retirement rule did not require durable handoff location

Resolution: `session-coordination:8` now requires the retirement record to name a durable handoff location before marking a spoke safe to archive/delete.
