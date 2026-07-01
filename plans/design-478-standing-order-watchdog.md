---
ticket_refs:
  - siege-analytics/claude-configs-public#478
---

# Design - #478 standing-order watchdog package artifacts

## Decision

Standing-order continuity is batch/continuity enforcement: when the operator gives a multi-step directive such as "download thirty shapefiles, load them into PostGIS, then compute overlaps," the agent must keep working through the queue until the work is complete, blocked, or the stated deadline is reached. Completing one unit and stopping for affirmation is the failure this closes.

## Scope

Finish the one remaining #478 acceptance criterion: Craft Agent package includes standing-order watchdog config. Preserve the existing pure Claude/Codex mechanism: flat package includes the resolver rule and `hooks/resolver/standing-order-guard.sh` via `settings-snippet.json`.

## Approach

1. Add source automation artifacts at `craft-agent/automations-snippet.json` and `craft-agent/standing-order-watchdog.json`.
2. Update `bin/build.py` so only `dist/craft-agent/` receives those Craft-native automation files.
3. Keep pure Claude/Codex package behavior as-is: `dist/claude-code/` continues to receive the flat hook/settings implementation but no Craft automation files.
4. Update package documentation to name both surfaces:
   - Claude/Codex: resolver + signal-file hook.
   - Craft Agent: same hook plus optional watchdog automation snippet.

## Operator decisions recorded

- Every change should have both a pure Claude/Codex and a Craft Agent version.
- For standing orders, the target failure is one-item completion followed by praise-seeking/idle stop.
- Craft Agent package should include the watchdog automation config. The existing flat hook remains the pure Claude/Codex version.

## Interface

`craft-agent/automations-snippet.json` is a mergeable `automations.json` fragment using supported Craft Agent automation schema:

- `version: 2`
- `SchedulerTick` automation to periodically spawn a watchdog session.
- `SessionStatusChange` automation to audit sessions marked done/blocked while a standing order may still be active.

`craft-agent/standing-order-watchdog.json` is a reference config documenting the signal file schema, completion criteria, and expected watchdog behavior.

## Verification plan

- `python3 bin/build.py`
- Confirm `dist/craft-agent/automations-snippet.json` exists.
- Confirm `dist/craft-agent/standing-order-watchdog.json` exists.
- Confirm those files do not appear in `dist/claude-code/`.
- Run JSON validation on the new source files.
- Run existing hook validation if available.
