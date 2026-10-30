# Self-review: reader and protected Git safety (#1122, #1121)

Goal source: #1122
Plan reference: plans/read-and-protected-git-safety.md
Investigate-artifact: plans/read-and-protected-git-safety.md
Pre-mortem-artifact: plans/pre-mortem-read-and-protected-git-safety.md
Hostile-review-artifact: plans/hostile-review-read-and-protected-git-safety.md
Project-contribution: Preserve ordinary inspection while preventing write/executable options and Git spelling variants from bypassing policy.

## Assumptions

This is the operator-approved remaining-repair slice delegated by the coordinator, based on exact origin/develop d26317b. Disposable local repositories/outputs establish effects without touching consumer refs. Unsupported Git targeting/wrappers/aliases are unresolved, not authorized merely because a task exists. Existing explicit destructive escapes remain policy inputs; Authorized is parsed at the resolved target.

## Peer review

Independent source review identified forced wildcard, per-command targeting/include configuration and hook registration override gaps. Each was fixed and independently re-reviewed. The final seven-method regression suite was run independently and passed; the review artifact distinguishes integration from runtime acceptance. New helper source is Tier C; combined dependency snapshots remain a named integration obligation rather than a false local pass.

## Lead review

The changes use existing per-tool read classifiers and the existing literal shell tokenizer. No candidate/alias is executed during normalization. Branch/destructive policy is separate from workflow completeness. Scope resolution uses the same target boundary; a full implementing task does not waive protected operations. Lazy task_actions-to-git_command import avoids initialization recursion, but the modules remain coupled; keep the boundary explicit and test both direct-policy and mutation-resolution consumers.

Blanket pytest/py_compile early allowance was removed with coordinator approval. Test code/plugins can execute or write files; a typed scoped runner is separate integration work. Normal read-only JSON/AST inspection, base64 stdout decoding, literal reflog inspection and ordinary pipelines remain allowed. No live runtime deployment or real-consumer registration was performed.

## Quantified claims

- New safety regression: seven methods pass, including actual benign effects and deny-before-dispatch file/ref comparisons; independent re-run also passes.
- Existing read allowlist: 354 passed, zero failed.
- Existing destructive guard: 30 passed, zero failed, preserving existing explicit escapes.
- Fast-skip suite: 327 passed, zero failed. Branch Git aliases/global options take full inspection; ordinary reads still pass.
- Task-keyed suite: 58 passed, zero failed. Old tests asserting ungated pytest/py_compile were changed to explicit negatives, preserving unrelated read and diagnostic controls.
- Python syntax compilation and git diff --check pass. Tier C staged classification passes.

## Test plan

Coordinator integration must refresh combined skill inventory/review metrics and F4 invocation edges/hashes, then run full build, impacted source/package suites and hosted required checks before promotion. Keep the exact reviewed source and no-effect fixtures for final review. Install only clean separate exact-main input; live canaries and consumer registrations remain independently reported acceptance.
