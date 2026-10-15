# Skill lifecycle migration ratchet

`bin/skill-lifecycle.py` keeps lifecycle metadata migration one-way. It validates the authoritative inventory, a SHA-256-pinned bootstrap path set, exact approved gap sets, and an append-only completion registry. A current gap may shrink, but it may not expand without an exact approval.

## Previous-state selection

The workflow normally compares the candidate with the event's protected previous commit:

- pull request: `github.event.pull_request.base.sha`
- push: `github.event.before`
- merge queue: `github.event.merge_group.base_sha`

Refs are resolved to full commit SHAs before policy comparisons. Missing or unreadable refs fail closed.

Two exact no-report boundaries exist:

1. `c2f27d00ce1e507176814307ba2a9252d7448ff8` is the historical policy-introduction bootstrap.
2. `b2d91ef2900f58ddb37c10e1eb2803a7aeaa6753` is the pre-lifecycle `main` commit for the first promotion only.

The second boundary is not a general missing-history exception. It is accepted only when GitHub event context and the Git graph prove one of these transitions:

| Event | Required context |
|---|---|
| Promotion PR | `pull_request`, base `main`, head `develop`, same canonical repository, and the supplied PR head equals the candidate merge's second parent |
| First main push | `push` to `refs/heads/main`; GitHub must associate the pushed merge with exactly one merged same-repository `develop` → `main` PR, whose immutable head SHA equals the candidate merge's second parent |

For both events, the candidate must be a two-parent merge whose first parent is the pinned main baseline. The main baseline and lifecycle policy base must be ancestors of the promoted develop commit, and the candidate tree must exactly equal the promoted develop tree. Missing repository/ref identity fails closed. Squash, rebase, direct-push, conflict-resolution, feature/fork, altered-tree, and unrelated-history shapes fail.

The push workflow resolves provenance through GitHub's commit-associated pull-request API and passes only the returned 40-character PR head SHA to the checker. It does not compare with the mutable live `develop` ref, so a later develop commit cannot create a false block or retroactively bless another second parent.

## Ratchet continuity during first promotion

The first-promotion exception does not disable lifecycle comparisons. After the transition is proven, the checker loads previous gaps and completions from the promoted develop commit's first parent. That commit must contain a lifecycle gap report. Bootstrap digest validation, gap nonexpansion, append-only completions, completed-metadata regression checks, and tracked allowlist freshness then run normally.

## Local checks

```sh
python3 bin/_test/skill_lifecycle_test.py
python3 bin/skill-lifecycle.py --check
python3 bin/review-risk.py --paths \
  bin/skill-lifecycle.py \
  bin/_test/skill_lifecycle_test.py \
  .github/workflows/build-and-publish.yml
```

The fixture suite creates an isolated Git graph and covers both GitHub event paths plus arbitrary baselines, fork/feature contexts, non-merge pushes, changed merge trees, missing develop lifecycle history, bootstrap digest changes, gap expansion, and completion deletion.
