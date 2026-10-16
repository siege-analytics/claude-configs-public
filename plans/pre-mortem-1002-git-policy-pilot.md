# Pre-mortem: #1002 exact Git policy pilot

## Scope

Prove operation-level policy evaluation for two selected projects with real disposable Git histories. Preserve the accepted #848 resolver and #1001 composition as the single policy/content path. The adapter emits eligibility evidence only; #1003 owns live host/provider proof and #1004 owns activation/rollback.

## Failure modes and controls

1. **Candidate replaces its own validator or workflow.** Execute from a base-controlled checkout and require current bytes for the validator, workflow, resolver, contract helper, schema, contract and selection receipt to equal exact Git blobs at the declared trusted revision.
2. **A green head hides an invalid interior commit.** Enumerate every object in exact `base..head`, evaluate every complete commit message and retain ordered object/parent/path/message-digest evidence.
3. **Local hook is bypassed or inert.** Exercise `--no-verify`, absent and no-op hooks. Treat local-hook configuration as observed feedback with `authorization_effect: none`; protected evaluation independently rechecks the range.
4. **Policy proposal authorizes itself.** Load only the immutable selected policy from its reviewed ancestor commit. Candidate policy is proposal data and can never replace active values.
5. **Repository alias or fork selects another project.** Keep canonical target and candidate source identities separate. Require exact normalized host/owner/repository equality for the bounded same-repository pilot; reject ports, forks, basename matching and unknown identities.
6. **Generated package is stale or has mixed locks.** Require the installed composition receipt to agree with exact project identity, selection, effective values and parent lock. Keep it configured-only and require #852 output identities separately for #1004 artifact activation.
7. **Merge topology hides content.** Support only linear and two-parent commits and enumerate the complete reachable range. Reject octopus and unavailable/non-ancestor ranges.
8. **Caller values manufacture host authorization.** Emit only `eligible`, `denied` or `error`; even eligibility says `protected-host-check-required`. Only a provider result bound to the same exact head and base-controlled identities may establish capability.
9. **The introducing PR self-proves registration.** It cannot: `pull_request_target` runs the older base. Retain the old authoritative guard, merge only after review, then use a subsequent head to exercise the new base-controlled path.
10. **A green provider job is not required protection.** Record repository ruleset/branch-protection evidence independently; never infer required status from a name or green badge.

## Rollback

The adapter is additive. The existing authoritative topology/validation guards remain unchanged through #1003/#1004 proof. Roll back by removing the new configured adapter/test/registration while retaining the selected pre-pilot policy and old required guard. No production route is retired in #1002.
