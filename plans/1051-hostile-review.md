# #1051 pre-commit hostile review evidence

Scope: bounded independent reviews of source snapshots before the implementation commit. This is **not** final exact-SHA acceptance. The coordinator must arrange the independent exact-SHA review after the draft PR is available.

## Initial findings and resolution

- **Opaque inline execution could escape declared targets.** Fixed: non-read inline execution is rejected when targets cannot be bounded. Regression: `test_hostile_review_opaque_and_nested_targets`.
- **Nested relative paths could escape task scope.** Fixed: canonicalize nested/option operands as mutation targets. Same regression; symlink, prefix and compound-target cases remain separately covered.
- **Identical no-ID spawns could reuse one reservation.** Fixed: unique PreToolUse reservations; no-ID PostToolUse matches a pending request signature and task, preventing double counts. Regressions: `test_same_arguments_without_request_id_cannot_reuse_reservation`, `test_fallback_reservations_reconcile_without_double_counting`.
- **Missing session identity could lend authority.** Fixed: mutation resolution requires a known runtime session. UUID-only payloads cannot select a wrong session directory; explicit diagnostics explain hook-host identity requirements.

## Follow-up reviews

The follow-up classification/administration snapshot reported: “No concrete bypass or normal-input bug found in the supplied snapshot.” It explicitly did not verify native test evidence or claim exact-SHA acceptance.

A focused identity/target-repo review reported: “No findings. The requested session-identity and repository-binding cases appear covered; I found no reproducible bypass or invocation regression in the reviewed changes.”

The final bounded source review covered `resolve-think-gate.py`, the real investigate/pipeline/think guards, the universal mutation gate, and the final acceptance tests, including the hook-host environment and removal of dummy missing-file fallbacks. Its result was: **“No findings.”**

## Evidence boundaries

The session-identity failure is described as **observed in the hook process, with live evidence pending from the Siege Utilities worker**, per the operator's latest correction. A resolver invocation in an agent shell is not evidence of hook-host behavior. The four identity regressions each exercise the real universal mutation hook and investigate resolver guard. The first three remove `CRAFT_SESSION_ID` and `CRAFT_SESSION_DIR`; the fourth deliberately tests the explicit directory override.

All executable changes remain clone-local. No live install, activation, deployment, release or shared-branch merge was performed. Final exact-SHA review remains pending and must not be inferred from this pre-commit record.

## Catalog dependency-chain follow-up review

The complete generated diff for progressive-loading metrics and language/data fixture costs was independently reviewed before the follow-up commit. Result: “No findings. The diff changes only measured character/token counts and generated rules-bundle size; it does not alter source selections, expected states, budgets, limits, or assertions.”

This review is limited to that supplied generated diff; it does not claim CI execution or final exact-SHA approval. The implementation executables were not changed. Full validate-job replay is separately recorded after completion.

Reviewed generated-diff SHA-256: 248d940bcc1847ed847497db4ca339221583349bf225e176c678b16cc9c64564

## Independent round-one FAIL supersedes snapshot reviews

The coordinator's independent review of the substantive implementation at `cbbb975` found six functional merge blockers: self-gate lifecycle lockout; real-header hub liveness/task accounting; repo-wide Git ownership; unsafe reader forms; investigation regressions; and terminal gate ownership. Its seventh blocker was historical red CI, subsequently green at `c9cbbecc`, but new code must obtain new hosted green. None of the earlier snapshot “No findings” statements constitutes acceptance of these failures. The complete reviewer evidence is retained by the coordinator/reviewer.

Mandatory upstream integration: merged `6685879e` into the feature branch, retained both changelog contributions, regenerated every conflicted catalog using the merged generators (no hand-merged values), and ran the review-risk snapshot suite successfully. Required validation dependency PyYAML 6.0.3 was reused from the existing installation under Python 3.12; no product installation or activation. Full post-fix validation and exact-head review remain pending.
