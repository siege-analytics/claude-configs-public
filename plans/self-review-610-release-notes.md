---
ticket_refs:
  - siege-analytics/claude-configs-public#610
---

# Self-Review - release notes and changelog continuity

## Assumptions

Goal source: siege-analytics/claude-configs-public#610.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: `CHANGELOG.md` had current release history only through `3.5.0`, while GitHub releases v3.5.11-v3.5.18 had boilerplate notes. `.github/workflows/build-and-publish.yml` used a hardcoded `gh release create --notes` string.
Hostile-review-artifact: pending.
Inventoried-shape: `CHANGELOG.md`, `.github/workflows/build-and-publish.yml`, `scripts/ci/`.

## Peer review

Shelf checks:

- Added `scripts/ci/release-notes.py` to generate release notes from a target version section or non-empty `[Unreleased]`.
- Release generation fails if neither source has meaningful text.
- Wired GitHub Release creation to use `--notes-file` generated from `CHANGELOG.md` rather than hardcoded boilerplate.
- Added a regression test for non-empty and empty changelog behavior.
- Backfilled v3.5.11-v3.5.18 behavior-changing release entries and added current `[Unreleased]` notes for #610.

## Lead review

[Lead] This fixes both symptoms: downstream consumers get backfilled source-of-truth entries, and the release pipeline now blocks or emits meaningful release notes instead of silently publishing boilerplate.

[Lead] The workflow still appends package asset/tag details, so consumers retain installation pointers while receiving behavior notes.

## Quantified claims

- Recent version entries backfilled: 8 (`3.5.11` through `3.5.18`).
- Release-note generator scripts added: 1.
- Release-note regression tests added: 1.
- Hardcoded release boilerplate call sites replaced: 1.

## Verification commands

```text
bash scripts/ci/test_release_notes.sh
python3 scripts/ci/release-notes.py --version 3.5.19 --check
python3 scripts/ci/release-notes.py --version 3.5.19 --out /tmp/release-notes-610.md
python3 -m py_compile scripts/ci/release-notes.py
bash skills/detect-ai-fingerprints/scan.sh
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `bash scripts/ci/test_release_notes.sh`: passed.
- `python3 scripts/ci/release-notes.py --version 3.5.19 --check`: passed.
- `python3 scripts/ci/release-notes.py --version 3.5.19 --out /tmp/release-notes-610.md`: generated notes from `[Unreleased]`.
- `python3 -m py_compile scripts/ci/release-notes.py`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
