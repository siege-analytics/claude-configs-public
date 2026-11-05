# Canonical instruction ownership and flat merge pilot

## Assumptions

Goal source: siege-analytics/claude-configs-public#1157, part of #1156; operator approved the staged instruction refactor and requires flat CraftAgents delivery.
Pre-author-inventory: current Core mainc7a6fe7 and clientmain32e8 are working; initial inventory and client builder/runtime observations precede these source edits.

Core ProcedureGraph selects ordered content and has no authorization effect. Effective policy models an integration branch, not a complete release/hotfix graph. The legacy client flat builder does not call that graph and writes native sources and generated outputs into the same tree. Its nested Core base is present in the current bind-mounted workspace but absent from a clean temporary flat build. A runtime wrapper therefore cannot be the portable contract.

## Design

One concise Core merge procedure references canonical authority/readiness/review and uses the target project's approved integration and release procedure. Siege K5 remains the scaffold topology owner. Resolvers navigate instead of copying merge readiness. Compatibility skill paths remain unchanged.

CraftAgents receives one generated skills/merge/SKILL.md with one frontmatter block. The client authors its narrow ElectInfo policy outside the generated skill path. Its existing builder combines the published Core base and client policy at build time, resolves existing tokens and records input provenance. It must not inline unrelated prerequisite skills or create a second policy engine. Other clients retain the generic base.

## Risks and falsification

- A generic integration branch does not authorize a release or hotfix. Missing project authority remains a dependent stop.
- A client policy must retain its nine Traffic Cop readiness gates, billing boundaries, role limits, actual holds and handoff conditions.
- A source/output collision could feed generated content back into the next build. Authored client policy must be disjoint from output.
- A source-relative link could work in the repository but fail in the flat artifact. Verify a clean output directory and complete referenced assets.
- One shared edit must flow through regeneration without hand-editing generic client paragraphs. Otherwise the pilot fails.
- No production gate/classifier, settings or protected-branch exception is added by this content refactor.

## Test plan

Validate source references, both layouts, generated freshness/provenance and actual flat discovery. Exercise deterministic regeneration and stale-output detection with a changed base and a changed client policy. Keep branch-policy, protected-acceptance and content selection separate. Independently evaluate approved trunk integration, Siege develop promotion, ElectInfo TC/non-TC roles, missing review, explicit holds, routine conflict, retained branches and ambiguous release policy. Source evaluation and package checks are not live backend callback evidence.

Use supported tool preflight, relevant existing composition/package checks and exact-head protected CI. Preserve working installs until accepted source publication. Normal local source activation and reviewed client main/normal cron delivery require fresh preservation baselines.

## Peer review

Independent source review accepted the concise Core procedure after finding and correcting the inherited unqualified main-branch decision tree. A separate forward evaluation exercised ten scenario fact sets; earlier draft findings are retained, and current trunk/Siege/other-project hotfix decisions follow their actual policy. This is source interpretation, not tool/backend execution. Client flat composition remains separately reviewed.

## Lead review

The pilot removes duplicate generic prose while retaining declared project policy and the current enforcement boundaries. Broader Think/review/coordination/deployment consolidation follows only after this packaging pattern is verified.

Pre-mortem-artifact: plans/instruction-architecture-1157.md#risks-and-falsification
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1157

## Quantified claims

Initial source size and package counts are inventory observations, not correctness proofs. Final source bindings, tool results and any size comparisons belong in the actual validation record.

## Canary and rollback

Start with isolated source/package fixtures and one active client. Keep prior release and install snapshots. Rollback uses the normal reviewed source/deployment path; it must not clear task state, operator settings or owner holds.

## Validation record

Final canonical refresh/freshness passed. Skill frontmatter validation, effective-policy fixtures and procedure-composition fixtures passed. Language/data source and packaged replay and protected-policy checks passed; their results and exact-head protected CI remain separate. The first refresh was invalidated by concurrent draft edits and is not a final pass. Fixture changes are twelve numeric size leaves only; identities, routes, item counts, budgets and expected rejection states are unchanged. This retains the data-fixture path's required Tier C. Full protected CI on the final head is required before merge; no passing local full-suite result is claimed.
