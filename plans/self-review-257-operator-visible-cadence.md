---
ticket_refs:
  - siege-analytics/claude-configs-public#257
---

# Self-Review - operator-visible cadence honesty

## Assumptions

Goal source: siege-analytics/claude-configs-public#257.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: issue reports that Monitor/ScheduleWakeup-style async events did not surface in the operator chat UI, so repo guidance must stop promising visible cadence when a runtime only provides agent re-entry.
Hostile-review-artifact: not required for docs/runtime-injection wording correction.
Inventoried-shape: `skills/drive-while-away/SKILL.md`, `skills/_writing-prose-rules.md`, `skills/RESOLVER.md`, `RESOLVER.md`, `hooks/resolver/standing-order-guard.sh`.

## Peer review

Shelf checks:

- Drive skill now separates scheduler re-entry from operator-visible chat delivery.
- Craft Agent fallback guidance uses foreground tool calls, durable artifacts, issue/PR comments, branch pushes, and verification files.
- Universal resolver no longer hard-codes ScheduleWakeup as the only valid standing-order re-entry mechanism.
- Runtime injection no longer tells sessions without ScheduleWakeup to use an unavailable tool.
- Future-action prose rule now forbids promising live chat updates from unproven async surfacing.

## Lead review

[Lead] The product failure was not only missing cadence. It was an honesty bug: the tool promise sounded visible to the operator while evidence showed agent-internal events. This patch makes the claim boundary visible at the rule, skill, resolver, and injected-runtime levels.

[Lead] The patch does not remove scheduling guidance for Claude/Codex runtimes. It scopes the guarantee: scheduler tools may provide re-entry, but visibility must be proven before promising chat cadence.

## Quantified claims

- Async primitive names covered in changed guidance: `CronCreate`, `ScheduleWakeup`, `Monitor`.
- Runtime layers updated: skill guidance, writing-prose rule, skill resolver, universal resolver, standing-order guard injection.
- Craft Agent visible-evidence channels named: foreground tool results, durable artifacts, issue/PR comments, branch pushes, verification files.

## Verification commands

```text
bash -n hooks/resolver/standing-order-guard.sh
bash skills/detect-ai-fingerprints/scan.sh
python3 scripts/ci/release-notes.py --version 3.5.24 --check
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `bash -n hooks/resolver/standing-order-guard.sh`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 scripts/ci/release-notes.py --version 3.5.24 --check`: passed.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
