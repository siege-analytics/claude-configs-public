---
ticket_refs:
  - siege-analytics/claude-configs-public#615
---

# Self-Review - session-scoped signal files

## Assumptions

Goal source: siege-analytics/claude-configs-public#615.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: `plans/investigate-615-session-scoped-signal-files.md`.
Hostile-review-artifact: pending fresh review.
Inventoried-shape: `hooks/lib/resolve-think-gate.py`, `hooks/resolver/standing-order-guard.sh`, `hooks/resolver/skill-enforcement-gate.sh`, signal-file documentation.

## Peer review

Shelf checks:

- `hooks/_test/session_signal_resolution.test.sh` proves session-scoped think and standing-order signals win over conflicting workspace-root files via env session identity and hook input JSON session identity.
- `hooks/_test/spawn_guard.test.sh` and `hooks/_test/coordinator_status_guard.test.sh` still pass, preserving recent enforcement work.
- `python3 -m py_compile hooks/lib/resolve-think-gate.py` verifies Python syntax.
- `bash -n` verifies modified shell hooks/tests.
- `python3 bin/validate-hooks.py` verifies hook references.
- `python3 bin/build.py` verifies package generation.
- `python3 bin/sync-skill-references.py --check` verifies rule/skill tokens.
- `bash skills/detect-ai-fingerprints/scan.sh --working` reports clean.

## Lead review

[Lead] The fix changes signal ownership from workspace-global to session-first while preserving legacy workspace-root fallback. This directly addresses cross-session overwrite and misattribution.

[Lead] The shared resolver handles think, investigate, review, and other gate types. Standing-order had bespoke resolution, so it now has its own session-first resolver.

[Lead] Documentation now instructs writers to place signals under session directories first, which prevents new sessions from continuing to create root singletons.

## Quantified claims

- Session signal precedence scenarios: 4 passed, 0 failed.
- Spawn guard scenarios: 11 passed, 0 failed.
- Coordinator status guard scenarios: 38 passed, 0 failed.
- Hook validation targets: source tree plus generated packages.

## Verification commands

```text
python3 -m py_compile hooks/lib/resolve-think-gate.py
bash -n hooks/resolver/standing-order-guard.sh hooks/resolver/skill-enforcement-gate.sh hooks/_test/session_signal_resolution.test.sh
bash hooks/_test/session_signal_resolution.test.sh
bash hooks/_test/spawn_guard.test.sh
bash hooks/_test/coordinator_status_guard.test.sh
python3 bin/validate-hooks.py
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
python3 bin/sync-skill-references.py --check
bash skills/detect-ai-fingerprints/scan.sh --working
```

## Results

- Session signal tests: 4 passed, 0 failed.
- Spawn guard tests: 11 passed, 0 failed.
- Coordinator status tests: 38 passed, 0 failed.
- Hook validation: all hooks valid; existing unreferenced-hook warnings only.
- Build: succeeded.
- Reference sync: clean.
- Fingerprint scan: clean.

## Residual risk

A runtime that exposes no session id, no session/signal directory, and no hook input JSON session id can only use legacy fallback. The patch supports explicit `CLAUDE_SIGNAL_DIR` / `CRAFT_AGENT_SIGNAL_DIR`, session env vars, and hook input JSON session ids so runtimes can opt into isolation without changing signal file schemas.
