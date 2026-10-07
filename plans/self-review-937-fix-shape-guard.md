# Self-review — fix-shape-guard merge-base freshness (CCP#937)

## Assumptions

Working as: software engineer, tech lead
Goal source: #937
Pre-author-inventory: #937 — investigated fix-shape-guard.sh line 60: `merge-base develop HEAD || merge-base main HEAD` uses the LOCAL develop ref, which in this workspace is ~517 commits behind skills-upstream/develop, so MERGE_BASE..HEAD spans unrelated upstream commits and inflates the scope-count. Confirmed no dedicated test file existed.
Investigate-artifact: #937
Pre-mortem-artifact: #937
Project-contribution: Stops the scope-repetition guard from false-blocking legitimate single-commit branches in this workspace (it fired 3x this session on feat/931/933/935), so the gate measures the real branch delta instead of stale-local-pointer drift.

Key assumptions:
- The intended metric is "commits on THIS branch since it diverged from the integration branch." The freshest reachable develop approximates that better than a stale local pointer. Verified against the guard's own rejection wording ("N commits on this branch share scope").
- Choosing the merge-base with the fewest commits to HEAD across candidate refs selects the freshest integration ref. When local == remote the merge-base is identical, so correctly-based branches are unaffected.

## Peer review

- **writing-tests:1 (red on revert).** AC1 (1-commit feature branch atop a fresh skills-upstream/develop that is 3 same-scope commits ahead of a stale local develop) passes (exit 0) under the fix. Revert to the old single-line merge-base and AC1 reddens: the old logic counts c0..HEAD = 4 commits with 3x fix(core), trips the scope threshold, and blocks (exit 2). The red-on-revert is structural, not incidental.
- **writing-code:7 (no silent swallow).** The loop skips a ref only when it does not resolve or yields no merge-base/count; it never swallows an error into a wrong answer, and the `if [[ -z "$MERGE_BASE" ]]: exit 0` fail-open is unchanged.
- **Behaviour preservation.** AC2 (genuine 3 same-scope commits ahead of the fresh develop) still blocks; AC2b (same cluster + Class-Audit) passes; AC3 (local-only repo, no remote ref) still blocks a real cluster. So the fix narrows ONLY the stale-pointer false positive.
- Gate 1 (syntax): `bash -n` on hook + test -> exit 0.
- Gate 2 (tests): `bash hooks/_test/fix_shape_guard.test.sh` -> 4 passed, 0 failed.
- Gate 3/4: N/A.

## Lead review

- **As tech lead:** the change is localized to merge-base selection; downstream scope/file-overlap logic is untouched. Candidate order lists remote develop/main before local so remote wins on ties-by-count only when it is genuinely fresher (fewer commits). `master` added to the fallback list for master-default repos.
- **Pre-mortem (focused):** Tiger — picking a WRONG (too-recent) merge-base and under-counting a real cluster. Mitigated: the min-count ref is by construction the closest common ancestor reachable, which is the true branch point; a real N-commit cluster ahead of the freshest develop still counts N (AC2 proves it). Paper Tiger — a repo with neither develop nor main: handled by the unchanged `if [[ -z "$MERGE_BASE" ]]: exit 0`. No launch-blocking risk.
- **As software engineer:** AC1 encodes the exact false positive from this session (the 44-count block on a 1-commit branch) so the regression is locked.
- No AI/assistant attribution anywhere.

## Quantified claims

- **4 scenarios pass, 0 fail.** Evidence: suite output "Results: 4 passed, 0 failed".
- **1 merge-base selection block replaced** (single-line -> freshest-ref loop); downstream logic unchanged. Evidence: the diff.
- **2 files changed** (hook + new test). Evidence: `git status -s`.
