---
ticket_refs:
  - siege-analytics/claude-configs-public#814: PR A landed; referenced as vocabulary predecessor
  - siege-analytics/claude-configs-public#817: PR governance carve-out; referenced as deployment predecessor
  - siege-analytics/claude-configs-public#822: PR deployment drift tooling; referenced as sync path
  - siege-analytics/claude-configs-public#828: PR self-review hook false-positive fixes; referenced as sibling
  - siege-analytics/claude-configs-public#827: PR D queued; referenced as Fix work-item for I1/I2/I3 rows
  - siege-analytics/claude-configs-public#810: R11 arc source PR; referenced as recurrence evidence
---

# Design note — PR B+C combined: shape-space audit surfaces + enumeration rules

## Ticket-shape

R11-meta remediation streams 1 (PR B, review-surface additions) and 3 (PR C, rule/table additions) combined into one PR. Executed from coordinator session `260525-long-swan` after three impl-session spawn cycles orphaned on `claude-max` with `status: todo, isActive: true, LLM never fired`:

- `260907-first-flow` (Opus 4.7, PR B original spawn) — orphaned
- `260907-early-raven` (Opus 4.7, PR B respawn) — orphaned
- `260907-quiet-mountain` (Sonnet 4.6, combined B+C spawn) — orphaned
- `260907-fine-cascade` (Opus 4.7, PR C original spawn) — orphaned
- `260907-true-torrent` (Opus 4.7, PR C respawn) — orphaned

Operator directive at 2026-09-07 22:16 CDT: option 2 (Sonnet retry) + option 4 (combined session), with option 5 (execute in coordinator session) as 5-minute fallback. Sonnet orphaned within the deadline; option 5 triggered. Reviewer session `260905-clever-quasar` (Siege Skills Revision) created the feature branch and a worktree at `/Users/dheerajchand/git/siege-analytics/claude-configs-public.wt-pr-bc` to unblock the coordinator's Write path around workspace-scoped mutation-gate friction.

## Diagnosis (from R11-meta gap analysis + consensus with 260905-clever-quasar)

Ten rounds of alternating-provider hostile review on `skills/detect-ai-fingerprints/` converged on GREEN. R11 (Scala-skeptic frame) found 3 INVALIDATING + 4 MAJOR shape misses in one pass. Meta-gap analysis (`plans/r11-meta-gap-analysis.md`) identified seven proposed additions (P1-P7):

