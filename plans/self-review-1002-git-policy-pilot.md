# Self-review: #1002 exact Git policy pilot

Pre-mortem-artifact: plans/pre-mortem-1002-git-policy-pilot.md
Hostile-review-artifact: plans/hostile-review-1002-git-policy-pilot.md

## Assumptions

- The active selection is the independently accepted exact snapshot `ecef9e8620f477cdea4962cd3d737e16873f06fa`, blob `086e7bda8e9f588c57294ed0899f9ff2ffa982c5`, review `5543665034`; working policy remains proposal-only.
- #1001 composition is configured content and cannot establish operation authority.
- `pull_request_target` executes workflow YAML/ref from default branch `main`, not the PR base. The registered main workflow delegates to the exact base's topology entrypoint; checked-out develop YAML is not executed-workflow evidence.
- Provider execution and required-check protection remain separate claims. The user's later #1019 negative/replacement-head probe must prove the repaired invocation and protection state.
- The bounded first deployment supports same-repository PRs, linear commits and two-parent merges only.

## Test plan

- Install one unchanged parent and accepted composed package into strict and trunk disposable repositories.
- Execute ordinary, `-F`, alias, chain and `--no-verify` commits and enumerate exact ranges.
- Replay invalid interior messages, stale heads, wrong repositories, explicit ports, fork/source differences, absent/inert hooks, policy proposals, missing/stale/mixed-lock installs, mutable trusted bytes, unavailable ranges, two-parent merges and octopus commits.
- Rebuild the complete installed package from a clean clone of the exact trusted revision using the existing composition API; compare every candidate-head installed file and the complete receipt.
- Mutate resident guidance, parent-content digest and effective-policy digest independently and require each contradiction to fail closed.
- Require generated guidance and executable branch/ticket decisions to agree.
- Run review-risk downgrade probes, focused suite, native Python/hook/workflow matrix, builds and generated freshness before publication.

## Peer review

A hostile model review found a concrete port-identity collapse and noted candidate-origin/host-input boundaries. The port reproduction was added and the interface split canonical target from source origin; unsupported forks now reject. Independent adapter review then reproduced configured-integrity and fixture-execution bypasses, repaired by exact trusted recomposition/full-tree comparison and non-short-circuiting setup. Follow-up review separated canonical promotion and sealed complete workflow registration. The subsequent live #1019 negative then falsified the activation premise: GitHub executed the default-branch main workflow and omitted the develop-only adapter step, so a missing-ticket candidate passed. The repair now preserves the registered topology step, invokes the adapter from the exact base entrypoint, parses exact host event inputs, fetches complete trusted history, and records actual default-workflow ref/revision/blob separately. A local replay also caught Bash-4-only `mapfile`; portable parsing replaced it. Fresh exact-head peer review remains required.

## Lead review

Implementation self-review confirms topology remains first and unchanged; provider activation occurs only under `GITHUB_EVENT_NAME=pull_request_target`; host event facts must agree with workflow inputs and both checkout HEADs; canonical history is deepened before immutable ancestry/blob checks; and `GITHUB_WORKFLOW_SHA` must equal fetched `origin/main`. The adapter receipt separates actual default-workflow and exact-base entrypoint identities. Independent exact-head review remains required. This repair still cannot prove its own hosted execution or required protection.

## Quantified claims

- 13 focused disposable/provider scenarios pass, including exact default-workflow identity, registered topology-entrypoint event denial, entrypoint/validator mutations, six installed-package mutations, and canonical-promotion negatives.
- 34 effective-policy and 21 gate-contract scenarios pass at the selected snapshot/contract.
- Final combined provider-repair validation passes 13/13 protected-policy/provider scenarios, 10/10 topology scenarios, 34/34 effective-policy scenarios, 21/21 gate-contract scenarios, 28/28 Python modules, 36/36 native hook suites and 2/2 workflow suites.
- The accepted scanner sequence and four-package documentation/runtime suites pass after integration. Canonical build/check, skill inventory, generated authority (198 sources / 804 snapshots / 2,916 mappings), progressive-loading metrics, review-risk metrics, kernel budget, ontology, three hook-package validators and flat-layout validation pass with no generated tracked drift.
- Two synthetic projects share one recomputed parent-content SHA-256 and produce distinct effective-policy SHA-256 identities.
- Every commit in exact `base..head` is evaluated; supported commits have at most two parents.
- Seven policy/validator dependencies plus the registered topology entrypoint are byte-bound to exact base blobs. The actual executed workflow is separately bound to canonical `origin/main`, `GITHUB_WORKFLOW_REF`, `GITHUB_WORKFLOW_SHA`, its Git blob and SHA-256.
- The adapter has zero final-allow result state; `eligible` always requires a separate protected host check.

## Rollback and non-claims

The change is additive. Keep the old authoritative guard through subsequent-head provider and required-protection evidence. No `main` change, release, install, deployment, production retirement or runtime rollout is authorized. #852 artifact identity and #1003 provider/protection proof remain separate prerequisites for #1004.
