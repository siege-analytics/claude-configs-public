## Assumptions
Domain(s): agent workflow
Geospatial cross-cut: no
Goal source: operator instruction (branch cleanup, cherry-pick salvageable content)
Goal source verification: Manual — operator said "Adapt and merge what should be merged"
Pre-author-inventory: self-review/SKILL.md (1043 lines), ci-billing-failure-merge/SKILL.md (90 lines)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Two targeted additions to existing skill files. Investigation: (1) Verified self-review SKILL.md Lead section has 5 existing questions — new Q6 is additive. (2) Verified ci-billing-failure-merge SKILL.md lacks silver_canonical scope and standing delegation — both unique to the branch. (3) Confirmed inject-resolver evaluate-ticket wiring is already effectively landed via RESOLVER.md references.

## Trivial-pre-mortem declaration
Risk surface: two markdown skill files modified with additive content only. No hooks, scripts, or build artifacts changed. Self-review Q6 adds a new Lead review question — does not modify existing questions. CI-billing standing delegation adds a new section and scope entry — does not modify existing authorization logic. Failure mode: if additions are wrong, they provide bad guidance — reversible by removing the sections.

## Peer review

### Syntax check
Markdown: no syntax errors (standard GFM, no frontmatter changes).

### Test suite
Not applicable — instruction-only skills, no executable code.

### Build validation
No build changes.

### Shelf: conventions
Both additions follow existing skill conventions. Self-review Q6 uses the same "Lead asks" format as Q1-Q5. CI-billing standing delegation follows the existing conditional-tier pattern with explicit requirements.

## Lead review

### Phase A: Structural coherence
Self-review Q6 ("Does this change belong here?") is logically placed after Q5 (mechanical gates) — it's a higher-order architectural question that the Lead asks after verifying the Junior ran the mechanics. The library-surface trigger is relevant to siege_utilities' package structure concerns.

CI-billing standing delegation follows the existing per-merge approval pattern but adds time-bounded blanket approval. Requirements section explicitly states standing delegation does NOT waive any substitute-review criteria. Time-bounding and discovery sections prevent unbounded delegations.

### Phase B: Did this close the gap?
- [x] Self-review Q6 library-surface trigger extracted from feat/self-review-junior-lead-roles
- [x] silver_canonical conditional scope extracted from skill/ci-billing-failure-silver-canonical-scope
- [x] Standing delegation mechanism extracted from same branch
- [x] inject-resolver evaluate-ticket wiring confirmed already landed — skipped
- [x] Merge mechanics, reporting, and post-merge comment updated for standing delegation

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims
- "Q6 is additive" — verified: inserted after existing Q5, before Lead section format line. No existing content modified.
- "5 existing substitute-review criteria preserved" — verified: standing delegation section states "All five Substitute-review criteria" and "does NOT waive any of them."

## Evidence-predates-work
Artifact: plans/self-review-branch-cleanup.md
