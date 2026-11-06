# Think procedure and conditional references

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1186
Part-of: #1156
Pre-author-inventory: fresh origin/develop7e1e0ae; reviewed actual Think501lines, resolver, ownership map, Kernel K1/K6, self-review tiers and universal/task resolver before source edits.

## Design

Keep one Think SKILL entrypoint with applicability, existing authorization-owner links, compact sequence, exact task bootstrap and separate pre-edit/commit-review distinction. Move existing detailed workflow to design-workflow.md, signal lifecycle to task-evidence.md and class claims to premise-claims.md, all ordinary sibling files. Resolver navigates instead of copying workflow. Existing preparation obligations remain; entry links are conditional on the phase they own, not optional waivers. No runtime, schema, tier, project policy or authorization change.

## Investigation

Verified source: skills/think/SKILL.md29-243 owns ticket/design/downstream preparation; lines289-501 own signal identity, scopes, claims and lifecycle. hooks/bash/universal-mutation-gate.sh259-262 requires implementing for A, investigation/pre-mortem for B, plus junior/senior/artifacts-posted for C. hooks/lib/resolve-think-gate.py829-885 computes declared-versus-target floor and fails closed. self-review/SKILL.md68-80 owns separate commit tiers; its B review requirement does not waive pre-edit preparation. KERNEL K1 says another task cannot authorize or block this task. RESOLVER51-84 repeats stronger universal mechanical language; correct navigation must preserve authored requirements while accurately distinguishing mechanical minima. bin/build.py1038-1081 copies ordinary support Markdown and resolves its references for either layout. No nested skill import is necessary.

Investigation Dependencies: verify preservation of every extracted workflow subsection and gate field; clean package must contain all three supports and resolve their links. If a consumer depends on the previous inline placement, update its navigation/test rather than omit the obligation. No runtime test result is claimed by this inspection.

## Pre-mortem

Severity: 75
Launch-Blocking Tiger: shortening Think drops preparation or implies TierB waiver. Mitigation: retain original workflow detail, separate named checkpoints, independent decision evaluation and source diff review. Implementation may proceed: YES with mitigation tested before merge.

Severity: 70
Launch-Blocking Tiger: references work in authored tree but vanish from flat delivery. Mitigation: clean real builder package test checks the complete reference closure and a missing-file negative control. No nested SKILL imports.

Severity: 65
Launch-Blocking Tiger: gate existence becomes approval or one task blocks another. Mitigation: preserve canonical authority and exact task ownership; forward scenarios include explicit holds/reviewer roles/independent tasks. No new gate fields.

Paper Tiger: local package verification mutates live settings. Build in temporary output only; no deploy/install flag.
Elephant: universal preparation versus broader future proportional authored workflow remains a separate policy decision; this slice does not settle it by deleting requirements.

## Test plan

Add real clean flat/nested Think closure regression with missing support negative control and structural single-entry discovery assertion. Existing tier/task scope and commit-review tests retain expected behavior. Validate frontmatter/references, build/freshness and focused relevant package checks. Run native commit/push hooks and real source-bound test producer. Independent forward source evaluation and Root review precede merge; protected CI supplies full applicable suite.

## Authorization

User approved this source-consolidation slice. Routine file boundaries are within that outcome. Root owns protected merge and install; no new approval checkpoint is introduced.
