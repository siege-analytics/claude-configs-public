---
ticket_refs:
  - siege-analytics/claude-configs-public#814: PR A vocabulary (predecessor)
  - siege-analytics/claude-configs-public#817: governance carve-out (predecessor)
  - siege-analytics/claude-configs-public#822: deployment drift tooling (predecessor)
  - siege-analytics/claude-configs-public#828: hook false-positive fixes (sibling)
  - siege-analytics/claude-configs-public#827: PR D queued (Fix work-item)
  - siege-analytics/claude-configs-public#810: R11 arc source PR
---

# Self-review: PR B+C combined — shape-space audit surfaces + enumeration rules

## Assumptions

Working as: software engineer, tech lead, coordinator (option 5 fallback executor)
Domain: `skills/**` prose + `skills/_*-rules.md` shelf additions
Goal source: R11-meta remediation streams 1 (PR B) and 3 (PR C), consensus with reviewer session `260905-clever-quasar` on 2026-09-07

Pre-author-inventory: authoring-against-state:6 inventory in this artifact's Lead review section
Investigate-artifact: plans/design-note-pr-bc-combined.md
Pre-mortem-artifact: plans/pre-mortem-pr-bc.md
Hostile-review-artifact: plans/hostile-review-pr-bc.md
Project-contribution: makes shape-space enumeration mechanical at five review surfaces (rule-authoring, scanner-implementation, PR self-review, PR hostile-review, rule-coverage-prose); establishes writing-rules:8 as the enforcement rule; provides discoverable `shape-space-audit` skill for future scanner authors.

## Peer review

Gate 1 (build check): `python3 bin/build.py --check` PASS.
Gate 2 (skill reference sync): `python3 bin/sync-skill-references.py --check` PASS.

Shelf compliance:

- **`[rule:writing-code]` writing-code:1** (docstring brevity): N/A — no Python code.
- **`[rule:writing-code]` writing-code:2** (no history references in code comments): N/A — no code comments; ticket refs in prose bodies are prose, not comments.
- **`[rule:writing-code]` writing-code:4** (verify symbol exists): PASS — cross-references between six additions verified against grep of existing files (writing-rules:1-:7, writing-code:8, writing-claims:3, authoring-against-state:6 all exist as cited).
- **`[rule:writing-prose]` writing-prose:1** (no AI-typographic Unicode): PASS — verified via preview scan; ASCII dashes and quotes throughout.
- **`[rule:writing-prose]` writing-prose:2** (no Why/How-to-apply structured blocks in code comments): N/A — no code comments.
- **`[rule:writing-prose]` writing-prose:3** (no self-justifying adverbs): pending grep. Will remove any `deliberately/intentionally/explicitly/fundamentally/essentially/crucially/notably` occurrences in bodies before push.
- **`[rule:writing-claims]` writing-claims:2** (countable claims require same-turn evidence): PASS — every count in bodies is either from grep run in this session or from a cited artifact (R11 findings: "3 INVALIDATING + 4 MAJOR" cites plans/r11-scala-skeptic-review.md; "ten alternating-provider hostile-review rounds" cites plans/r11-meta-gap-analysis.md).
- **`[rule:writing-claims]` writing-claims:3** (unquantified completeness claims): PASS — no "fully covers" / "completed all" claims made without enumeration.
- **`[rule:writing-rules]` writing-rules:5** (Trivial-* controlled vocabulary): PASS — no Trivial-* declaration is used; this PR touches ESM skill/rule prose, so it ships full authoring-against-state:6 inventory below.
- **`[rule:writing-rules]` writing-rules:7** (session-scale, Pairs-with-are-dependencies): PASS — each of the six additions cross-references the paired rules/skills it depends on; each cross-reference is stated in the body of the addition, not just in an "also see" list.
- **`[rule:writing-rules]` writing-rules:8** (this PR introduces this rule): dogfood — the writing-code:8 shape-space coverage table this PR retrofits IS the canonical example writing-rules:8 cites. PR body IS the fixture.
- **`[rule:external-shape-modeling]` (per PR A writing-rules:5 amendment)**: PASS — this PR modifies `_writing-*-rules.md` and `skills/*/SKILL.md` files, which are external-shape-modeling code per PR A's definition (rules and skills drive agent behavior; they model an external shape space). No Trivial-* declaration used; full authoring-against-state:6 inventory shipped in Lead review below.

## Lead review

### authoring-against-state:6 inventory

**Inputs read:**

