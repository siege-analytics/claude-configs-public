---
ticket_refs:
  - siege-analytics/claude-configs-public#478
---

# Pre-Mortem - #478 standing-order watchdog

Task: Finish Craft Agent package standing-order watchdog artifacts.
Ticket: siege-analytics/claude-configs-public#478
Fact Sheet: `plans/investigate-478-standing-order-watchdog.md`
Design note: `plans/design-478-standing-order-watchdog.md`

## Tigers

### Tiger 1: Craft artifact ships to both packages

- Scenario: Craft-only automation config is copied into `dist/claude-code/`, confusing pure Claude/Codex consumers with unsupported automation schema.
- Evidence: consumer package loop builds both targets from the same function (`bin/build.py:1185-1217`) and currently uses target-specific logic only for settings filtering.
- Severity: 45 (monitor-after-ship)
- Urgency: Fast-Follow
- Trigger condition: artifact copy logic is placed outside the `target == "craft-agent"` branch.
- Mitigation: add explicit `if target == "craft-agent"` copy logic and verify the files are absent from `dist/claude-code/` after build.
- Status: Mitigated by implementation plan.

### Tiger 2: Watchdog promise exceeds platform capability

- Scenario: package claims the automation can force a stopped agent to continue, but Craft automations can only fire prompt actions; they cannot retroactively make a completed assistant turn call a tool.
- Evidence: #477 notes the existing hook cannot compel action after stop and identifies external watchdog/platform constraint as the remaining shape.
- Severity: 62 (mitigate-before-ship)
- Urgency: Launch-Blocking unless wording is constrained.
- Trigger condition: artifact language says the watchdog hard-blocks idling instead of saying it spawns/checks continuity and re-injects work.
- Mitigation: reference config must state that SchedulerTick/SessionStatusChange create watchdog sessions/prompts; the hard guarantee remains the signal-file hook plus operator/runtime support.
- Status: Mitigated by wording in the reference config.

## Paper Tigers

### Paper Tiger 1: JSON schema uncertainty blocks source artifact creation

- Scenario: automation snippets might require a CLI-only generated format.
- Why handled: Craft docs define JSON structure directly: top-level `version: 2`, event-keyed `automations`, `cron`, `matcher`, and prompt actions. Use that documented shape.

## Elephants

### Elephant 1: Runtime stop detection is still platform-limited

- What it is: The best enforcement point is an end-of-turn/Stop surface that can require a scheduled wakeup before the agent becomes idle. The package can provide a watchdog automation, but cannot alone guarantee that every runtime compels action.
- Why deferred: #478 is a packaging ticket, not a Craft platform feature.
- Cost of deferral: Watchdog may be advisory/periodic rather than a true hard stop.
- Trigger for revisiting: Craft Agent exposes a first-class end-of-turn action gate or command automation surface.

## Launch-Blocking Assessment

- [x] No Launch-Blocking Tigers remain unmitigated by the implementation plan.
- [x] All Tiger mitigations are grounded in investigated facts.
- [x] Elephant has deferral rationale and revisit trigger.
- Implementation may proceed: YES.
