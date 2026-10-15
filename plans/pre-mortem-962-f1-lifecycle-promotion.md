# Pre-mortem: epic #962 F1 lifecycle first promotion

## Scope

Permit the pinned first `develop` to `main` promotion to cross a pre-lifecycle `main` baseline without turning every missing historical lifecycle report into a bootstrap exception.

## Failure scenarios

1. **A symbolic or abbreviated ref bypasses the exact baseline pin.** Resolve every supplied ref to a full commit SHA before comparing it with the pinned baseline.
2. **A feature or fork impersonates the promotion.** Require GitHub pull-request context with base `main`, head `develop`, and identical canonical/head repositories.
3. **A forged event label authorizes an unrelated tree.** Require a two-parent candidate merge: first parent equals the pinned previous main commit, second parent equals the promoted develop commit, previous main is an ancestor of develop, and candidate/develop trees are identical.
4. **The first push follows different semantics from the PR check.** Cover the pull-request base SHA and push `before` SHA separately; for the push derive the promoted develop commit from the candidate's second parent.
5. **The exception disables migration ratchets.** Compare current gaps and completions with the promoted develop commit's first parent, which must contain a lifecycle report; continue enforcing the pinned bootstrap digest and tracked allowlist freshness.
6. **An arbitrary no-history commit gains access.** Keep the allowlist to the exact existing policy bootstrap SHA and exact first-promotion main SHA; reject every other missing report.
7. **A non-merge/squash/direct push is mistaken for the canonical promotion.** Fail unless the candidate has exactly two parents with the required parent order and unchanged promoted tree.
8. **The fix accidentally publishes or promotes.** Modify only validation code, fixtures, workflow context, documentation, and review evidence; target a draft PR to `develop` and perform no merge, release, deployment, installation, or `main` write.

## Rollback

Revert the single F1 commit on `develop`. The prior fail-closed behavior returns immediately; no catalog state, release artifact, installation, or branch promotion is mutated by this change.
