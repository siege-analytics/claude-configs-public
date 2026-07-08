---
ticket_refs:
  - siege-analytics/claude-configs-public#615
---

# Investigation - session-scoped signal files

## Prior knowledge

- Workspace-root signal files are singleton state and can be overwritten by any session in the same workspace.
- The observed failure involved a session reading signal files that referenced another repo/ticket.
- Existing repo-scoped gate work (#494/#578) reduced cross-repo collision but did not solve same-workspace multi-session collision.

## Verified shapes

- `hooks/lib/resolve-think-gate.py`
  - Before: env override, workspace repo-scoped, workspace singleton, repo-local.
  - After: env override, session signal dirs, `<workspace>/sessions/<session-id>/`, `<workspace>/session-signals/<session-id>/`, workspace repo-scoped, repo-local, legacy workspace singleton. Session id is derived from env or hook input JSON.

- `hooks/resolver/standing-order-guard.sh`
  - Before: `CLAUDE_STANDING_ORDER` or `<workspace>/standing-order.json`.
  - After: env override, signal/session dirs, session-id directories from env or hook input JSON, then legacy workspace singleton.

- `hooks/resolver/skill-enforcement-gate.sh`
  - Before: helper call without repo/session context fell back to workspace singleton.
  - After: uses helper `--all`, which now returns session-scoped active gates first.

- `hooks/_test/session_signal_resolution.test.sh`
  - Creates conflicting session and workspace-root signal files.
  - Verifies the session-scoped think gate wins via env session id.
  - Verifies the session-scoped think gate wins via hook input JSON session id.
  - Verifies the session-scoped standing order wins via signal dir.
  - Verifies the session-scoped standing order wins via hook input JSON session id with session env vars absent.

- Documentation updates
  - `RESOLVER.md`, `skills/think/SKILL.md`, `skills/investigate/SKILL.md`, `skills/cross-review/SKILL.md`, `hooks/README.md`, and Craft watchdog artifacts now instruct session-scoped signals first and mark workspace root as legacy fallback.

## Coherence

The fix moves the state ownership boundary from workspace to session. Hooks still support existing root files, but when a session id or session signal directory is available, that session's files are selected first. That prevents another session's standing order or pipeline gate from becoming the current session's directive.

## Falsification

The fix is false if:

- `hooks/_test/session_signal_resolution.test.sh` fails;
- a session-scoped `think-gate.json` loses to a conflicting workspace-root `think-gate.json`;
- a session-scoped `standing-order.json` loses to a conflicting workspace-root `standing-order.json`;
- legacy workspace-root signals stop working when no session signal exists.
