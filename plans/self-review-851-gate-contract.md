# Self-review: #851 authoritative gate contract pilot

Pre-mortem-artifact: plans/self-review-851-gate-contract.md#pre-mortem
Hostile-review-artifact: plans/self-review-851-gate-contract.md#hostile-review

## Assumptions

- This slice defines and validates the bounded contract substrate for branch policy, ticket requirement, and review procedure binding; it does not implement #848 precedence resolution.
- Checked-in synthetic fixtures are configured contract instances, not proof of effective-policy provenance, protected acceptance, installation, or live host capability.
- The existing `bin/build.py` enforcement generator remains authoritative for generated Craft artifacts; no second runtime registry or all-gate migration is introduced.
- The native commit-message hook and generated pre-push hook are the executable pilot boundaries. A generated manifest claim alone is insufficient.
- Custom procedure replacement remains #1001; the #851 fixture procedure must resolve to an existing canonical skill.
- Protected end-to-end acceptance remains #1002 and live Claude/Codex/backend evidence remains #1003.

## Pre-mortem

Potential failure modes considered before acceptance:

1. Source catalog, JSON Schema, executable checker, generated manifest, settings metadata, and package bytes drift independently.
2. A package contains a no-op or symlinked executable while source probes remain green.
3. A generated pre-push script retains expected strings but exits before invoking a blocking gate.
4. CI retains command text while a condition, early exit, or `|| true` prevents enforcement.
5. Project data changes a parent-owned locked field or labels the change as a higher-authority override.
6. Missing capabilities, overlapping result codes, duplicate IDs/probes, unknown fields, or unsafe paths are accepted.
7. A procedure binding matches the type pattern but resolves to no canonical source.
8. Configuration metadata is misreported as verified runtime or protected-acceptance evidence.
9. Importing `build.py` through isolated `importlib` fixtures fails because of an eager sibling import.
10. Build changes leave generated skill inventory or authority evidence stale.

The implementation and tests now fail closed for 1–7 and 9–10. Item 8 is bounded by `configured_evidence_only: true`, fixed capability states, explicit comments, and deferred live/protected tickets.

## Test plan

- Validate exact source schema, three policy fields, four capabilities, and two synthetic fixtures.
- Run both source and packaged ticket allow/deny probes.
- Run packaged pre-push with controlled clean and blocking gate executables.
- Mutate unknown fields, duplicate IDs/probes, result-code overlaps, locks, capabilities, paths, schema constraints, generated metadata, concrete registrations, package files, executable bytes, symlinks, procedures, parent locks, and CI step shape.
- Build complete consumer artifacts and verify source/generated/package agreement.
- Run all Python test modules with Python 3.13, all hook shell suites, both workflow policy suites, source/consumer hook validators, ontology checks, inventory/authority freshness, and build checks.

## Hostile review

Independent staged-diff falsification produced four successive review packets:

1. Found generated settings/gate removal, packaged ticket no-op/symlink, nested schema drift, self-declared fixture provenance, and unresolved procedure risks.
2. Confirmed ticket/settings/procedure closures; found an early-exit packaged pre-push bypass and a deeper override-path schema drift.
3. Confirmed those closures; found a conditional CI-step skip that preserved command strings.
4. The conditional, early-exit, and error-swallowing workflow variants are now rejected by an exact bounded step-shape check.
5. Independent exact-SHA review of the initial PR head reproduced four additional structural bypasses: declared registration could disagree with the actual target; only the last of multiple package paths was probed; an incompatible uninspected JSON Schema constraint passed; and JSON key order bypassed duplicate repository identity detection. The replacement rejects all alternate pilot target/package declarations, resolves validation through the declared path, seals the complete reviewed schema while evaluating the canonical source against it, and compares identity fields in canonical order.

The remaining provenance concern is explicitly outside this fixture validator: #848 must derive effective values and provenance from separate approved inputs rather than trusting project declarations. The fixture files here are reviewed synthetic inputs and make no effective-policy or authorization claim.

## Peer review

No same-account GitHub approval can be recorded before publication. The pre-commit peer role is represented by independent model-based hostile review of the exact staged diffs and executable reproductions for every P1 finding. A separate exact-head repository review is still required before merge; this artifact is not that acceptance verdict.

## Lead review

Lead check confirms:

- scope remains one contract/checker integrated with the existing generator;
- no `main`, release, deployment, installation, or live runtime mutation occurs;
- generated metadata remains `configured`, not `verified`;
- project attempts cannot change ticket locks or protected/local branch constraints;
- the synthetic trunk fixture changes only the organization-profile branch field;
- all P1 hostile findings have direct negatives;
- #848, #1001, #1002, and #1003 retain their separate responsibilities.

## Quantified claims

- Contract: 3 policy fields, 4 capability declarations, 2 synthetic fixture instances.
- Focused contract suite: 20 tests passing after exact-SHA hostile remediation.
- Ontology: 34 terms and 119 bound values validated; ontology suite 25/25.
- Python regression: 20/20 modules passing with Python 3.13. The system Python 3.9 cannot import pre-existing PEP 604 annotations and is not used for that matrix.
- Hook regression: 36/36 shell suites passing.
- Workflow policy regression: 2/2 suites passing.
- Hook package validation: source 40 paths, Claude Code 37 paths, Craft Agent 40 paths; warnings are the existing unreferenced-hook inventory.
- Generated authority: 198 sources, 804 artifact snapshots, 2,904 generated file mappings current.

## Rollback

Before integration, rollback is deletion of the feature branch/worktree. After an authorized merge to `develop`, exact rollback is a revert of that merge commit followed by full rebuild, contract/ontology checks, inventory/authority regeneration checks, and the complete Tier C matrix. No release or installation state is changed by this slice.

## Residual risks and handoff

- #848 must derive effective-policy provenance and evaluate policy-changing operations under the previously approved policy.
- #1001 must prove project procedure replacement/extension and resident composition without duplicate loading or authority changes.
- #1002 must prove exact pushed-range/head protected acceptance, including bypassed local hooks.
- #1003 must produce pinned live Claude/Codex/backend capability evidence; generated registration cannot substitute for it.
- The contract currently validates the bounded pilot only. Expanding it to every legacy gate without a migrated behavior and tests would recreate the general policy language intentionally excluded from #851.
