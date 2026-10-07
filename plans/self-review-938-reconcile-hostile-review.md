# Self-review — reconcile hostile-review drift (CCP#938)

## Assumptions

Working as: tech lead, software engineer
Goal source: #938
Pre-author-inventory: #938 design note — investigated the build/deploy model (CRAFT_WORKSPACE == this workspace; bin/build.py `--deploy` copies dist/flat/skills into skills/, so the committed flat IS a stale runtime deploy artifact), the 3-way content matrix (general 627 / project source 165 / stray flat 354), git history showing the stray got #1005 P6/scan-patterns pre-migration, and that sibling project skills have no repo-root flat dir.
Investigate-artifact: #938
Pre-mortem-artifact: #938
Project-contribution: Makes the siege hostile-review skill whole at runtime — #936's P3/P4 reviewer-standard becomes live AND the #1005 P6/Notebook-API-fidelity + Security scan-patterns are preserved in the authoritative source, so the Adversary skill the release-hardening effort depends on is no longer silently missing half its checks.

Key assumptions:
- `[skill:<siege-utilities--hostile-review>]` resolves from the projects/ source at build/deploy. Verified via RESOLVER + CONTRIBUTING.md + build.py.
- Refresh (not delete) is correct: the committed flat is a live deploy target in this workspace. Verified via CRAFT_WORKSPACE == this workspace.

## Peer review

- **writing-prose:1 (no AI typography/adverbs).** Added lines carry no em/en-dashes and no banned adverbs. Evidence: `git diff | grep '^+' | grep -nE 'dashes|adverbs'` -> empty; the one migrated "explicitly" was reworded to "actually". PASS.
- **writing-code:6 (doc-edit symmetry).** Source and its deployed flat were updated together (source spliced; flat regenerated from the built source), so they no longer drift. The new reference.md flat carries P4.
- **Content-union integrity.** The new source == the flat UNION with P3: `diff source flat` shows the ONLY residual difference is the P3 red-on-revert paragraph (expected; P4 lives in reference.md). No content dropped.
- Gate 1 (syntax): N/A — markdown only.
- Gate 2 (tests): N/A — no executable change. Validation: `python3 bin/build.py --check` -> exit 0 (tokens resolve). `python3 bin/build.py --layout flat` -> exit 0; the built flat carries red-on-revert + Notebook-API-fidelity + Scan-patterns + SSRF (SKILL) + round-trip symmetry (reference.md).
- Tiger check (pre-mortem): plain `build.py` did NOT mutate the main workspace (dirty-file count 195 -> 195); it wrote only to the gitignored worktree dist/. The refreshed flat was copied by hand from that dist output.
- Gate 3/4 (docs/notebooks): N/A.

## Lead review

- **As tech lead:** this is refresh-not-delete, which is safe under both runtime models and matches the authorized plan. The stray-flat is a live deploy target here, so deleting it was rejected. The general 627-line skills/hostile-review/ twin is out of scope (D2, noted for separate review). Sibling project skills lacking repo-root flat dirs is a separate partial/stale-deploy observation, noted for follow-up, not fixed here.
- **As software engineer:** the splice was anchored on unique marker strings (not line numbers), and the result was verified against the flat to confirm a clean union with no dropped content. The migrated #1005 content was brought into rule-compliance (adverb reworded) rather than imported verbatim.
- Edited the projects/ SOURCE (authoritative) and regenerated the deployed flat from it. No AI/assistant attribution anywhere.

## Quantified claims

- **2 flat-only regions folded into source** (P6 + Scan-patterns block; Layer-3 items 7 & 8). Evidence: the pre-fold `diff` had exactly 3 hunks — 2 flat-only (now folded) + 1 source-only (P3, preserved).
- **source SKILL grew 165 -> 357 lines**; all 4 marker classes present. Evidence: grep counts (red-on-revert=1, Notebook-API-fidelity=1, Scan-patterns=1, SSRF=1) + reference.md round-trip=1.
- **0 content dropped**: post-fold `diff source flat` = only the P3 paragraph. Evidence: the diff output.
- **build --check exit 0**; **built flat carries all 5 markers**. Evidence: command outputs above.
- **3 files changed**: projects/ SKILL (spliced), flat SKILL (refreshed), flat reference.md (new). Evidence: `git status -s`.
