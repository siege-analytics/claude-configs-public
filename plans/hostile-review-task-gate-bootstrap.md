# Independent task-gate guidance review

Reviewed 2026-10-29 in two bounded source rounds on branch `bugfix/task_gate_bootstrap`; exact source commit `b324824150c1ad91a7c3f78d940ca5c4eb4ad96f` approved against `origin/main`. Read the corrected recovery plan. Review-only; no source, runtime or user session changes made.

## Verdict: no must-fix findings in the revised scope

The initial guidance repair teaches the existing per-task contract and improves the actionable denial. The final amendment rejects unresolved templates but does not alter session identity recovery, path ownership, task selection, execution classification, status enforcement or effective review tiers. The new helper only constructs error text. Kernel and think guidance consistently require an own-session task, explicit identity and target repository scope, without inventing a hash or issue prerequisite.

The original experimental identity recovery and its tests are entirely removed. My earlier explicit-workspace consistency finding concerned that experiment and does not apply to the shipped diff. No speculative identity repair is required for this scope.

## Evidence and limits

The corrected plan accurately reports the live observations relayed by the coordinator: original deployed hooks permitted GA's own-task Write and bounded Bash mkdir. A literal shell environment value does not establish a failing hook callback identity. The plan now treats stale root-signal/hash guidance as the confirmed workflow problem, preserving that distinction.

Independently ran these five tests against the revised diff: all passed in 22.877 seconds:

- actionable unscoped-action bootstrap denial;
- independent report execution and designing task with plain slugs;
- own-session gate lifecycle end to end;
- own-session management cannot escape session or permitted signal shapes;
- workspace-root singletons never authorize or satisfy task requirements.

The earlier independent session-anchor suite also passed 13/13; session-anchor source is unchanged in the revised diff. No full-suite completion or runtime deployment is claimed by this review.

## Acceptance boundary

Source is suitable for promotion following the coordinator's broader required checks. Separately verify the installed guidance/denial version and the actual GA workflow through its effective tier. Successful task bootstrap alone does not prove successful report execution. Private-memory supersession and deployed registrations were outside this read-only source review.

## Subsequent bounded identity-safety amendment

Re-reviewed the additional five-line `session_id_from_env` guard and its regression on 2026-10-29. Verdict remains no must-fix findings. This guard rejects either unexpanded-template delimiter in any supported directory environment variable before converting that directory to an identity. It prevents the demonstrated synthetic `__SESSION_PATH__` shared-task/scratch authority and adds no discovery or recovery mechanism. This is a synthetic safety defect, separately justified from the unproven live GA callback hypothesis.

Independently ran the new template safety test plus denial guidance, plain-slug task independence, conflicting-payload precedence, and real-transcript host-directory cases: five passed in 5.446 seconds. The new test exercises all three directory variable names, pre-existing shared-gate mutation denial, shared own-signal Write denial, and ungated `ls` allowance.

The stricter failure behavior is intentional: any malformed directory binding disables environment identity resolution, including a lower-priority variable alongside a valid Craft directory or explicit environment ID. Repairing that malformed binding restores the established precedence; fallback is unsafe because `own_session_path` independently chooses a directory root. Existing explicit function `session_id` arguments and CLI `--session-id` remain trusted caller overrides; this check does not claim to abolish that API. The actual `--action-json` mutation path uses environment resolution and does not take such an explicit caller argument. No session-anchor source change or speculative workspace scanning is present.

The earlier proposed workspace-recovery CLI finding still does not apply: that feature remains removed. Final acceptance still requires the coordinator's full checks and deployment/UAT receipts.

## Exact source commit approval

Independent reviewer approved `b324824150c1ad91a7c3f78d940ca5c4eb4ad96f` against `origin/main`, with no must-fix. This follow-up corrects review-stage wording only; it changes no executable source or runtime policy.


## Kernel digest pin follow-up review

Independent reviewer approved the one-line verify-enforcement.sh pin update. All four packaged kernels independently hash to `1e94ede28fd98551f492ba275991393719e5d657f759113e960a555a031f78a4`, matching the new constant and kernel-budget catalog. The source-to-package change is reference resolution; nonempty regular non-symlink checks and the exact digest comparison remain intact. No weakening or must-fix finding.
