---
ticket_refs:
  - siege-analytics/claude-configs-public#635
---

# Self-Review - goal-mode intention-feints

## Assumptions

Goal source: siege-analytics/claude-configs-public#635, created from operator diagnosis during backlog-drain standing order.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: repeated failures where the agent emitted future-tense transition text and then stopped without the promised tool/action. Existing #628 blocked progress-summary stops, but did not name intention-feint stops.
Hostile-review-artifact: not required for small rule/text correction; local scanner/build validation covers package quality.
Inventoried-shape: universal resolver standing-order rules, runtime standing-order injection, drive-while-away skill, future-action prose rule, changelog.

## Peer review

Shelf checks:

- Added standing-order goal-mode rule: future-tense transition text is valid only with same-turn action, re-entry, or blocker evidence.
- Updated runtime injection so every standing-order turn receives the intention-announcement warning.
- Added drive-while-away failure mode C: intention-feint-then-stop.
- Updated future-action prose rule to classify goal-mode transition announcements as future-action claims.
- Added current changelog entry.

## Lead review

[Lead] The defect was not a missing progress summary rule. The agent found a new escape hatch: announcing motion instead of doing motion. This patch names that shape directly and ties it to same-turn evidence.

[Lead] The fix emulates goal persistence by changing the acceptable turn boundary: a goal-mode turn cannot end on a promise of next action. It must contain the action, a re-entry mechanism, or a blocker.

## Quantified claims

- Rule surfaces updated: 4.
- Runtime injection updated: 1.
- New failure mode named: 1.
- New implementation hooks added: 0; this is instruction/runtime-injection reinforcement.

## Verification commands

```text
bash -n hooks/resolver/standing-order-guard.sh
bash skills/detect-ai-fingerprints/scan.sh
python3 scripts/ci/release-notes.py --version 3.5.28 --check
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `bash -n hooks/resolver/standing-order-guard.sh`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 scripts/ci/release-notes.py --version 3.5.28 --check`: passed.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
