# Pre-mortem: epic #962 F4 enforcement dependency risk

Goal source: GitHub issue #962 latest comment, finding F4, and PR #958 review 5528052640.

## Scope

Correct Tier C classification for shared blocking dependencies and CI/runtime enforcement infrastructure without promoting every hook or changing runtime behavior.

## Failure modes considered before implementation

1. **Only the three reported examples are fixed.** A neighboring helper can still turn a blocking decision into an allow while receiving Tier B review.
   - Prevention: trace configured entrypoints, sourced helpers, generated native hooks/manifests, and checker inputs; record the audited graph in documentation.
2. **A broad `hooks/**` pattern hides the audit gap.** Advisory or unrelated utilities receive Tier C without evidence, making the policy noisy and encouraging future bypasses.
   - Prevention: use explicit entrypoint/helper patterns and document exclusions.
3. **Rename or deletion escapes the floor.** A dependency moved to a benign destination is classified by only its new path.
   - Prevention: retain NUL-safe `--no-renames` discovery and parameterize staged modification, deletion, and rename fixtures for every added path.
4. **Direct classification passes but declared Tier B is accepted.** Tests assert the computed label without exercising the enforcement exit status.
   - Prevention: invoke the real CLI with `--staged --declared B` for each change shape and require exit 2 plus `valid: false`.
5. **Generated catalogs are mistaken for policy.** Broadly elevating every generated metric/output creates a Tier C burden without protecting a decision point.
   - Prevention: classify code that computes the expected state; retain generated outputs below Tier C when hand edits are recomputed and rejected.
6. **Runtime generator remains Tier B.** Hook source files are protected, but `build.py` can omit or downgrade them in consumer packages.
   - Prevention: classify `bin/build.py` and hook wiring validation as Tier C.
7. **Authority checker has an unprotected discovery dependency.** The checker is Tier C but a Tier B inventory implementation can omit canonical sources consistently.
   - Prevention: classify `bin/skill-inventory.py` as an authority dependency.
8. **Documentation and metrics drift.** The policy changes but review evidence continues to describe the old path set.
   - Prevention: regenerate metrics, update the changelog and audit document, and run freshness checks.

## Negative-test plan

- Reproduce Tier B for the three named paths at the exact base.
- After policy change, require Tier C and declared-B rejection for every audited dependency.
- Exercise staged modification, deletion, and rename for each dependency.
- Pin `log-block.sh`, scaffold-test-stub, review-risk metrics, and an unknown agent-comms path below Tier C.
- Run classifier unit and shell policy suites, then the complete Python/hook/workflow suite and generated freshness checks.

## Rollback

Revert the F4 commit. No release, install, deployment, publication, main promotion, or merge is authorized.
