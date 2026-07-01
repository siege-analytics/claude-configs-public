---
ticket_refs:
  - siege-analytics/claude-configs-public#478
---

# Fresh Review: #478 standing-order watchdog package artifacts

Reviewer path: fresh Craft Agent session spawned as `260701-mild-aspen` on `chatgpt-plus` / `pi/gpt-5.5` in execute mode with the staged diff attached.

Fallback validation: fresh-context `call_llm` validation on the same staged diff returned:

```json
{"valid": true, "errors": [], "warnings": []}
```

## Verdict

APPROVE.

## Findings

No blocking findings.

## Review notes

- Craft-only packaging path is scoped to `target == "craft-agent"` before copying `automations-snippet.json` and `standing-order-watchdog.json` (`bin/build.py:1236-1242`).
- Claude/Codex package settings are still generated from the filtered hook/settings snippet path (`bin/build.py:1212-1218`) and the new Craft automation artifacts are not copied in that branch.
- The Craft automation snippet uses the documented v2 automation shape with `SchedulerTick`, `SessionStatusChange`, `cron`, `matcher`, `permissionMode`, and prompt actions (`craft-agent/automations-snippet.json:1-32`).
- Current package outputs match the acceptance split: `dist/craft-agent/` contains both watchdog artifacts, while `dist/claude-code/` contains neither.
