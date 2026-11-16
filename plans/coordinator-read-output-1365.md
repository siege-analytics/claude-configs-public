# Coordinator read/output regression

Task: siege-analytics/claude-configs-public#1365

## Assumptions

The captured native WC refusal was a preexecution status-guard decision, not failed GitHub execution. The exact sanitized tool_input command hashes to 0bd1b42dab578b565f0f3e1a3973b070a302c1e13a3b5aa1a8ac86f1bb8ca1b3. An isolated admission fixture reproduced exit2 and the identical failure-reason message; its gh trap was never invoked. The actual command was never executed or replayed on the remote host.

Read coordinator-status-guard, task_actions.shell_tokens/_wrapped_command/released_read_verdict, the canonical reader grammar, and existing status/mechanical tests. A file redirection makes the aggregate action non-read-only; legacy first-gh path inspection then mistakes GET receipt paths/status fields for a post. The fix retains actual command bytes and delegates filesystem/Task authority to UMG.

## Test plan

The exact captured sanitized input now admits at final hook SHA af53df0a609b176a1a834144929553375bff04285610c5b3e323c8b3249a2bc9 with exit0 and no gh invocation. Both results used a controlled fixture cwd and Bash PreToolUse envelope, not an asserted copy of unsanitized live SDK metadata.

Maintained coordinator_read_outputs: six methods PASS3.442s. They cover default/explicit/clustered GET, eight status-like receipt paths, jq fields, quoted operation data, descriptor duplication, literal output, opaque/glob/tilde/substitution refusals, later close/reopen/POST/PATCH and supported wrappers, including depth33. The original code allowed GET followed by close with reason not planned, or POST body=hello, with exit0; the candidate denies2. This is an old hole closed by the mixed-operation check, not merely preservation of a presumed earlier denial.

Existing mechanical completion suite:31 tests PASS51.977s with its controlled GitHub transport. Existing coordinator-status entrypoint:80 passed/0 failed, including its existing metadata corpus; the outer unexpected-gh trap was never invoked. Normal build/inventory/source-authority generation and reference/build/inventory/authority checks passed. Raw results are in instruction-refactor-evidence-20261104/core1365-status-get-regression-20261113.

## Findings

The proof replaces only supported literal stdout/stderr file destinations with /dev/null in memory, preserves real operators/quoted data and uses the canonical whole-command reader verdict. It never rewrites or executes the user's command. Every chain member must pass; filesystem ownership remains independently enforced by UMG.

Root review found the first implementation missed gh behind supported timeout wrappers. Shared effect-wrapper unwrapping now detects that executable, without using the unwrap as a reader/permission proof. Before freeze, a real depth33 probe exposed an arbitrary32-iteration silent drop; the input-length bound removes it and the regression is permanent. Unknown wrappers/options are not newly authorized. Unproven multi-GitHub operations must be split into separately checked calls under their existing grant, not a new operator approval.

## Independent review

External Root inspected the successive actual diffs and independently reproduced the timeout counterexamples. On the final af53df0a hook it confirmed exact captured input0/noGH and depth33 later-close2 in both orders/noGH, reviewed the source-length bound, and reported no additional source blocker. Its earlier six-method PASS3.427s belongs to the prior hash and is retained only as historical evidence. The final six-method PASS3.442s above is the author's run. Root inspected the final production/tests/inventory diff and actual broader results, reported no unresolved P1, and posted its independent source review at https://github.com/siege-analytics/claude-configs-public/issues/1365#issuecomment-6847980270. Final PR review will also be posted directly on the published head.

This record claims source/admission-fixture behavior only, not installed-source delivery, hosted CI success, live API result validity or mission completion. No runtime/Main mutation or gate bypass is included.

Final staged scan completed with exit0. The genuine unbound three-source test-evidence producer reran the six maintained methods at final bytes: PASS3.101s.

## Hosted dependency-pin follow-through

Hosted run43393770993 failed the maintained helper invocation-site digest. Comparing actual site sets against b030 proved one added executable import, `from git_command import literal_prefix`; no removed sites or changed dependency edges. Updated the exact digest to e219f469593464d6bf79b47cf05d86e623e6bed72cc52b2af2c2bebaefdf3604 and the coordinator-to-git_command invocation count from one to two. All existing dependency removal/duplication falsification controls remain unchanged. The production hook remains af53df0a609b176a1a834144929553375bff04285610c5b3e323c8b3249a2bc9.

The complete local hosted risk step passed: review_risk_test.py PASS, review_risk_policy.test.sh 13 passed/0 failed, and review-risk-metrics.py --check current. A separate dependency-graph run also passed its removal/duplication controls. Official reference/build/inventory/source-authority checks passed without generated changes. These local results do not claim hosted acceptance.

Root independently recomputed the one added site and its count, and confirmed removing or duplicating it is rejected. The staged repair scan completed with one inherited finding at review_risk_test.py:487: its unchanged SyntaxError handler cannot establish a helper chain, so the caller's missing-edge/digest checks fail closed. The maintained malformed-source regression and full dependency tests passed. This is not a clean scan claim.