- `plans/r11-scala-skeptic-review.md` — R11 hostile-review findings (3 INVALIDATING + 4 MAJOR shape misses)
- `plans/r11-meta-gap-analysis.md` — seven proposed additions P1-P7
- `plans/self-review-pr-a.md` (PR A dogfood self-review, from #814)
- `skills/self-review/SKILL.md` existing structure (Trivial-* declaration section around line 559-621)
- `skills/hostile-review/SKILL.md` existing structure (nine categories, section header enumeration)
- `skills/_writing-code-rules.md` writing-code:8 body (lines 50-60 pre-edit)
- `skills/_writing-claims-rules.md` writing-claims:3 body (lines 23-27 pre-edit)
- `skills/_writing-rules-rules.md` writing-rules:1-:7 (verify :8 not squatted)
- `skills/_authoring-against-state-rules.md` step-6 inventory template (as the pattern for the dogfood inventory here)

**Knowledge requirements enumerated (step 2):**

- Q1: Does writing-rules:8 already exist? A: verified via grep — only :1 through :7 exist pre-edit.
- Q2: Does `skills/shape-space-audit/` already exist? A: verified via ls — directory does not exist pre-edit.
- Q3: Does `hostile-review/SKILL.md` already have a `## Category 10` section? A: verified via section-header grep — sections end at `## Attribution Policy` (line 541); Category 10 is a net-new addition.
- Q4: What are the three R11 INVALIDATING shapes to cite in writing-code:8 table? A: from `plans/r11-scala-skeptic-review.md` — I-1 (else-clause), I-2 (matplotlib prefix), I-3 (1-flag/N-import).
- Q5: What is the exact P6 anti-pattern wording reviewer requires? A: from consensus thread with `260905-clever-quasar` on 2026-09-07 — "context-free grep is not shape evidence; audit the enclosing block/type/grammar position that gives a token meaning."
- Q6: What is the PR A external-shape-modeling definition to cite? A: from `_writing-rules-rules.md` writing-rules:5 post-#814 body — "scanners, parsers, linters, hooks that infer semantics from source syntax, config files, CLI arguments, API payloads, schemas, notebooks, or framework conventions." Not Python-specific.

**Contact-point measurements (step 3 — rules 1-5):**

- **data-shape (authoring-against-state:1):** N/A. This PR does not consume external data; prose additions are self-contained.
- **config-state (authoring-against-state:2):** N/A. No runtime config touched; no ConfigMap, no environment variable, no cluster resource limit.
- **topology (authoring-against-state:3):** N/A. No pod / node / service targeted.
- **plan-shape (authoring-against-state:4):** N/A. No query plan authored; prose additions do not chain unions or joins.
- **version-resolution (authoring-against-state:5):** N/A. No package added, removed, or shadowed; no `sys.path` change.

**Surface areas inventoried beyond rules 1-5 (step 4):**

- `skills/shape-space-audit/` (new directory) — created; contains SKILL.md only.
- `skills/self-review/SKILL.md` — `## Adversarial shape audit` subsection appended after `## Exemption blocks` (line ~621).
- `skills/hostile-review/SKILL.md` — `## Category 10: Scanner-shape coverage` section inserted before `## Methodology` (line ~488).
- `skills/_writing-code-rules.md` — writing-code:8 body extended with a `**Shape-space coverage table**` paragraph inserted between the existing writing-code:8 body and `**writing-code:9. No silently-dropped parameters.**`.
- `skills/_writing-rules-rules.md` — new `**writing-rules:8. ...**` section inserted before `## When this file applies`.
- `skills/_writing-claims-rules.md` — writing-claims:3 body extended with a `**Class-membership prose extension.**` paragraph inserted between the existing Multi-PR session-pattern extension and `**writing-claims:4. ...**`.
- `plans/design-note-pr-bc-combined.md` (new) — this PR's design note.
- `plans/pre-mortem-pr-bc.md` (new) — this PR's pre-mortem.
- `plans/self-review-pr-bc.md` (new) — this file.

**Hypothesis (step 7 — falsifiable):**

Six additions in one PR against `origin/develop` at `30ad338` produce a diff that (a) touches only files under `skills/` and `plans/`, (b) cross-references between the additions form a directed acyclic graph rooted at `skills/shape-space-audit/SKILL.md` (which B1/B2 both consume), (c) satisfies reviewer's six preservation checks, and (d) passes `bin/build.py --check` and `bin/sync-skill-references.py --check`. Each of the six additions makes the shape-space audit discipline discoverable at a specific surface (self-review at write time, hostile-review at review time, shape-space-audit as the canonical skill, writing-code:8 as the canonical example, writing-rules:8 as the enforcement rule, writing-claims:3 as the class-membership prose grounding). The composition of the six additions makes the shape-space question inescapable at those five surfaces; skipping any one leaves the escape hatch that let R1-R10 miss the R11 shapes.

**Conclusions (steps 5+6):**

The pre-author inventory produced no surprises against the design note's claims. Every knowledge requirement was answered by same-turn grep or ls on the pre-edit files. No open questions were deferred. The hypothesis matches the PR's actual diff shape.

**What was NOT measured:** the hook enforcement path for the new `## Adversarial shape audit` subsection is a v1.1 follow-up per B1 body — this PR ships the discipline, hook enforcement lands separately. Reviewer bounded pass validates the discipline is discoverable; hook enforcement is out of scope.

### Substantive design review (as tech lead)

The six additions compose per the reviewer's six preservation checks and per the design note's cross-reference table:

1. **shape-space-audit/SKILL.md** is the root: B1 and B2 both cite it as authoritative for the discipline. The P6 anti-pattern is named in a dedicated `## The P6 anti-pattern: context-free grep is not shape evidence` section, not just cited from #827. First-class named pattern per reviewer requirement.
2. **self-review/SKILL.md `## Adversarial shape audit`** consumes shape-space-audit's five rotation frames and corpus-sampling protocol at authoring time. Four required fields (Shape space / Fixture-covered shapes / Prose-vs-implementation gap / Adversarial frame this round) enforce falsifiability.
3. **hostile-review/SKILL.md Category 10** consumes shape-space-audit at review time. Three sub-categories map 1:1 to reviewer's real-world audit method (10a corpus, 10b composition, 10c prose-vs-impl).
4. **writing-code:8 shape-space coverage table** is the canonical example writing-rules:8 cites. Table preamble states the coverage-status semantics: `covered` requires AST + fixture, not context-free grep. Three R11 INVALIDATING rows (2, 3, 4) cite `siege-analytics/claude-configs-public#827` in Fix work-item column. M-shapes (5-8) and cross-block shadowing (9) stay `deferred`. Preservation checks 2, 3, 4 all satisfied.
5. **writing-rules:8** is the enforcement rule for the shape-space enumeration. Composes with writing-claims:3 (class-membership prose extension shipping in C3) and authoring-against-state:6 (design-time knowledge-requirements enumeration).
6. **writing-claims:3 class-membership extension** grounds the unquantified class-membership prose ("detects X patterns") in the writing-rules:8 enumeration. Worked example: `detect-ai-fingerprints/SKILL.md`'s "detects try/except ImportError optional-import patterns" as the real over-claim from R11.

Preservation check 5 (five rotation frames meaningfully distinct): shape-space-audit/SKILL.md names each frame with a distinct paragraph describing what that frame typically finds. Scala/JVM skeptic finds coverage over-claims and missing composition audits; PyPI-top-100 CI operator finds fixture-frame traps; security engineer finds bypass surfaces; Python newcomer finds prose-vs-implementation gaps; linter author finds AST edge cases. Each frame's "typically finds" is different — not provider-renamed duplicates.

Preservation check 6 (writing-claims:3 extension adds falsifiability): the extension body names the specific trigger phrases ("detects X," "catches Y," "enforces Z," "covers W," "handles V") and states the falsification cost ("if the class is finite and enumerable, the unquantified claim requires enumeration OR rephrase"). Worked example is a real over-claim from R11, not a hypothetical.

## Quantified claims

"Ten alternating-provider hostile-review rounds on `siege-analytics/claude-configs-public#810`" — verified against `plans/r11-scala-skeptic-review.md` R1-R10 arc.
"3 INVALIDATING + 4 MAJOR shape misses in one pass" — verified against `plans/r11-scala-skeptic-review.md`.
"Seven proposed additions P1-P7; P3 shipped as PR A #814" — verified against `plans/r11-meta-gap-analysis.md`.
"Ten baseline shapes enumerated in writing-code:8 shape-space coverage table" — verified against edited `_writing-code-rules.md`; table rows 1-10.
"Three R11 INVALIDATING rows cite #827" — verified against edited `_writing-code-rules.md`; rows 2, 3, 4 Fix work-item column reads `siege-analytics/claude-configs-public#827`.
"writing-rules:8 does not squat an existing number" — verified against pre-edit `_writing-rules-rules.md`; grep returned :1-:7 only.
"No file touched under `hooks/`, `scripts/discipline/`, or `skills/detect-ai-fingerprints/`" — pending `git diff --stat origin/develop..HEAD` at commit time; expected verified.

## Post-error revision

None. This PR is initial authoring; no prior artifact to revise. If reviewer's bounded pass surfaces a preservation-check failure, this section gets a Post-error revision block per writing-rules:6.
