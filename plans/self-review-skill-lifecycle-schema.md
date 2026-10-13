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
Hostile-review-artifact: pending before push.
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
Pending implementation.

## Lead review
Approach fit: an exact migration allowlist creates a ratchet without a high-risk bulk metadata rewrite. Blast radius is CI/catalog governance only.

## Findings
| ID | Priority | Description | Resolution |
|---|---|---|---|
| L1 | P1 | New sources can omit lifecycle/ownership metadata indefinitely. | pending fix |
| L2 | P2 | Existing 198 sources cannot migrate atomically without noisy risk. | exact temporary allowlist |

## Quantified claims
Baseline counts come from the committed Phase 0 catalog and will be asserted by the generator.

## Rework ledger
No rework yet.

## Evidence-predates-work
Artifact: plans/self-review-skill-lifecycle-schema.md
First-added commit: populated after this artifact commit
Work commit: subsequent lifecycle implementation commit
Verification: artifact commit must be an ancestor of implementation.
