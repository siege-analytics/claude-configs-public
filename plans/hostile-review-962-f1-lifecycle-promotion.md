# Hostile review: epic #962 F1 lifecycle first promotion

## Scope

Independent Tier C review of `bin/skill-lifecycle.py`, its Git-history fixtures, the GitHub Actions event wiring, and lifecycle policy documentation. Reviewers were asked to falsify exact-baseline pinning, canonical branch/repository provenance, Git parent/tree/ancestry proof, real pull-request and first-push semantics, and continuity of bootstrap digest, gap expansion, and append-only completion protections.

## Round 1

Two independent reviewers rejected the initial implementation.

| Finding | Priority | Counterexample | Resolution |
|---|---|---|---|
| Push path treated any merge second parent as develop. | P1/P2 | A feature commit containing main and policy history, with a matching merge tree and prior lifecycle report, consumed the pinned baseline. | Push provenance must be supplied separately and equal merge parent 2; added a feature-derived negative fixture. |
| Missing PR head-repository identity was replaced with the canonical repository. | P2 | An unavailable `pull_request.head.repo.full_name` became same-repository through workflow fallback. | Removed the fallback; missing identity now reaches Python as empty and fails closed; added a missing-identity fixture. |

## Round 2

Both reviewers rejected comparison with live `refs/remotes/origin/develop`.

| Finding | Priority | Counterexample | Resolution |
|---|---|---|---|
| Live develop could advance after a valid promotion and falsely block it. | P2 | A new develop commit before the push job starts makes the branch tip differ from merge parent 2. | Replaced the mutable branch ref with the immutable head SHA of the PR associated with the pushed merge. |
| Live develop could retroactively bless a non-develop second parent. | P2 | Advance develop to a feature-derived second parent before validation; the mutable equality then passes. | GitHub lookup now requires exactly one merged same-repository `develop` → `main` PR whose `merge_commit_sha` is the pushed SHA; Python accepts only its full 40-hex head SHA. |

## Round 3

Two independent reviewers re-reviewed the revised files. Both returned `ACCEPT` with no remaining P1/P2 finding. They confirmed that the exact pinned baseline remains bounded by event identity, repository identity, immutable associated-PR provenance, merge parent order, ancestry, and tree equality, while ratchet state is loaded from the promoted develop commit's parent.

## Negative evidence

`bin/_test/skill_lifecycle_test.py` rejects:

- arbitrary missing-history baselines;
- non-`main`/non-`develop` PR context;
- fork and unavailable head-repository identity;
- non-merge/direct push shape;
- non-main push ref;
- changed promotion merge tree;
- feature-derived second parent;
- missing or mutable push provenance;
- promoted history without a prior lifecycle report;
- bootstrap digest tampering;
- unapproved gap expansion;
- completion record deletion and completed-metadata regression.

The same fixture accepts both promotion-PR and first-main-push semantics and proves that later develop advancement does not affect immutable push provenance.

## Disposition

ACCEPT after Round 3. No finding was waived. No release, publication, deployment, installation, merge, or main-branch mutation was performed.
