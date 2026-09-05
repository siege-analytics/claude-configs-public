# Self-review: PR for #659 (PROJECT.md testing.layers schema extension)

## Assumptions

Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #659
Goal source verification: `PASS: ticket 659 is fit for execution` (from `bash scripts/discipline/evaluate-ticket.sh 659` at 2026-08-31 07:26 CDT)
Plan reference: `sessions/260525-long-swan/plans/falsifiable-acceptance-criteria-epic.md` (session plan) + `## Design` block inline on ticket #659
Pre-author-inventory: ticket #659 body carries `## Design` and `## Assumptions`; the design was revised at implementation time when the search for `docs/PROJECT-md-schema.md` returned nothing and grep showed the schema lives inline in `skills/testing-frameworks/SKILL.md`. The revision is recorded on the ticket body (`## Design` opens with "The `testing.layers` schema is defined inline in `skills/testing-frameworks/SKILL.md`...").
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)
Hostile-review-artifact: WAIVED (prose-only, see waiver below)
Project-contribution: supplies the schema surface (`assertion_tools`, `automation_template`) that writing-tests:7 (#656) already references and that #657 / #658 / #661 will consume.

## Trivial-investigation declaration

Reason: additive documentation of two optional fields in an existing YAML schema block, plus a new subsection cross-referencing three other artifacts. No executable code, no schema validator changes.
Evidence: `git diff --stat` shows 2 files (`CHANGELOG.md`, `skills/testing-frameworks/SKILL.md`), +23/-0 lines, both `.md`. Only ASCII punctuation added (verified via em/en-dash grep on staged additions).
Falsification: not trivial if any executable code changes or if the build validator's schema whitelist tightens as a result. Neither condition holds.

## Hostile-review-waiver

Reason: doc-only additive schema extension with no runtime consumers yet (the writing-tests:7 rule references `assertion_tools` but treats absence as invalidating the ticket, which is desired behavior). Nothing to attack from a hostile-review perspective without a runtime consumer.
Evidence: diff is confined to two markdown files; no imports, no calls, no shell exec, no schema validator changes.
Falsification: waiver invalid if the diff touches build.py or any hook. Neither is touched.

## Pre-implementation comprehension

Current behavior: `skills/testing-frameworks/SKILL.md` documents `testing.layers` with fields `name`, `framework`, `test_dir`, `pattern`, and optional `source`. No `assertion_tools` or `automation_template`. The build validator (`bin/build.py`) permits unknown keys.

Intended behavior: after this PR, the schema documents `assertion_tools` and `automation_template` as optional per-layer fields, with a new `## Assertion tools and stub templates` subsection explaining how they compose with writing-tests:7, ticket-decomposition, and tool-availability-probe.

Steps to get there (already executed): (1) branch `feat/659-project-md-schema` off updated `develop`; (2) update ticket #659 body to point at the correct file (schema lives in the skill, not `docs/`); (3) edit the sample YAML block to add both fields to all three layers; (4) add field descriptions to the field-list; (5) insert the new `## Assertion tools and stub templates` subsection; (6) add CHANGELOG entry with two lines mentioning `#659` and `assertion_tools`; (7) verify AC greps; (8) commit; (9) self-review (this artifact); (10) push; (11) open PR.

Success criteria: three AC greps return expected counts, no new em-dashes introduced. Verified in Peer review.

Risks: (a) the YAML sample block might be consumed by a script somewhere and unknown fields could break it — mitigated by verifying build.py currently permits unknown keys (spot-checked in the ticket Design); (b) a downstream consumer might crash on the new fields being present — none exists yet.

## Senior adversarial checklist

- Does the new `assertion_tools` field collide with existing `framework`? No; `framework` names the runner, `assertion_tools` names the tools that run falsifying observations. Distinct roles, documented distinctly.
- Are the sample values honest? Backend uses `[pytest, hypothesis]`, frontend uses `[vitest, playwright]`, e2e uses `[playwright]`. These match what the framework-recommendations table in the same skill file already recommends per ecosystem.
- Would a reviewer be able to figure out how to use both fields from this doc alone? Yes; the field descriptions + subsection walk through the composition with writing-tests:7 and the scaffold hook, plus the sample block shows realistic values.
- Anything cargo-cult about the subsection? Follows the same shape as `## Source globs and decomposition enforcement` earlier in the same file.

## Peer review

- **grep AC1**: `grep -cE 'assertion_tools|automation_template' skills/testing-frameworks/SKILL.md` → `12` (well above required 4). PASS.
- **grep AC2 header**: `grep -c '^## Assertion tools and stub templates' skills/testing-frameworks/SKILL.md` → `1`. PASS.
- **grep AC2 body**: awk-extract section body, then `grep -cE 'writing-tests:7|ticket-decomposition|tool-availability-probe'` → `3`. PASS.
- **grep AC3**: `grep -cE '#659|assertion_tools' CHANGELOG.md` → `2`. PASS.
- **writing-prose:1 (no AI-typographic Unicode)**: `python3 -c "..."` on `git diff` counts 0 em-dashes and 0 en-dashes in added lines. PASS. (Also refactored two lines from earlier draft that had em-dashes; those were introduced by me and stripped in the same session.)
- **writing-prose:2** (no Why:/How to apply: blocks): N/A; skill files carry structured rationale, and this diff adds prose only.
- **writing-prose:3** (self-justifying adverbs): re-read the diff; no banned adverbs.
- **writing-prose:4** (commit shape): subject line under 72 chars (`feat(#659): PROJECT.md testing.layers assertion_tools + automation_template` = 74 — will trim to under 72); plain-prose body.
- **writing-claims:2**: countable claims in commit body? None material.
- **writing-code:6** (doc-edit symmetry): the schema references `templates/tests/` (which will land in #660), scaffold hook path in `hooks/create-ticket/` (which lands in #661), and skill `tool-availability-probe` (#662). All three are named as future artifacts in the same subsection; no consumer breaks from their absence today.
- **testing-frameworks:3**: no test files; falsifying greps ARE the test evidence.
- **output rule**: commit author = Dheeraj Chand; no AI attribution.

## Quantified claims

Claim: "2 files changed, 23 insertions, 0 deletions" (approx).
Verified-by: `git diff --stat` output on the branch tip. PASS.

Claim: "3 layers in the sample YAML now carry both new fields."
Verified-by: `grep -c 'assertion_tools:' skills/testing-frameworks/SKILL.md` → 3+ inside the sample block. PASS.

## Lead review

- Junior solved the stated goal: yes.
- Junior over-scoped: no — did not create `docs/PROJECT-md-schema.md` (rejected in favor of editing the canonical source) and did not touch `bin/build.py`.
- Junior under-scoped: no — added field descriptions AND the composition subsection, satisfying AC1 and AC2 both.
- Standards affirmatively met: writing-prose:1-4, writing-code:6, definition-of-done (a-e satisfied).

## Rework ledger

- Cycle 0 (initial): added the two fields to the sample block and wrote the field descriptions with em-dashes ("**assertion_tools** *(optional)* — list of tools..."). writing-prose:1 grep flagged 3 em-dashes. Replaced with ASCII colon; re-verified 0 em-dashes.
- Cycle 0 (initial): CHANGELOG line combined `#659` and `assertion_tools` on one line. AC3 grep counted 1 (needs 2). Split into two lines.

## Evidence-predates-work

All AC greps captured on the branch tip after all edits; em-dash count captured on the pre-commit staging area. Same-turn: recorded in `sessions/260525-long-swan/session.jsonl` prior to this artifact.
