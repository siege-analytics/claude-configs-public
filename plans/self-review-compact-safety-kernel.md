# Self-review: compact safety kernel and budget

## Assumptions

Domain(s): software engineering, agent governance
Geospatial cross-cut: no
Goal source: user-approved Skill Library Simplification Plan, kernel PR.
Goal source verification: inventory, lifecycle, and generated-source authority are merged on `develop` at `53aaed8e294629f74f2cdccd0e5f7dfddcf03817`.
Plan reference: approved `skill-library-simplification.md`, Phase 2 / proposed PR 4.
Pre-author-inventory: 37 general rule files plus 1 project rule currently produce an approximately 425k-character bundle; progressive loading is deliberately the next PR, not this one.
Investigate-artifact: current `skills/RULES.md`, rule bundle metrics, and generated-source authority catalog.
Pre-mortem-artifact: Risks below.
Hostile-review-artifact: three independent rounds completed; all S1/S2 findings resolved and recorded in `plans/hostile-review-compact-safety-kernel.md`.
Project-contribution: define the small non-overridable constitution that the later resolver can load globally without flattening on-demand or project-specific policy.

## Pre-implementation comprehension

Current behavior: all rule prose is bundled; no separately measured kernel states precedence or the minimum safety invariants. Project rules are scoped but there is no compact contract explaining what they may override.

Intended behavior: add one concise canonical kernel, generate it into nested/flat/Claude Code/Craft Agent forms, validate exact invariant IDs and precedence, forbid embedded shelf content, and enforce hard budgets of 80,000 characters and 20,000 estimated tokens. This PR does not switch runtime loading; the progressive-loading PR will make the kernel/resolver the always-loaded surface.

Steps:
1. author invariant-focused kernel prose without full procedures;
2. define project/task override precedence with a non-overridable safety boundary;
3. generate the kernel into all four artifact forms;
4. add it to generated-source authority coverage;
5. add deterministic budget/structure catalog and negative fixtures;
6. enforce in hosted CI while preserving the current bundle until progressive loading.

Success criteria: all ten approved responsibilities are represented by stable IDs; kernel remains below both hard budgets; no shelf/reference body is embedded; project overlays remain authoritative within scope but cannot weaken credential, destructive-action, branch-topology, exact-main deployment, permission, or evidence protections; all existing suites pass.

## Risks

1. Calling the kernel “always loaded” before resolver migration would misstate runtime behavior. Label it a candidate/runtime target until the next PR.
2. Condensing safety may accidentally weaken enforcement. Existing hooks and detailed procedures remain intact and linked; this PR adds no replacement/removal.
3. Project precedence could flatten legitimate overlays. State that overlays win within project scope except for a narrow enumerated safety boundary.
4. A character budget alone can be gamed with dense prose. Enforce both characters and estimated tokens plus required invariant IDs.
5. A copied reference shelf could fit the budget but violate architecture. Reject shelf tokens/paths and keep the kernel principles-only.
6. Generated kernel copies could drift. Extend the merged source-authority catalog and CI.

## Senior adversarial checklist

Reject missing/duplicate invariant IDs, over-budget source or artifacts, budget metadata drift, shelf inclusion, override ambiguity, safety-kernel weakening, generated-copy omissions, and any accidental switch in runtime loading.

## Peer review

Three hostile-review rounds challenged project/user precedence, source-to-artifact binding, source symlinks, invariant-heading loopholes, shelf-globalization prose, and stale authority catalogs. All identified S1/S2 findings were fixed; the final confirmation found none remaining.

## Lead review

A separately generated and budgeted kernel is the reversible prerequisite for progressive loading. Keeping current runtime loading unchanged avoids combining policy authorship with resolver cutover. Every budget check now transitively performs a fresh isolated build through generated-source authority before accepting artifact hashes.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| K1 | P1 | No compact machine-budgeted safety constitution existed. | Added ten stable invariants and hard source/artifact budgets. |
| K2 | P1 | Override precedence was implicit. | Matching project overlays are authoritative in declared scope beneath the narrow kernel boundary; conflicts ask. |
| K3 | P2 | Current bundle is approximately 425k characters. | Kernel is measured separately; runtime cutover remains the next PR. |
| K4 | P1 | Measured artifacts were not initially bound to validated source semantics. | Artifact hashes must match fresh-build authority, and the authority check is mandatory for every budget invocation. |
| K5 | P1 | Resolving before symlink checks could accept a linked kernel source. | Every source path component is checked before resolution. |
| K6 | P1 | Extra/malformed K headings and prose shelf-globalization could evade literal checks. | All K-number headings must exactly equal K1 through K10; literal and prose shelf guards have negative fixtures. |
| K7 | P2 | Shelf prose detection is not a complete semantic resolver. | Catalog labels it heuristic; deterministic shelf isolation remains a required progressive-loading invariant. |

## Quantified claims

Current full rules bundle is 424,988 characters. The candidate kernel is 6,944 characters and 1,736 estimated tokens, versus hard limits of 80,000 characters and 20,000 estimated tokens. Generated-source authority now covers 804 snapshots and 2,900 generated file mappings after adding the four kernel forms.

## Rework ledger

1. Corrected matching-overlay precedence and explicit conflict handling.
2. Bound all generated kernel artifacts to the fresh-build authority catalog.
3. Rejected pre-resolution source symlinks.
4. Closed extra/malformed invariant-heading and prose shelf-globalization loopholes.
5. Made every kernel budget invocation fail closed unless fresh isolated authority verification passes.

## Evidence-predates-work

Artifact: `plans/self-review-compact-safety-kernel.md`
First-added commit: this planning commit
Work commit: subsequent implementation commit
Verification: this commit must be an ancestor of implementation.
