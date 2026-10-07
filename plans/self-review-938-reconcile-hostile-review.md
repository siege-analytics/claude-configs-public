# Self-review — reconcile hostile-review drift (CCP#938)

## Assumptions

Working as: tech lead, software engineer
Goal source: #938
Pre-author-inventory: #938 design note + the tracked-vs-untracked ground truth in the provisioned workspace. `git ls-files 'skills/*--*'` returns ONLY `skills/siege-utilities--hostile-review/SKILL.md` -- the lone COMMITTED flat stray. The sibling project-skill flats (notebook-impact, error-path-tests) are on-disk but UNTRACKED (build-generated at provisioning). So the runtime reads repo-root flat dirs, and hostile-review is a pre-migration committed build-output that shadows + staleness-beats what the build would produce from the projects/ source.
Investigate-artifact: #938
Pre-mortem-artifact: #938
Project-contribution: Makes the siege hostile-review skill whole at runtime -- #936's P3/P4 reviewer-standard becomes live AND the #1005 P6/Notebook-API-fidelity + Security scan-patterns are preserved in the authoritative source -- and removes the committed stray so the flat regenerates from source like its two siblings instead of a stale copy winning.

Key assumptions:
- The siege routing token resolves from the projects/ source at build/deploy. Verified via RESOLVER + CONTRIBUTING.md + build.py.
- DELETE (not refresh) is correct: the committed flat is the lone tracked stray; its siblings are untracked and regenerate at provisioning, so deleting the committed copy lets hostile-review regenerate the same way. Verified by the ls-files ground truth + the delete+rebuild check below.

## Peer review

- **writing-prose:1 (no AI typography/adverbs).** Added source lines carry no em/en-dashes and no banned adverbs; the one migrated "explicitly" was reworded to "actually". Evidence: `git diff` of the source fold scanned clean.
- **writing-code:6 (doc-edit symmetry).** The projects/ SOURCE now carries P3 + P4 (reference.md) + P6 + Scan-patterns; the committed flat is deleted so it can regenerate from that source. No hand-maintained flat remains to drift.
- **Delete+rebuild integrity (the crux).** After `git rm -r skills/siege-utilities--hostile-review/`, `python3 bin/build.py --layout flat` regenerates `dist/flat/skills/siege-utilities--hostile-review/` from source with red-on-revert + Notebook-API-fidelity + Scan-patterns + SSRF (SKILL, 356 lines, NOT the leaner 165) + round-trip symmetry (reference.md). So delete+rebuild yields a COMPLETE artifact, not a stripped one.
- **Addendum sweep.** `git ls-files 'skills/*--*'` = only the hostile-review stray -> true one-off, no other committed strays to sweep. Reconciliation of the `_rules` concern: `skills/_siege-utilities-rules.md` (SINGLE dash) is TRACKED but is the legitimate general "Siege Utilities First" always-on rule (RESOLVER row 205), not a stray; `skills/_siege-utilities--rules.md` (DOUBLE dash, the flattened project-rules artifact) is correctly UNTRACKED.
- Gate 1 (syntax): N/A -- markdown + a dir deletion.
- Gate 2 (tests): N/A. Validation: `python3 bin/build.py --check` -> exit 0 (tokens resolve); the flat build above regenerates the complete artifact.
- Tiger check (pre-mortem): plain `build.py` wrote only to the gitignored worktree dist/, not the main workspace.
- Gate 3/4 (docs/notebooks): N/A.

## Lead review

- **As tech lead:** DELETE is the clean fix -- the committed flat is the sole tracked stray; removing it makes hostile-review regenerate from source exactly like notebook-impact / error-path-tests. Refresh (the earlier approach) would have re-committed a build-output and re-introduced the drift risk. The delete+rebuild verification proves no content is lost. The general 627-line `skills/hostile-review/` twin is out of scope (D2, separate skill #863); noted, not consolidated.
- **As software engineer:** the source fold was anchored on unique marker strings and verified a clean union (only residual diff vs the old flat was the P3 paragraph). The regenerated artifact is 356 lines with every marker, so the authoritative source is genuinely whole.
- Edited the projects/ SOURCE (authoritative) and deleted the committed flat stray. No AI/assistant attribution anywhere.

## Quantified claims

- **1 committed stray deleted** (`skills/siege-utilities--hostile-review/`, SKILL.md + reference.md). Evidence: `git status -s` shows `D` for both.
- **2 flat-only regions folded into source** (P6 + Scan-patterns; Layer-3 items 7 & 8); P3/P4 preserved. Evidence: source greps (red-on-revert=1, Notebook-API-fidelity=1, SSRF=1; reference.md round-trip=1).
- **delete+rebuild regenerates 356-line complete artifact** (> the 165-line leaner source), all 5 markers. Evidence: build-flat output greps above.
- **0 other committed strays.** Evidence: `git ls-files 'skills/*--*'` = 1 entry (the one deleted).
- **build --check exit 0.** Evidence: command output.
