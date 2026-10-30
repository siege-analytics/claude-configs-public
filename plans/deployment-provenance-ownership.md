# Deployment provenance and settings ownership

Goal source: operator-authorized completion of the historical audit findings,
2026-10-29, delegated by the coordinator. Related contracts: #821, #852, #1038.

## Investigation and design

The audit reproduced a dirty tracked hook being installed and verified while
the stamp named clean main. `validate_deploy_source` compared commit labels,
but `deploy_to_workspace` consumed mutable working-tree bytes. It also reproduced
`install-hooks.sh` deleting an unrelated absolute operator command because its
last path components resembled a managed native hook.

Selected design: preserve the exact-main policy, compare tracked source bytes
and executable modes with that commit, then build and deploy from a private
immutable Git-object snapshot. Recheck original main before activation and
before writing a stamp. Verify copied artifact bytes before that stamp. This
is artifact verification, not a claim that a host invoked its hooks. The
existing installer still owns settings wiring and full enforcement probes.
Reject overlapping source/target paths before mutation. Legacy repositories
without the merge-then-deploy policy retain their previous behavior.

Alternatives: a plain `git diff --quiet` misses index flags and file-mode
configuration; a working-tree check alone leaves a check/copy race. Reusing
`source_snapshot.git_files` makes Git objects the source of deployed content.
There is no claim of an atomic multi-file installation or a new rollback
protocol; failed partial activation invalidates the old stamp.

Ownership design: supported relative commands resolve against the declared
hooks root. Absolute commands and aliases must physically resolve within the
managed native directory before retirement. Preserve foreign commands, their
metadata, and first-occurrence ordering. Remove only exact duplicate managed
registrations from the source settings file.

## Pre-mortem

- A mutable source could change after validation: private snapshot content,
  frozen builder/runtime, and pre/post source checks prevent certifying it.
- A tracked FIFO or symlink could hang validation: nonblocking no-follow reads,
  regular-file checks, and bounded byte reads reject it.
- A target inside the source could replace authored content with generated
  files: canonical source/target overlap is rejected before build/activation.
- A copy or source check could fail after partial activation: do not issue an
  authority stamp, and invalidate the previous stamp after any attempted copy.
- An operator command could resemble a managed basename: resolve ownership
  before retirement; regression fixtures keep foreign absolute paths and aliases.
- Legacy source fixtures could become unusable: apply strict source validation
  only after the committed/remote merge-then-deploy policy is established.

## Verification plan

Cover unstaged/staged/deleted/mode/suppressed-index edits, ignored/untracked
controls, source/target aliases, frozen snapshot behavior, failed activation
stamp invalidation, foreign hook preservation and managed retirement. Run the
affected deployment/native/settings fixtures and build checks. The coordinator
will integrate and refresh shared generated catalogs once.
