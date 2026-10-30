# Self-review: deployment provenance and ownership

Domain: software engineering
Goal source: plans/deployment-provenance-ownership.md
Goal source verification: direct operator repair authorization recorded in the
design before implementation; historical contracts #821, #852 and #1038 verified
against the coordinator's collected issue bodies and temporary reproductions.
Plan reference: plans/deployment-provenance-ownership.md
Investigate-artifact: plans/deployment-provenance-ownership.md
Pre-mortem-artifact: plans/deployment-provenance-ownership.md
Hostile-review-artifact: plans/hostile-review-deployment-provenance-ownership.md
Project-contribution: the revision named by a deployment stamp now supplies the
actual activated bytes, and cleanup cannot silently remove a foreign hook.

## Assumptions

- The entrypoint Python/Git toolchain is trusted. Do not extend that trust to an
  unchecked checkout helper: its accepted Git blob supplies the snapshot reader.
- The committed merge-then-deploy policy remains sticky. Legacy unmarked source
  behavior remains compatible, rather than silently adopting a new policy.
- The existing copier is not an atomic multi-file transaction. Its stamp is
  invalidated before writes; failure does not certify a mixed generation.
- A private accepted snapshot is the source of activation. Convenience dist
  outputs are not read by activation. Literal-object reads disable replacement
  refs and ambient repository/index/object routing.
- No global/user Claude settings may be modified: another authorized session is
  editing them. This slice changes only source settings in an isolated worktree.

## Peer review

A separate review-only agent examined the current implementation and ran
independent fixtures. The durable report is the hostile-review artifact above.
It approved the corrected source after identifying mutable-helper bootstrap,
hardlink aliases, special target leaves, and output-path preflight concerns.
This was a separate agent review, not a claimed cross-provider review.

## Lead review

Reworked the bootstrap to execute accepted reader bytes, not a dirty sibling.
Added literal-object Git semantics, raw tracked byte/mode checks, immutable build
and copy sources, physical target checks, pre-copy stamp invalidation and post-copy
artifact checks. Static target symlinks, hardlinks, FIFO/device/socket leaves and
non-directory parents fail before writes. Source/main are rechecked before copy
and before stamp. Artifact verification is explicitly separate from host UAT.

Foreign native-looking commands are preserved by physical ownership. The earlier
fixture that expected an arbitrary `/old/package/...` command to be deleted was
corrected to the explicit preservation contract in #1038. Genuine relative and
resolved managed aliases still retire. Source settings keep the first matching
registration and remove eight exact duplicates; validation no longer hides them
by comparing sets alone.

No unresolved blocking finding remains in the independent scoped review. The
coordinator owns final integrated CI, exact-main promotion, rollback backup and
live installation; this local slice does not perform or claim those stages.

## Quantified claims

- `deploy_source_policy_test.py`: PASS after final fixes. Exercises three actual
  private builds: successful immutable activation, original-source mutation after
  copy, and deliberately corrupted installed bytes. Negative controls include
  staged/unstaged/deleted/mode/index-flag changes, dirty-reader side effects,
  replacement refs, ambient Git routing, source/target/output overlaps and aliases,
  hardlinked settings, FIFO leaves and non-directory parents.
- `native_push_test.py`: 20 tests passed, including foreign absolute/native-shaped
  commands and symlink aliases with operator metadata and reinstall idempotence.
- `settings_drift_test.py`: 12 checks passed, including duplicate registration
  entries and repeated matcher groups.
- `selected_generation_test.py`: 13 tests passed, exercising generation consumers
  of the shared source snapshot interface.
- Full build and build `--check`: PASS. Source hook validation: 45 hook paths valid,
  with existing unreferenced-hook warnings. `git diff --check`: PASS.
- Shared generated catalogs are intentionally left for one coordinated refresh
  after integration. Full integrated CI is a later coordinator acceptance stage.

## Test plan

The affected tests above cover the observable failure classes. The final
integration must additionally exercise generation/selection consumers of the
shared Git snapshot reader and the normal installer against a separate temporary
workspace. No source worktree or user-global configuration is an install target.
