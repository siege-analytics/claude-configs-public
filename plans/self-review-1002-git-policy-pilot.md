# Self-review: #1002 exact Git policy pilot

Pre-mortem-artifact: plans/pre-mortem-1002-git-policy-pilot.md
Hostile-review-artifact: plans/hostile-review-1002-git-policy-pilot.md

## Assumptions

- The immutable #848 selection remains the sole active policy until a separately reviewed replacement snapshot is sealed.
- #1001 composition is configured content and cannot establish operation authority.
- A base-controlled host provider and required-check protection are unavailable to the introducing PR; #1003 must prove them on a later head.
- The bounded first deployment supports same-repository PRs, linear commits and two-parent merges only.

## Test plan

- Install one unchanged parent and accepted composed package into strict and trunk disposable repositories.
- Execute ordinary, `-F`, alias, chain and `--no-verify` commits and enumerate exact ranges.
- Replay invalid interior messages, stale heads, wrong repositories, explicit ports, fork/source differences, absent/inert hooks, policy proposals, missing/stale/mixed-lock installs, mutable trusted bytes, unavailable ranges, two-parent merges and octopus commits.
- Require generated guidance and executable branch/ticket decisions to agree.
- Run review-risk downgrade probes, focused suite, native Python/hook/workflow matrix, builds and generated freshness before publication.

## Peer review

A hostile model review found a concrete port-identity collapse and noted candidate-origin/host-input boundaries. The port reproduction was added and the interface split canonical target from source origin; unsupported forks now reject. Fresh exact-head peer review remains required after contract/policy resealing.

## Lead review

Pending exact-head review. The acceptance question is whether the adapter correctly produces non-authoritative eligibility evidence from immutable prior policy and exact Git facts, not whether this PR proves live branch protection.

## Quantified claims

- 10 focused disposable-history scenarios currently pass.
- Two synthetic projects share one parent-content SHA-256 and produce distinct effective-policy SHA-256 identities.
- Every commit in exact `base..head` is evaluated; supported commits have at most two parents.
- Seven trusted authority dependency paths are byte-bound to exact Git blobs at the declared trusted revision.
- The adapter has zero final-allow result state; `eligible` always requires a separate protected host check.

## Rollback and non-claims

The change is additive. Keep the old authoritative guard through subsequent-head provider and required-protection evidence. No `main` change, release, install, deployment, production retirement or runtime rollout is authorized. #852 artifact identity and #1003 provider/protection proof remain separate prerequisites for #1004.
