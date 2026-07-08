---
propagation-deferred: PR-only follow-up for open pull request 614; no source issue exists
---

# Self-Review - work-item ownership rules

## Assumptions

Goal source: PR #614.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: PR #614 diff showed the new `_work-item-ownership-rules.md` file existed but was not listed in `skills/RULES.md`.
Hostile-review-artifact: not required for this documentation-only activation fix; PR #614 already passed build validation before this follow-up, and this change only wires the rule into the existing meta-rule index.
Inventoried-shape: `skills/_work-item-ownership-rules.md`, `skills/RULES.md`.

## Peer review

Shelf checks:

- The new rule cohort exists at `skills/_work-item-ownership-rules.md`.
- `skills/RULES.md` now lists `_work-item-ownership-rules.md` in the cross-cutting meta-rule table.
- This makes the cohort discoverable by resolver consumers that load `RULES.md` as the always-on rule entry point.

## Lead review

[Lead] The original PR added useful coordinator/ownership guidance but risked being inert because it did not appear in the active rule index. Adding the row to `RULES.md` is the minimal fix.

[Lead] The rule is still judgment-enforced, but it now reaches the actor. Mechanical enforcement can follow later through spawn prompt guards or outbound coordinator-message detection.

## Quantified claims

- Active-index wiring files changed: 1.
- New rule cohort files already in PR: 1.
- Validation commands below passed locally.

## Verification commands

```text
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
bash skills/detect-ai-fingerprints/scan.sh --working
```

## Result

Passed locally:

- `python3 bin/sync-skill-references.py --check` -> clean.
- `python3 bin/build.py` -> succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/` -> all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/` -> all hooks valid, existing warnings only.
- `bash skills/detect-ai-fingerprints/scan.sh --working` -> clean.
