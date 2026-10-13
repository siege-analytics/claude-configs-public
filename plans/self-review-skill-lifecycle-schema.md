# Self-review: skill lifecycle schema and migration gate

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: User-approved Skill Library Simplification Plan, Phase 1.
Goal source verification: Phase 0 catalog merged in #953 with 198 authoritative items, 194 unknown owners, and 198 unknown lifecycle states; Phase 1 calls for validated metadata with a temporary legacy allowlist reduced to zero over later PRs.
Plan reference: `catalog/skills-inventory.json` and approved `skill-library-simplification.md`.
Pre-author-inventory: Phase 0 schema, project owner inheritance, existing skill YAML frontmatter, rules without frontmatter, and hosted CI freshness steps.
Investigate-artifact: `catalog/skills-inventory.json` diagnostics.
Pre-mortem-artifact: this document, Risks section.
Hostile-review-artifact: four independent hostile-review rounds completed before push; findings and fixes are recorded below.
Project-contribution: prevents future undocumented skill/rule growth while allowing existing sources to migrate without a risky 198-file rewrite.

## Pre-implementation comprehension
Current behavior: catalog exposes lifecycle/ownership gaps but does not block new unowned or unclassified items.
Intended behavior: every authoritative source is either metadata-complete or explicitly listed in a checked legacy allowlist; new undocumented items fail CI; fixed items must leave the allowlist.
Steps: define machine-readable lifecycle schema; validate source frontmatter/project inheritance; generate an exact legacy allowlist from current gaps; add stale/unknown allowlist detection; add fixtures and CI.
Success criteria: exact 198-item coverage, no wildcard exemptions, new undocumented source fails, metadata-complete source passes, stale allowlist row fails, project owner inheritance works, and runtime loading remains unchanged.

## Risks
1. A wildcard allowlist would permanently disable the gate. Use exact canonical source paths only.
2. Generated copies could be allowlisted instead of sources. Validate against inventory canonical sources.
3. Project overlays could be forced to duplicate owner metadata. Permit owner inheritance from PROJECT.md.
4. Rules currently lack frontmatter. Allowlist them initially; do not invent metadata in this PR.
5. Adding metadata fields can be mistaken for activation semantics. This PR validates governance only; runtime routing remains unchanged.

## Senior adversarial checklist
The gate must fail closed for new sources, reject unknown paths and stale exemptions, preserve project override semantics, and avoid coupling lifecycle state to deployment before progressive loading exists.

## Peer review
Four hostile-review rounds challenged regeneratable allowlists, inheritance scope, schema divergence, unsafe paths, mutable bootstrap membership, completed-item regression, missing base history, and expansion of existing gap sets. Every S1/S2 finding was reproduced conceptually and fixed before commit.

## Lead review
Approach fit: a SHA-256-pinned 198-path bootstrap, explicit post-baseline approval registry, append-only completed-migration registry, and protected-base gap comparison form a one-way ratchet without a high-risk bulk metadata rewrite. Blast radius remains CI/catalog governance only; runtime routing and generated deployment behavior are unchanged.

## Findings
| ID | Priority | Description | Resolution |
|---|---|---|---|
| L1 | P1 | New sources could omit lifecycle metadata and enter a regenerated allowlist. | New gaps outside the pinned bootstrap require reason, approval reference, and approval date. |
| L2 | P2 | Existing 198 sources cannot migrate atomically without noisy risk. | Exact baseline paths are preserved in a separately hashed bootstrap file. |
| L3 | P1 | Non-project items could inherit inferred tier/owner values contrary to the schema. | Inheritance is restricted to project skill/rule items with a project declaration. |
| L4 | P1 | Project frontmatter could claim a non-project tier. | Declared project tier must equal `project`; conflicts fail. |
| L5 | P1 | Validator enums/types could diverge from the published schema. | Required fields and enums are loaded from the schema; values are type-checked and case-sensitive. |
| L6 | P1 | Inventory traversal or stale inventory could undermine coverage. | Canonical root-contained source paths and same-command inventory freshness are mandatory. |
| L7 | P1 | Bootstrap membership could be expanded silently. | Bootstrap bytes are pinned by SHA-256 in the validator. |
| L8 | P1 | A completed bootstrap item could regress and re-enter legacy status. | Completion must be recorded; recorded metadata regressions fail. |
| L9 | P1 | Deleting the completion record and reverting metadata together could bypass L8. | Completed paths are append-only relative to the protected base/previous SHA. |
| L10 | P1 | Missing shallow-checkout history could fail open. | Validation checkout fetches full history and an unreadable previous ref is fatal. |
| L11 | P1 | An existing exception could gain additional missing/invalid fields. | Current gap sets may only shrink; expansion requires an explicit approval record. |
| L12 | P1 | A deleted or still-incomplete source could be mislabeled as a newly completed migration. | Newly added completion records require the source to remain authoritative and metadata-complete in the same candidate. |

## Quantified claims
The generated report covers all 198 authoritative source items: 0 metadata-complete and 198 bootstrap exceptions at Phase 1 introduction. Missing-field counts are derived from the current inventory and source frontmatter, not handwritten totals. The bootstrap contains exactly those 198 canonical paths and is pinned to `develop@c2f27d00ce1e507176814307ba2a9252d7448ff8`.

## Rework ledger
1. Replaced a regeneratable exact allowlist with pinned bootstrap plus explicit future approvals.
2. Restricted inheritance and made schema values authoritative.
3. Added safe path and same-command inventory validation.
4. Added monotonic completion recording and regression rejection.
5. Made completion records append-only against protected history.
6. Made legacy gap sets nonexpanding without explicit approval and made unavailable history fatal.
7. Required newly recorded completions to remain present and metadata-complete, preventing simultaneous deletion from masquerading as migration.

## Evidence-predates-work
Artifact: plans/self-review-skill-lifecycle-schema.md
First-added commit: populated after this artifact commit
Work commit: subsequent lifecycle implementation commit
Verification: artifact commit must be an ancestor of implementation.
