---
ticket_refs:
  - siege-analytics/claude-configs-public#625
---

# Self-Review - stale Unreleased reuse

## Assumptions

Goal source: siege-analytics/claude-configs-public#625.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: release v3.5.20 shipped #282 code but GitHub Release notes reused the stale #610 `[Unreleased]` text.
Hostile-review-artifact: not required for changelog-only follow-up.
Inventoried-shape: `CHANGELOG.md`, `docs/release-notes.md`, `scripts/ci/release-notes.py` behavior.

## Peer review

Shelf checks:

- Moved the stale #610 `[Unreleased]` content into a concrete v3.5.19 section.
- Added v3.5.20 notes for #282.
- Added a fresh `[Unreleased]` note for #625.
- Added `docs/release-notes.md` documenting that behavior-changing PRs must update `[Unreleased]` before merge.

## Lead review

[Lead] This fixes the immediate release-note mismatch and documents the workflow gap that caused it.

[Lead] The generator still uses `[Unreleased]` for auto-version releases; the repository now documents the required discipline for keeping that section current.

## Quantified claims

- Backfilled concrete version sections: 2 (`3.5.19`, `3.5.20`).
- New release-note discipline docs: 1.

## Verification commands

```text
python3 scripts/ci/release-notes.py --version 3.5.21 --check
python3 scripts/ci/release-notes.py --version 3.5.21 --out /tmp/release-notes-625.md
bash skills/detect-ai-fingerprints/scan.sh
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `python3 scripts/ci/release-notes.py --version 3.5.21 --check`: passed.
- `python3 scripts/ci/release-notes.py --version 3.5.21 --out /tmp/release-notes-625.md`: generated notes from fresh `[Unreleased]` #625 text.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
