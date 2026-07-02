---
ticket_refs:
  - siege-analytics/claude-configs-public#248
  - siege-analytics/claude-configs-public#345
  - siege-analytics/claude-configs-public#612
---

# Self-Review - lifecycle, spawn isolation, and drive-handoff follow-up

## Assumptions

Goal source: siege-analytics/claude-configs-public#248, #345, #612.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: `plans/investigate-248-345-612-lifecycle-spawn-autonomy.md`.
Hostile-review-artifact: `plans/hostile-review-248-345-612-lifecycle-spawn-autonomy.md`.
Inventoried-shape: `hooks/agent-comms/spawn-guard.sh`, `hooks/_test/spawn_guard.test.sh`, `skills/_ticket-lifecycle-rules.md`, `skills/drive-while-away/SKILL.md`, `hooks/resolver/standing-order-guard.sh`, ticket lifecycle skills.

## Peer review

Shelf checks:

- Spawn isolation: `hooks/_test/spawn_guard.test.sh` covers missing worktree block, inherited working-directory block, worktree instruction pass, and read-only review carve-out.
- Existing coordinator guard: `hooks/_test/coordinator_status_guard.test.sh` still passes after follow-up changes.
- Hook validation: `python3 bin/validate-hooks.py` validates source hooks.
- Package validation: `python3 bin/validate-hooks.py dist/claude-code/` and `python3 bin/validate-hooks.py dist/craft-agent/` validate generated packages.
- Reference sync: `python3 bin/sync-skill-references.py --check` is clean.
- Prose/fingerprint scan: `bash skills/detect-ai-fingerprints/scan.sh --working` is clean.

## Lead review

[Lead] #248: The fix enforces isolation at the parent spawn boundary. It cannot create a worktree inside the platform, but it blocks write-capable Git-repo child spawns that omit worktree isolation or read-only intent.

[Lead] #345: The fix expands drive-handoff recognition and changes fired-turn semantics from passive checking to durable forward motion. Standing-order injection now repeats the productive-turn bar.

[Lead] #612: The fix moves lifecycle status transitions into an always-on rule cohort plus the action skills that perform each lifecycle step. Platform-specific field limitations are handled through `Status: <state>` fallback comments.

## Quantified claims

- Spawn guard scenarios: 11 passed, 0 failed.
- Coordinator guard scenarios: 38 passed, 0 failed.
- Hook validation targets: source tree, `dist/claude-code/`, `dist/craft-agent/`.
- Open tickets addressed by this diff: 3 (#248, #345, #612).

## Verification commands

```text
bash -n hooks/agent-comms/spawn-guard.sh hooks/resolver/standing-order-guard.sh hooks/_test/spawn_guard.test.sh hooks/_test/coordinator_status_guard.test.sh
bash hooks/_test/spawn_guard.test.sh
bash hooks/_test/coordinator_status_guard.test.sh
python3 bin/validate-hooks.py
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
python3 bin/sync-skill-references.py --check
bash skills/detect-ai-fingerprints/scan.sh --working
```

## Results

- Spawn guard tests: 11 passed, 0 failed.
- Coordinator guard tests: 38 passed, 0 failed.
- Hook validation: all hooks valid; existing unreferenced-hook warnings only.
- Build: succeeded.
- Package validation: all hooks valid; existing unreferenced-hook warnings only.
- Skill reference sync: clean.
- Fingerprint scan: clean.

## Residual risk

- #248 platform-level automatic worktree creation is still outside this repo's direct control. This PR enforces the spawn contract at the parent hook boundary, including the default inherited-working-directory case.
- #612 field updates remain platform-dependent; fallback comments preserve state when no mutable Status field is available.
