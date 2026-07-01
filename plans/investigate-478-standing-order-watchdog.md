---
ticket_refs:
  - siege-analytics/claude-configs-public#478
---

# Investigation Fact Sheet - #478 standing-order watchdog

Task: Finish Craft Agent package standing-order watchdog artifacts.
Ticket: siege-analytics/claude-configs-public#478
Investigated: 2026-07-01
Approach: `plans/design-478-standing-order-watchdog.md`

## Prior Knowledge

- Ticket body read: YES. #478 acceptance includes "Standing order watchdog config in craft-agent package" and the design names `automations-snippet.json` plus `standing-order-watchdog.json` as Craft Agent package artifacts.
- Ticket comment read: YES. Current status is 6 of 7 acceptance criteria met; remaining gap is "Standing order watchdog config (automations-snippet.json / standing-order-watchdog.json in craft-agent package): not present. Needs operator decision on exact automation shape before inclusion."
- Related ticket #477 read: YES. It states the existing `standing-order-guard.sh` is advisory-only and cannot compel a stopped agent; the `Stop` automation surface would be ideal, but command actions were removed, so an external watchdog or platform constraint is needed.
- Automations docs read: YES. Supported schema is `version: 2`, event-keyed `automations`, `SchedulerTick` with `cron`, and prompt actions.

## Knowledge Loci

- **Standing-order rule:** `RESOLVER.md:338-381`. Current state defines signal-file continuity and the no-idle invariant. This task clarifies packaging, not the rule semantics.
- **Pure Claude/Codex hook:** `hooks/resolver/standing-order-guard.sh:1-90`. Current state reads `standing-order.json` and injects the shift directive on every `UserPromptSubmit`.
- **Hook documentation:** `hooks/README.md:27`. Current state documents the pure hook but not the Craft automation package artifacts.
- **Craft package build:** `bin/build.py:1015-1075` and `bin/build.py:1163-1220`. Current state generates Craft enforcement files and consumer packages but has no automation artifact copy step.

## Impact Chain

### Upstream

- #478 design expects `dist/craft-agent/automations-snippet.json` and `dist/craft-agent/standing-order-watchdog.json`.
- Craft Agent automation schema supports `SchedulerTick`, `SessionStatusChange`, and prompt actions per docs.

### This Task

- Add source files under a Craft-specific directory.
- Add build copy logic so those source files appear only in `dist/craft-agent/`.
- Update documentation to explain the dual runtime split.

### Downstream

- Release packages consume `dist/craft-agent/` and `dist/claude-code/`.
- Craft Agent users get the automation snippet in release artifacts.
- Claude/Codex users remain on the flat hook/settings version and are not given Craft-only automation config.

## Verified Shapes

- **Resolver standing-order rule** (`RESOLVER.md:338`)
  - SEMANTIC: standing order means autonomous work until deadline/exhaustion/blockage | ATTESTED: `RESOLVER.md:338-381`
  - CORRECTNESS: no-idle invariant includes scheduled wakeup/running agents/active tool call/work remaining | ATTESTED: `RESOLVER.md:359-379`

- **Standing-order hook** (`hooks/resolver/standing-order-guard.sh:29`)
  - SCHEMATIC: signal path is `${CLAUDE_STANDING_ORDER:-$WORKSPACE_ROOT/standing-order.json}` | ATTESTED: `hooks/resolver/standing-order-guard.sh:27-29`
  - SEMANTIC: active signal causes a shift-work directive to be emitted | ATTESTED: `hooks/resolver/standing-order-guard.sh:67-90`

- **Build consumer package loop** (`bin/build.py:1185`)
  - SCHEMATIC: consumer package targets are `claude-code` and `craft-agent` | ATTESTED: `bin/build.py:1185-1187`
  - SEMANTIC: target-specific branching already exists for settings filtering and Craft skill stripping | ATTESTED: `bin/build.py:1211-1231`

- **Craft automation schema** (`automations.md`)
  - SCHEMATIC: top-level `version: 2`, `automations`, event arrays, prompt actions | ATTESTED: docs read before implementation
  - SEMANTIC: `SchedulerTick` supports cron; `SessionStatusChange` supports matcher on new status | ATTESTED: docs read before implementation

## Coherence

The existing hook implements the pure runtime version; the missing piece is only the Craft-native automation artifact. Adding Craft-specific source files plus a Craft-only build copy step satisfies #478 without weakening the flat package.

## Hypothesis and Falsification

Hypothesis: after implementation, `python3 bin/build.py` will produce `dist/craft-agent/automations-snippet.json` and `dist/craft-agent/standing-order-watchdog.json`, while `dist/claude-code/` will not contain Craft-only automation files.

Falsification:

- Build exits non-zero.
- Either Craft artifact is absent from `dist/craft-agent/`.
- Either Craft artifact appears in `dist/claude-code/`.
- JSON syntax validation fails for either source artifact.
