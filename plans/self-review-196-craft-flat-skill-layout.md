---
ticket_refs:
  - siege-analytics/claude-configs-public#196
---

# Self-Review - Craft Agent flat skill layout

## Assumptions

Goal source: siege-analytics/claude-configs-public#196.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: affected Craft Agent workspaces resolve bare skill slugs against top-level `skills/<slug>/SKILL.md` only. CCP already publishes `release/flat`, but package/CI should make that invariant hard to regress and document the required consumption layout.
Hostile-review-artifact: pending fresh review after PR.
Inventoried-shape: `bin/build.py`, CI workflow, README distribution docs, flat-layout regression test, changelog.

## Peer review

Shelf checks:

- Added build-time `validate_flat_skill_paths()` so non-shelves, non-router leaf skills must publish to top-level `skills/<slug>/` in flat layout.
- Added craft-agent package assertion for the two concrete failing slugs from #196: `code-review` and `qml-component-review`.
- Added `scripts/ci/test_flat_skill_layout.sh` regression test covering concrete slugs and all non-shelves leaf skills.
- Wired the regression test into GitHub validation workflow.
- Updated README to state Craft Agent consumers must use `release/flat` or the `craft-agent` package.
- Added current changelog entry.

## Lead review

[Lead] This patch does not claim to fix the host resolver. It hardens CCP's artifact contract so Craft Agent-compatible outputs keep bare-slug leaf skills at top level and documents that nested consumption is the wrong layout for that host behavior.

[Lead] The test includes the incident slugs and a broader sweep so future nested leaf additions cannot silently ship unreachable in flat/Craft outputs.

## Quantified claims

- Incident slugs guarded directly: 2 (`code-review`, `qml-component-review`).
- Build validation layers added: 2 (flat layout, craft-agent package).
- CI tests added: 1 focused shell test.

## Hook-Dependencies

- `scripts/ci/test_flat_skill_layout.sh`: safe dependencies: bash, python3; fallback behavior: loud non-zero exit.
- `bin/build.py`: safe dependencies for new validation: Python standard library only; fallback behavior: raises `BuildError`.

## Verification commands

```text
python3 -m py_compile bin/build.py
bash scripts/ci/test_flat_skill_layout.sh
bash skills/detect-ai-fingerprints/scan.sh
python3 scripts/ci/release-notes.py --version 3.5.26 --check
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `python3 -m py_compile bin/build.py`: passed.
- `bash scripts/ci/test_flat_skill_layout.sh`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean; emitted known `config_arg[@]: unbound variable` warning before clean result.
- `python3 scripts/ci/release-notes.py --version 3.5.26 --check`: passed.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
