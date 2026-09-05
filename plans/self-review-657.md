# Self-review: PR for #657 (create-ticket skill: Falsifiable-by + tool render)

## Assumptions

Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #657
Goal source verification: `PASS: ticket 657 is fit for execution` (from `bash scripts/discipline/evaluate-ticket.sh 657` at 2026-08-31 07:47 CDT)
Plan reference: `sessions/260525-long-swan/plans/falsifiable-acceptance-criteria-epic.md` + `## Design` on ticket #657
Pre-author-inventory: ticket #657 carries `## Design` + `## Assumptions`. Verified `skills/create-ticket/SKILL.md` had 223 lines pre-edit; AC block existed at lines 130-133; Full-example AC block existed at lines 192-195. No prior mention of `Falsifiable-by`, `assertion_tools`, or `tool-availability-probe`.
Investigate-artifact: TRIVIAL (see declaration)
Pre-mortem-artifact: TRIVIAL (see declaration)
Hostile-review-artifact: WAIVED (see waiver)
Project-contribution: makes the create-ticket skill produce rule-compliant tickets by default; without this, every consumer manually re-implements writing-tests:7's shape.

## Trivial-investigation declaration

Reason: prose-only edits to a single skill file + CHANGELOG entry. No executable code, no schema validation changes.
Evidence: `git diff --stat` shows 3 files (`CHANGELOG.md`, `plans/self-review-657.md`, `skills/create-ticket/SKILL.md`), additive only.
Falsification: not trivial if the AC-template change breaks any downstream consumer that parses the specific bullet format. `grep -rn 'Criterion 1\|Criterion 2' scripts hooks bin` returns no hits outside the skill file itself; no automated parser depends on the old shape.

## Hostile-review-waiver

Reason: prose additions to a documentation skill; no runtime behavior. The layer-tool table names artifacts (`.tmpl` templates and `.sh` probes) whose existence is verified by adjacent PRs (#660 landed via PR #667; #662 via PR #668). Any hostile-review path here would target the ticket-body-shape drift, which is the intended behavior change.
Evidence: no code changes; no imports; no exec.
Falsification: waiver invalid if the skill file has code fences with executable content. Verified — only markdown code fences are yaml/markdown/bash examples, no `!#/bin/bash` shebang that a hook would execute.

## Pre-implementation comprehension

Current behavior: `skills/create-ticket/SKILL.md` produces tickets whose ACs are prose checklists (`- [ ] Criterion 1`). Reviewers must infer how to check each AC; when they infer wrong, close-time evidence is ad-hoc.

Intended behavior: after this PR, the skill's AC template requires a `Falsifiable-by:` observation and `Tool:` name per AC. The new `## Falsifiable acceptance criteria` section documents the layer-tool table + probe invocation pattern + multi-layer handling + schema-gap surfacing. The Full-example section shows a paired AC end-to-end.

Steps executed: branch → update ticket #657 body → edit AC template block → add new section after QA/Verification → update Full-example AC block → CHANGELOG entry → verify five ACs → self-review → push → PR.

Success criteria: all five ACs pass (`Falsifiable-by:` + `Tool:` labels present >= 4 times; six probe scripts named in layer-tool table; `tool-availability-probe` referenced; Full-example section has Falsifiable-by >= 2; CHANGELOG has 2 matching lines). Verified.

Risks: (a) the new AC section could bloat the skill file past readable — mitigated by keeping the section tight (single table + three short paragraphs); (b) the layer-tool table could rot if template/probe filenames change — mitigated by locking to the same paths already in `templates/tests/README.md` and `skills/tool-availability-probe/SKILL.md`.

## Senior adversarial checklist

- Does the new AC template make writing simple tickets more painful? Modestly yes — a bugfix now takes 3 lines per AC instead of 1. Justified by the falsifiable-AC discipline being the whole point of epic #655.
- Are the layer-tool paths absolute or relative? Relative to repo root, matching how templates/tests/README.md and skills/tool-availability-probe/SKILL.md name them.
- Does the "surface the schema gap" instruction (add PROJECT.md sub-ticket first, then Blocked-by) risk cascading tickets? Yes — but that's the correct behavior. A layer without declared `assertion_tools` cannot support falsifiable-AC tickets; forcing the schema fix first is the point.
- Does the Full-example bugfix ticket AC block still make sense given the new format? Yes — each AC has a Falsifiable-by that names a runnable SQL/pytest command and a Tool from the appropriate layer.
- Are we naming pytest for a layer whose real project might not have pytest? Sample values only; the skill instructs authors to draw from the touched layer's own PROJECT.md, not from the sample.

## Peer review

- **grep AC1**: `grep -cE 'Falsifiable-by:|Tool:' skills/create-ticket/SKILL.md` -> 11 (>= 4). PASS.
- **grep AC2**: `grep -cE 'pytest.sh|playwright.sh|vitest.sh|schemathesis.sh|great-expectations.sh|k6.sh' skills/create-ticket/SKILL.md` -> 7 (>= 6). PASS. (Extra hit is because `scripts/probe/pytest.sh` is named twice in the layer-tool table — once for `backend`, once for `backend/integration`.)
- **grep AC3**: `grep -c 'tool-availability-probe' skills/create-ticket/SKILL.md` -> 1. PASS.
- **grep AC4**: awk-extract Full-example section, `grep -c Falsifiable-by:` -> 3 (>= 2 required). PASS.
- **grep AC5**: `grep -cE '#657|create-ticket' CHANGELOG.md` -> 2. PASS.
- **writing-prose:1**: 0 em-dashes / en-dashes in added lines. PASS.
- **writing-prose:2** (Why:/How to apply:): none.
- **writing-prose:3** (self-justifying adverbs): re-read; none.
- **writing-prose:4** (commit shape): subject under 72 chars, plain-prose body.
- **writing-code:2** (no history refs in code comments): the SKILL.md references `#655/#656/#657/#659/#660/#661/#662` — architectural cross-refs to companion epic tickets. Same judgment as prior PRs in this epic.
- **testing-frameworks:3**: no test files; grep ACs ARE the test evidence.
- **output rule**: no AI attribution.

## Quantified claims

Claim: "AC template gains Falsifiable-by + Tool sub-items per AC."
Verified-by: grep count of the two labels in the skill = 11, up from 0 pre-edit.

Claim: "Layer-tool table names all seven templates and their probes."
Verified-by: the six unique probe scripts + backend/integration reuse = 7 total occurrences.

Claim: "Full-example bugfix demonstrates three falsifiable ACs."
Verified-by: awk-extract of the Full-example section counted 3 Falsifiable-by clauses.

## Lead review

- Junior solved the stated goal: yes.
- Junior over-scoped: no — did not auto-generate stubs (that's #661) and did not update the ticket-decomposition skill (that's #658).
- Junior under-scoped: no — added the schema-gap-surfacing instruction (add PROJECT.md sub-ticket first) which is the load-bearing behavior for a layer with no `assertion_tools` yet.
- Standards affirmatively met: writing-prose:1-4, writing-code:2, definition-of-done (a-e).

## Rework ledger

- Cycle 0: no rework — all five ACs green on first grep pass.

## Evidence-predates-work

All AC greps captured on the working tree pre-commit.
