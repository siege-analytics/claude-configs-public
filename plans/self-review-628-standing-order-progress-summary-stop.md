---
ticket_refs:
  - siege-analytics/claude-configs-public#628
---

# Self-Review - standing-order progress-summary stop

## Assumptions

Goal source: siege-analytics/claude-configs-public#628.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: operator identified a standing-order violation: after an explicit go order to finish all open issues, the agent stopped with a progress summary while open issues remained.
Hostile-review-artifact: not required for small instruction/runtime text correction.
Inventoried-shape: `RESOLVER.md`, `hooks/resolver/standing-order-guard.sh`, `skills/drive-while-away/SKILL.md`.

## Peer review

Shelf checks:

- Added explicit resolver rule: progress-summary stops are violations while pending work remains.
- Updated standing-order guard runtime injection to require starting the next item after a progress summary when the queue is not empty.
- Updated drive-while-away skill to name multi-item progress-summary stops, not only one-item praise stops.
- Added current changelog entry.

## Lead review

[Lead] The violation was not forgetting the standing order; it was treating a status summary as a natural stopping point after several completions. The fix names that shape directly.

[Lead] This patch does not create a new process. It clarifies the existing termination conditions: complete, blocked, deadline, or user termination.

## Quantified claims

- Standing-order runtime injection updated: 1.
- Standing-order skill/resolver docs updated: 2.
- New termination conditions added: 0; existing conditions clarified.

## Verification commands

```text
bash -n hooks/resolver/standing-order-guard.sh
bash skills/detect-ai-fingerprints/scan.sh
python3 scripts/ci/release-notes.py --version 3.5.23 --check
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `bash -n hooks/resolver/standing-order-guard.sh`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 scripts/ci/release-notes.py --version 3.5.23 --check`: passed.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
