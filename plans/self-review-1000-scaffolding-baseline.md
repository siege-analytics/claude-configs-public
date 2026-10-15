# Self-review: #1000 scaffolding baseline

## Scope

Plan-only evidence reconciliation at exact `develop` SHA `f97d194fedf1eda053a16e938851c6151f308d72`. No hook, policy, build, package, deployment, release, install, or runtime behavior changes.

## Claims checked

- Re-ran the named build, registry, project resolution, wrapper, runtime, verifier, consumer, scanner, review, advisory, concurrency, and session-isolation suites.
- Regenerated ignored local packages without `--deploy`; verified the worktree retained only the two intended untracked plan files.
- Confirmed the pre-build runtime suite can skip with exit 0, then used the post-build 9-case run as evidence.
- Confirmed generated pre-push points to `hooks/git/self-review.sh`, not the range-aware hook.
- Confirmed the scanner suite has five basic scenarios and does not prove staged/PR-head blob truth.
- Confirmed hub cap precedence is environment → state file → default 3; no project/manifest field was found.
- Confirmed fallback consumption tags resolve live `release/*` branch tips and changelog promotion occurs after package branch builds.
- Kept uncertain claims marked partial/unverified instead of converting absence of search results into proof.

## Risk and alternatives

- Risk: filename-based parser/policy counts undercount semantic definitions. The baseline labels them conservative lower bounds.
- Risk: synthetic fixture B could accidentally weaken locked safety. The fixture keeps Tier C, credential, and destructive-action floors locked.
- Alternative rejected: encode a new policy schema in #1000. That would preempt #851/#848 contract review; this slice only specifies fixtures and evidence.
- Alternative rejected: treat current green suites as completion of open tickets. Each disposition is criterion-specific and preserves missing boundary tests.

## Focused review response

- Split the common resident integrity floor from profile-selected workflow policy so the synthetic trunk fixture does not contradict literal K5 topology while this repository retains its strict profile.
- Embedded the exact read-only measurement probe, including generated-output prerequisites, filters, symlink/file counting, and bytes/characters/token-estimate definitions.
- Made duplicate composition deterministic: identical repeated references load once; conflicting replacement declarations reject.
- Added explicit ticket cleanup/exception semantics and a protected exact-range/head acceptance requirement.
- No runtime or policy implementation changed.

## Validation

```text
git diff --check
python3 bin/build.py --check
python3 bin/review-risk.py --paths plans/scaffolding-baseline-1000.md plans/self-review-1000-scaffolding-baseline.md --declared A
```

Expected tier: A (plans only). Required evidence: Self-Review.

## Rollback

Delete the two new plan files. No generated or live state is committed.
