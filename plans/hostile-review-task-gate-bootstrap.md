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


## Expanded task ownership follow-up

Configs review identified template-ID sharing, alternate-directory diagnostic mismatch and shared-shelf plain-ID pre-mortem borrowing. Independent Codex review of the corrections additionally found file/directory-link borrowing and then a shell-quoting regression. Both were corrected before source promotion. Final independent review: bash syntax passes, six targeted positive/negative cases pass (9.524s), and a fresh valid full-ticket repository-plan case returns allow. Descriptor-relative no-follow evidence reads require a regular single-link file and reuse the same content for identity/risk/launch checks. No remaining must-fix findings in the corrected diff. Full-suite and cross-model final-head receipts remain separate requirements.


## Final host-directory and identity review

Independent review approved central own-session directory derivation and transport from resolver output into artifact validation; tool input does not supply that binding. #831 plus five host/provenance/lifecycle cases passed. Final canonical identity amendment approved after fixture correction: six extended identity/transcript/precedence/alternate-directory tests passed in 12.859s. Known Craft slugs, UUIDs and alphanumeric fixture IDs retain identity; invalid values reject instead of colliding through sanitization. No remaining must-fix. Exact commit and full-suite receipts follow separately.


## Compact kernel follow-up approval

Independent review approved the concise kernel paragraph: own-session/task identity and scope, separate evidence, effective tier and fail-closed unscoped mutations remain explicit. Detailed bootstrap procedure remains in think and diagnostics. All four packages match pin `6796027e2ce6017c9f84a00eea52fcdf7cb80a18538d745bc14e6c11ad180d9f`. Independent load-set, progressive loading 20/20 (9664-byte large selection) and progressive mount checks pass. No budget relaxation or verifier weakening. No must-fix finding.


## Final R1 and placement independent approval

Independent review approved the complete invalid-host/native fallback boundary after reproducing and fixing its payload-only variant. Two complete tests pass (6.195s), including real guard denials for invalid env/payload bindings and preserved genuinely unbound native allowance. The helper recognizes identity/transcript payload forms without declaring arbitrary tool diagnostics bound. Placement wording and all four package hashes independently match verifier pin `556024416ac1d363597934f5cccc3152c5e8d86ef4116ee5a0a81b8a1748cc26`; no scope/tier, budget or integrity protection is weakened. No remaining must-fix in the reviewed source. Exact final-head and full-suite receipts remain separate.