- **P3** shipped as PR A (siege-analytics/claude-configs-public#814): vocabulary hardening + external-shape-modeling never-trivial.
- **P1, P2, P4, P5, P6, P7** ship in this PR (combined B+C).

The through-line: provider alternation without frame alternation converges on shared fixture set as ground truth. This PR makes frame alternation a required discipline (B1/B2/B3), requires rules that name idiom classes to enumerate their covered shape space (C1/C2/C3), and makes the enforcement mechanical at the review boundary (C1 table semantics: `covered` requires AST + fixture, not context-free grep).

## Six additions

### PR B content — review-surface additions

**B1. `skills/self-review/SKILL.md` — new `## Adversarial shape audit` subsection.** Required when the diff modifies external-shape-modeling code per PR A's writing-rules:5 definition. Four required fields, each requiring same-turn evidence: Shape space, Fixture-covered shapes, Prose-vs-implementation gap, Adversarial frame this round.

**B2. `skills/hostile-review/SKILL.md` — new `## Category 10: Scanner-shape coverage`.** Three sub-categories: 10a corpus sample audit (adversarial inputs from real-world code, not fixture set); 10b detector composition audit (guards masking sibling findings; R9-F3 named counter-example); 10c prose-vs-implementation audit (grep SKILL.md coverage claims, verify each has code + fixture).

**B3. New skill `skills/shape-space-audit/SKILL.md`.** Purpose, when-it-applies, five rotation frames (Scala/JVM skeptic / PyPI-top-100 CI operator / security engineer / Python newcomer / linter author), corpus sampling protocol including the P6 anti-pattern named prominently as a first-class named pattern: "context-free grep is not shape evidence; audit the enclosing block/type/grammar position that gives a token meaning."

### PR C content — rule/table additions

**C1. Retrofit `_writing-code-rules.md` writing-code:8 with a shape-space coverage table.** Ten baseline shapes. The three R11 INVALIDATING rows (I1/I2/I3 — else-clause, matplotlib prefix, 1-flag/N-import) cite `siege-analytics/claude-configs-public#827` in Fix work-item column. Four MAJOR shapes (M1-M4) and one edge case stay `deferred`. Coverage-status semantics stated in table preamble: `covered` requires AST + fixture, not context-free grep.

**C2. New `writing-rules:8`.** Rules that describe a class of code idioms must enumerate the covered shape space. Composition rules with writing-claims:3 and authoring-against-state:6. Canonical example: writing-code:8's shape table (retrofit in this PR).

**C3. Extend `writing-claims:3` — class-membership prose extension.** Not a new rule number; extension to existing body. Class-membership prose is subject to writing-claims:3 when the class is implicitly finite. Worked example: `detect-ai-fingerprints/SKILL.md`'s "detects try/except ImportError optional-import patterns" as a real over-claim from R11's findings.

## What this PR does NOT do

- No changes to `skills/detect-ai-fingerprints/` scanner code (PR D / #827).
- No new hooks or hook edits (Stream 4 hook fixes already shipped in #828).
- No modifications to `_authoring-against-state-rules.md` other than cross-reference update if warranted.
- No R5-R10 self-review artifact modifications.

## Reviewer's six preservation checks (from 260905-clever-quasar consensus)

1. P6 anti-pattern named prominently in `shape-space-audit/SKILL.md` — first-class named pattern, not merely cited from #827.
2. `writing-code:8` table preamble states coverage-status semantics: `covered` requires AST + fixture, not context-free grep.
3. I1/I2/I3 rows cite `#827` in Fix work-item column.
4. M-shapes remain `deferred` — not falsely claimed covered.
5. Five rotation frames meaningfully distinct (not provider-renamed duplicates).
6. `writing-claims:3` extension adds falsifiability, not stronger rhetoric.

## Rollback

Single revert of the merge commit. Six additions become unavailable; meta-governance layer regresses one step. PR D can no longer cite `writing-code:8` shape table as spec. Content recoverable from this design note.

## Success criteria (falsifiable)

- Six additions present and cross-referenced correctly at merge time.
- `bash bin/build.py --check` PASS.
- `python3 bin/sync-skill-references.py --check` PASS.
- Reviewer bounded pass validates all six preservation checks.
- No file touched under `hooks/`, `scripts/discipline/`, or `skills/detect-ai-fingerprints/`.
- `plans/self-review-pr-bc.md` contains no Trivial-* declaration and ships full authoring-against-state:6 inventory.

## Verification of preconditions

- `origin/develop` at `30ad338` (post-#828 squash merge, verified).
- `origin/main` at `ab4e73f` (verified).
- No writing-rules:8 in the pre-edit `_writing-rules-rules.md` (verified via grep; rules :1 through :7 present).
- No existing `skills/shape-space-audit/` directory (verified before Write).
- No existing `## Category 10` section in `skills/hostile-review/SKILL.md` (verified via section-header grep; sections went up to `## Attribution Policy` at line 541).

### Verified Shapes

**S1** ATTESTED: PR touches six files across `skills/` (three edits + one new + two rule edits) plus artifact chain in `plans/`. No hook or scanner file touched.
**S2** ATTESTED: `shape-space-audit/SKILL.md` names the P6 anti-pattern as a first-class named pattern in a dedicated `## The P6 anti-pattern` section, not just cited from #827.
**S3** ATTESTED: `_writing-code-rules.md` writing-code:8 shape table preamble states coverage-status semantics: `covered` requires AST + fixture, not context-free grep.
**S4** ATTESTED: Table rows 2, 3, 4 (I1/I2/I3) cite `siege-analytics/claude-configs-public#827` in Fix work-item column.
**S5** ATTESTED: Table rows 5-9 (M1-M4 + cross-block shadowing) remain `deferred` in Fix work-item — no false coverage claim.

### Tiger 1

**Severity:** MEDIUM
**Likelihood:** medium
**Trigger:** self-review dogfood accidentally uses Trivial-* declaration despite PR touching ESM code. PR A's own enforcement (#814) blocks merge until fixed.
**Mitigation:** self-review artifact template pre-planned as full authoring-against-state:6 inventory; no Trivial-* section drafted.
**Fallback:** if merge blocks, amend self-review and re-push.

### Tiger 2

**Severity:** LOW
**Likelihood:** low
**Trigger:** cross-references between six additions reference wrong file paths or rule numbers.
**Mitigation:** verified writing-rules numbering (only :1-:7 pre-edit); dependency-ordered writes (shape-space-audit first since B1/B2 reference it).
**Fallback:** amend commit with corrected cross-references.
