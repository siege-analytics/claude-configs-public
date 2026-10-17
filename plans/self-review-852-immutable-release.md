# #852 immutable release handoff

Pre-mortem-artifact: this document, Failure analysis
Hostile-review-artifact: this document, Peer review (independent review pending)

## Assumptions

Only the existing main-push publishing workflow may publish releases. Develop
remains integration-only. This change is tested using disposable local Git remotes
and generated packages; no actual release or promotion is part of implementation.
Release provenance identifies artifacts, and never grants runtime authorization.

## Plan

Prepare version/changelog before build. Derive one exact four-output manifest from
the built Git trees and archive hashes. Make producer and release-event repair use
that handoff, reject mismatched existing tags and avoid selecting branch tips.
Reuse the existing changelog promoter and package build rather than adding a
second build or policy resolver. Document all four consumer tags.

## Failure analysis

- Branch tips advance before a release-event repair: resolve only recorded exact
  output commits, and compare their trees and versioned changelog to the manifest.
- An existing wrong tag is mistaken for an idempotent success: dereference and
  compare every existing tag before any missing tag is published.
- A partial tag push leaves a misleading release: one atomic Git push contains
  the complete requested ref update set; preflight all identities first.
- Prepared changelog differs across packages: compare source/prepared hashes and
  exact version headings before publishing anything.
- A corrupt or foreign handoff authorizes arbitrary tags: require exact schema,
  repository, source tag commit and all expected output names, and validate Git
  objects against recorded content. The handoff is trusted only as an asset from
  the authorized producer, not as an attestation against a compromised producer.
- Archive and tagged tree diverge: make archives from those exact output commits
  and record their digests; verify downloaded bytes before tag repair.
- A retry overwrites an already released artifact: existing manifest/asset/tag
  disagreement fails; mutable release branches are never a rollback identity.

## Peer review

Independent review will be requested from the existing Craft coordinator on the
exact PR head, with findings followed through directly on GitHub. No acceptance
is claimed before that review.

## Lead review

Keep changes bounded to release preparation, handoff and tag repair. Preserve the
accepted package runtimes. #1004 can consume the exact identities later; this
ticket does not implement activation, live host delivery or rollback by itself.

## Quantified claims

Fifteen disposable Git/manifest/archive scenarios pass, including a server-side
rejection proving atomic ref publication, moved branches, fresh source-only
checkout fetching exact objects, annotated tags, conflicting tags, corrupt
archives, uncommitted source inputs and Git export attributes hiding version
metadata. The original pre-composition matrix passed 79/79 commands; the final
combined matrix passed **81/81 commands** in 385.0 seconds on accepted develop
`682a66866d1956f789945bf5f3bd5f2e73a9d309`: 25 Python modules, 36 hook suites,
two workflows, both builds and all reference/freshness checks. Log:
`/tmp/cc-852-integration-validation.log`. Hosted checks and independent exact-head
acceptance remain pending at publication.

A separate canary cloned the public source into a temporary repository, committed
the candidate snapshot there, prepared synthetic version v99.0.0, ran the full
build, staged all four actual output trees using the workflow's orphan-worktree
commands, recorded/verified all archives, and published/repaired against a local
bare remote. It passed again after integrating #1001 and the export-attribute
check. Logs: `/tmp/cc-852-real-build-canary.log`,
`/tmp/cc-852-real-build-output.log`; synthetic receipt:
`/tmp/cc-852-real-build-manifest.json`. This is local artifact proof, not an actual
GitHub release or live installation. YAML syntax validation also passes.

The producer preserves its handoff as a workflow artifact before remote mutation.
Tag repair is idempotent and rejects conflicting existing targets. Full producer
reruns retain the existing version-allocation behavior; they do not overwrite
published tags or assets. A failed release creation leaves the saved handoff for
explicit recovery. Releases predating the manifest do not receive a guessed
branch-tip fallback. The producer continues to run only on main pushes and now
skips bot pushes at the job boundary, preserving their prior no-release behavior.

## Validation and rollback

Exercise the helper against disposable local bare remotes and built fixtures,
including moved branches, wrong/missing objects, bad digests, wrong versions,
conflicting tags and idempotent retries. Run workflow/source-policy and repository
regressions. A failed prepare/verify must leave the remote untouched. Revert the
reviewed change through normal develop workflow if a regression is discovered;
never repoint an existing published consumer tag.
