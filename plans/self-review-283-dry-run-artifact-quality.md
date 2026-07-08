---
ticket_refs:
  - siege-analytics/claude-configs-public#283
---

# Self-Review - dry-run artifact quality

## Assumptions

Goal source: siege-analytics/claude-configs-public#283.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: issue #283 identifies that prose dry-run evidence was presence-checked but not scale-checked; toy probes were rationalized as production evidence.
Hostile-review-artifact: pending.
Inventoried-shape: `hooks/git/self-review.sh`, `skills/investigate/SKILL.md`, `CHANGELOG.md`.

## Peer review

Shelf checks:

- Tightened `hooks/git/self-review.sh` transformation-code gate.
- If a transformation commit uses prose `Pre-ship-dry-run:` evidence and not machine `Probe-Matrix:`, it must also include `Dry-run-scale:` and `Dry-run-falsification:` trailers.
- Updated investigate skill to document the scale and falsification trailers.
- Added current `[Unreleased]` changelog entry so generated release notes describe #283.

## Lead review

[Lead] This targets the failure directly: the previous gate checked that dry-run evidence existed, while this requires the author to name scale and falsified failure modes.

[Lead] Machine-form `Probe-Matrix:` remains preferred and is already validated separately. The new prose gate does not weaken that path.

## Quantified claims

- New required trailers for prose transformation dry-runs: 2.
- Hook enforcement sites changed: 1.
- Skill documentation sites changed: 1.

## Verification commands

```text
bash -n hooks/git/self-review.sh
bash skills/detect-ai-fingerprints/scan.sh
python3 scripts/ci/release-notes.py --version 3.5.22 --check
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `bash -n hooks/git/self-review.sh`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 scripts/ci/release-notes.py --version 3.5.22 --check`: passed.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
