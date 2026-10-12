# Self-review: PR #924 committed deploy-model marker

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: PR #924 review finding that an untracked `.claude/deploy-model` marker could bypass the deploy-stamp gate.
Goal source verification: The existing PR tests proved only a committed happy path and missing-marker failure path; direct inspection showed the hook read the mutable worktree file.
Plan reference: PR #924 review thread and approved develop-to-main reconciliation plan.
Pre-author-inventory: Existing implementation at `hooks/git/self-review.sh:1000-1065` and `hooks/_test/self_review_hook_489_deploy_model.test.sh`.
Investigate-artifact: TRIVIAL — focused two-file correction; inspection identified the exact mutable-worktree condition.
Pre-mortem-artifact: TRIVIAL — principal risk is accepting staged/untracked policy state; negative tests cover both forms.
Hostile-review-artifact: WAIVED — focused correction implementing the already-posted adversarial PR finding.
Project-contribution: Makes merge-then-deploy an auditable committed repository policy instead of a mutable local bypass.

## Pre-implementation comprehension
Current behavior: the hook uses `-f` and `grep` against the worktree marker, so an untracked or staged-only marker can disable the deploy-stamp requirement.
Intended behavior: only `HEAD:.claude/deploy-model` with the exact value `merge-then-deploy` may select that model.
Steps: read the marker from the HEAD tree; add untracked and staged-only negative cases; run focused and baseline hook tests plus the complete build check.
Success criteria: committed marker passes; absent, untracked, and staged-only markers block; baseline behavior and build remain green.
Risk: reading from the wrong repository root could reject a valid committed marker; the existing fixture executes in isolated repositories and covers root discovery.

## Senior adversarial checklist
1. The initial PR claimed “committed” without enforcing committed state.
2. The observable result is explicit: mutable markers remain blocked.
3. Deployment semantics and the solo-deploy true positive remain covered.
4. Staged-only state was originally omitted and is now tested.
5. Prior PR implementation and tests were read directly.
6. Work is in the PR #924 branch worktree.
7. Two new failure cases are included.
8. The class is closed by reading policy from the Git object database, not by adding another filesystem check.
9. Done includes fresh CI on the updated PR before merge.
10. Full build and baseline tests will not be skipped.

## Peer review
- Shell correctness: `git cat-file -e HEAD:<path>` proves the path is committed; `git show HEAD:<path>` validates committed content.
- Failure paths: untracked and staged-only markers each have a negative regression.
- Syntax check: `bash -n` will cover both modified shell files.
- Tests: focused #924 regression, #819/#820 baseline, `python3 bin/build.py --check`, and `git diff --check`.

## Lead review
Software engineering verdict: approach fits the trust boundary because repository policy is selected by reviewed commit state. Blast radius is limited to the #489 deploy-stamp carve-out. The sequencing assumption is that post-main deployment remains a separate enforced release step.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | Mutable worktree marker could bypass deploy-stamp enforcement. | fixed |

## Quantified claims
No release-count or corpus-count claims.

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Commit hook rejected missing self-review trailers | Initial commit attempt preceded durable artifact | Low | Low | 1:1 |

## Evidence-predates-work
Artifact: plans/self-review-924-marker-hardening.md
First-added commit: populated after this artifact commit
Work commit: pending
Verification: populated before push

## Hostile-review-waiver
This is a two-file focused hardening of an already identified review finding, with direct negative regression coverage; a separate provider review would not be proportionate.
