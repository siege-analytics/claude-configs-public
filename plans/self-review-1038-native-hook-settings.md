# Self-review: native Git hooks in Claude settings (#1038)

## Observed failure

The v3.5.64 source snippet was clean, but merge-only installation preserved `hooks/git/pre-push-self-review.sh` under `PreToolUse:Bash` in the active workspace. The native script read ordinary tool payload as a push update and blocked every Bash action. User-level and workspace-level entries were removed surgically with backups; this patch prevents recurrence.

## Review boundary

- The first test run rejected an over-broad `hooks/git/*` retirement because canonical dual-use guards were removed and re-added out of order. That design is rejected. Classification now uses only current managed `pre-push-*` filenames plus exact `hooks/git` path segments.
- Existing symlinks resolving into the current managed native directory are classified.
- Unknown operator commands remain present.
- Empty/malformed commands fail before settings or Git config mutation.
- Native dependency and `core.hooksPath` logic is unchanged.

## Evidence ledger

The initial focused native suite failed idempotence under the rejected over-broad design; this falsification is preserved. The narrowed design passes all 19 native installer/push tests, including old-root, relative, symlink-alias, operator same-basename preservation, canonical dual-use guard retention, repeated-install byte stability, malformed-command no-mutation, and native deny/allow behavior.

Source and generated Craft `validate-hooks.py` pass 39 registered paths. Build, generated-source authority (198 sources / 804 snapshots / 2,916 mappings), skill inventory, review-risk metrics/tests, ontology (39 terms / 160 bindings), 24 package-selection tests, 14 selected-registration tests under one physical Python 3.11 interpreter, and all 36 hook suites pass.

Two harness failures are not product passes: system Python 3.9 could not parse supported type syntax, and mixed Python 3.9/3.11 public entrypoints correctly rejected different selected-registration interpreter identities. Replaying every entrypoint under one Python 3.11 resolved both without source changes.

The real workspace reconciliation passes deployed hook validation and the source verifier: zero Claude commands contain a managed `hooks/git/pre-push-*` reader, the canonical dual-use branch guard remains, ordinary `probe-ok` Bash runs, and native invalid/valid push probes deny/allow as expected. Live host injection remains unverified.

## Promotion review correction

CodeRabbit found that both scans parsed every hook as a command. Valid non-command hooks such as `type: prompt` have no `command`, so the accepted head could reject operator settings. The promotion was stopped. The additive correction retains non-command hooks during retirement, skips them during command-conflict matching, and adds repeated-install preservation coverage. Prior author and independent verdicts do not transfer to the replacement head. The corrected 19-test native suite passes with a preserved prompt hook across repeated installation. Source/generated validation, build and freshness, 14 selected-registration tests under one physical Python 3.11 interpreter, generated-source authority, review-risk freshness, and all 36 hook suites also pass.

## Lead verdict

Accept for independent re-review after the additive correction. The patch retires only pre-push protocol readers, preserves operator and canonical dual-use hooks, leaves native `.githooks` semantics intact, and passes source plus real-workspace replay.
