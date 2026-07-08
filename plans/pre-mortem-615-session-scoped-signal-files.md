---
ticket_refs:
  - siege-analytics/claude-configs-public#615
---

# Pre-Mortem - session-scoped signal files

Fact sheet: `plans/investigate-615-session-scoped-signal-files.md`
Design: `plans/design-615-session-scoped-signal-files.md`

## Tigers

### Tiger 1: Existing consumers lose their legacy root signals

- Evidence: current users may still write `<workspace>/think-gate.json` or `<workspace>/standing-order.json`.
- Severity: HIGH
- Urgency: Launch-Blocking
- Mitigation: keep workspace-root singleton files as final fallback.
- Status: Mitigated.

### Tiger 2: Session resolver still chooses another session's signal

- Evidence: helper `--all` previously scanned workspace-root files globally.
- Severity: HIGH
- Urgency: Launch-Blocking
- Mitigation: session dirs are searched before workspace-root files; regression test creates conflicting root/session files and asserts session wins.
- Status: Mitigated.

### Tiger 3: Standing-order guard remains singleton-only

- Evidence: standing-order guard did not use the shared resolver.
- Severity: HIGH
- Urgency: Launch-Blocking
- Mitigation: add explicit session-first standing-order path resolver.
- Status: Mitigated.

## Paper Tigers

### Paper Tiger 1: Session id env var names vary

- Why handled: resolver supports explicit signal-dir env vars, session-dir env vars, common session id names, and hook input JSON session ids. Explicit env override remains highest priority.

## Elephant

### Elephant 1: Platform may not expose session env vars to all hooks

- Disposition: mitigated. Fallback remains backward-compatible, and isolation can use explicit signal dirs, session env vars, or hook input JSON session ids. If a runtime exposes none of these, it can still set `CLAUDE_SIGNAL_DIR` / `CRAFT_AGENT_SIGNAL_DIR`.
- Revisit trigger: another cross-session overwrite report after consumers are updated to v3.5.x with this release.

## Launch decision

No unmitigated launch-blocking Tigers remain.
