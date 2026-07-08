---
ticket_refs:
  - siege-analytics/claude-configs-public#615
---

# Design - session-scoped signal files

## Problem

Workspace-root signal files are shared by all sessions in the workspace. A concurrent session can overwrite `standing-order.json`, `think-gate.json`, `investigate-gate.json`, or `review-gate.json` with another ticket's state. The observed incident was an ellington-web session seeing root signals overwritten to reference `siege-analytics/claude-configs-public#457` from a different session.

## Approach

1. Extend `hooks/lib/resolve-think-gate.py` so all gate types prefer session-scoped paths before repo/workspace fallbacks.
2. Update hooks that do not use the helper, especially `standing-order-guard.sh`, to prefer session-scoped standing-order signals.
3. Update docs/skills to instruct agents to write session-scoped signal files first.
4. Keep legacy workspace-root files as fallback for backward compatibility.
5. Add direct regression tests proving session-scoped signals override conflicting workspace-root signals.

## Resolution order

For gate files resolved by `resolve-think-gate.py`:

1. explicit env override,
2. `$CLAUDE_SIGNAL_DIR` / `$CRAFT_AGENT_SIGNAL_DIR`,
3. `$CRAFT_AGENT_SESSION_DIR` / `$CLAUDE_SESSION_DIR`,
4. `<workspace>/sessions/<session-id>/`, where `<session-id>` comes from env or hook input JSON,
5. `<workspace>/session-signals/<session-id>/`, where `<session-id>` comes from env or hook input JSON,
6. repo-scoped workspace file,
7. repo-local file,
8. legacy workspace-root singleton.

For standing orders, use the same session-first strategy with `standing-order.json`.

## Verification plan

- Add `hooks/_test/session_signal_resolution.test.sh`, including env-based and hook-input-JSON-based session identity cases.
- Run syntax checks for modified Python/shell files.
- Run signal-resolution, spawn, and coordinator guard tests.
- Run hook validation, build, package validation, sync, and fingerprint scan.
