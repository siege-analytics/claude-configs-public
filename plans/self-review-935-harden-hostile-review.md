# Self-review — harden hostile-review (CCP#935)

## Assumptions

Working as: tech lead, software engineer
Goal source: #935
Pre-author-inventory: #935 — verified the authoring source is projects/siege-utilities/skills/hostile-review/ (per RESOLVER + bin/build.py walk); confirmed red-on-revert exists author-side (writing-tests:1, RESOLVER bug-fix row) but not as a reviewer close standard; confirmed round-trip is a property-testing technique (_property-testing-rules.md) but not a hostile-review checklist item.
Investigate-artifact: #935
Pre-mortem-artifact: #935
Project-contribution: Raises the hostile-review bar the release-hardening effort depends on — reviewers now reproduce red-on-revert themselves (the step that surfaced #1338 from #1337) and scan converter pairs for the write-preserves/read-drops asymmetry (#1336), so a second adjacent defect is less likely to survive a review round.

Key assumptions:
- Both changes are prose additions to review guidance; no executable code changes.
- Edits go in the projects/ source, not the skills/ build artifact.

## Peer review

- **writing-prose:1 (no AI typography).** Added lines use ASCII `--`, no em/en-dashes. Evidence: `git diff | grep '^+' | grep -nE 'em/en-dash|adverbs'` -> empty (clean).
- **writing-tests:1 (red on revert).** The P3 addition operationalizes writing-tests:1 on the reviewer side: a fix whose test does not go red on revert is testing the mock; the text makes the reviewer run it rather than trust the assertion.
- **writing-rules:8 (shape-space).** P4 enumerates the converter-pair shape space it covers (to_X/from_X, serialize/deserialize, write/read, encode/decode) rather than naming one instance.
- Gate 1 (syntax): N/A -- markdown-only, no .py/.sh.
- Gate 2 (tests): N/A -- no executable change. Validation: `python3 bin/build.py --check` -> exit 0 (tokens resolve).
- Gate 3 (docs sphinx): N/A -- not a docs/ sphinx source.
- Gate 4 (notebooks): N/A.

## Lead review

- **As tech lead:** both additions sharpen the existing review standard without changing enforcement mechanics; LOW blast radius (prose in one skill). Edited the source; did not touch the build artifact.
- **As software engineer:** the P4 check cites the mechanical complement (round-trip property test) so the reviewer item and the test discipline reinforce rather than duplicate.
- Surfaced a pre-existing, out-of-scope divergence (the committed skills/ artifact carries ~170 lines absent from source) in the ticket and PR for the maintainer to reconcile; did not attempt to fix it here.
- No AI/assistant attribution in any deliverable.

## Quantified claims

- **2 edits across 2 files** (SKILL.md Verdicts, reference.md Composition seam checks). Evidence: `git diff --cached --name-only` lists exactly those two plus this artifact.
- **0 em-dashes / banned adverbs in added lines.** Evidence: the grep above returned empty.
- **build.py --check exit 0** (no broken token references introduced). Evidence: command exit code.
