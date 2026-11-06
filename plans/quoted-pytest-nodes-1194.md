# Literal quoted pytest node selectors

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1194, part of #1156. Parent dependency: reviewed #1185 at d4feed76905358a840993a899764d0969ec20209.

## Context

Part of #1156. Recent actual local CraftAgents enforcement still blocks a quoted parametrized pytest node ID before task lookup. Session `261105-prime-blossom`, tool `toolu_01CQHmgdQxuDuitWhbn3QQA7`, received `expanded mutation targets require explicit concrete paths` at 2026-11-05T07:50:52Z while using a quoted pytest node selection. The installed generation was f004df3c. Reviewed repair parent #1185 at d4feed76 retains this residual. No command or private report payload is published here.

Minimal source-only reproduction against d4feed76:

```sh
python3 -m pytest 'tests/test_demo.py::test_case[param]'
```

`task_actions.action` returns the same expanded-target error. Its shell tokenizer correctly reports zero unquoted glob positions. A later generic operand character check nevertheless treats the quoted `[` as shell expansion. This precedes task selection and cannot be repaired by supplying additional review artifacts.

## Goal

Preserve shell lexical provenance for literal pytest node selectors and the bounded sibling filesystem-operand class, while retaining real task ownership and review-tier enforcement. A quoted node ID is data; running pytest remains executable task work, not a reader exception.

## Acceptance criteria

- Quoted or escaped literal `::node[param]` selectors resolve without the false glob error, including the actual absolute-venv Python invocation family.
- The real hook still denies without task ownership, during designing, and for cross-task/foreign targets. Authorized own-task execution retains the existing applicable review tier.
- Unquoted globs, shell substitutions, opaque inline code and unsupported plugin/config execution do not obtain reader or investigation authority; their existing guarded classification remains.
- Recognized literal filesystem operand commands honor quoted brackets without expanding file scope; unknown opaque command families retain conservative handling.
- Tests distinguish actual shell glob metadata from literal bracket characters, observe real hook results and include negative controls. No blanket pytest exemption.

## Assumptions and design

Parent #1185 must integrate first; this branch starts at its reviewed d4feed76 head and does not change that branch or installed settings. Reuse `shell_tokens` provenance rather than remove all unknown-command safeguards. Restrict the quoted-operand relaxation to named filesystem operations and pytest invocation families; retain unquoted-glob rejection and unknown-executable behavior. Unknown pytest plugin/config options continue through existing task/risk requirements and are not certified read-only. No generic shell expansion evaluator, new policy engine or global approval state.

## Investigation and pre-mortem

Verified the actual local deny audit/source stamp separately from candidate classification. Tokenizer output has zero unquoted glob positions for the minimal and actual quoted selections; the generic operand character guard causes the rejection. Review-risk test execution is a later phase, so #1171 cannot fix this parser failure.

Tiger: treating literal syntax as an early allow could hide a second write or lower plugin risk. Keep the entire action mutative, preserve all targets and tier calculation, and test mixed foreign writes/unknown plugin flags. Tiger: removing generic character checks globally could open unknown opaque execution. Use a bounded family predicate, retain unknown-family denial, and test Python `-c` and arbitrary executables with bracketed arguments. Tiger: unquoted selectors might expand to extra files. Preserve the earlier lexical-glob rejection and test unquoted variants independently.

## Verification

Red-first classifier and real-hook fixtures, focused parser/task execution regressions, independent source/scanner review, real native content-bound test receipt and normal protected PR to develop. No duplicate complete local workflow or installation in this slice.

Git is excluded from the filesystem sibling relaxation: quoted Git pathspecs can still expand inside Git, so shell quoting alone does not prove literal Git operands. Tilde handling is unchanged.

## Assumptions

The parent repair generation remains a separate dependency and is not installed here. This parser change does not certify test execution as read-only, alter task scope, lower a review tier or validate arbitrary plugin behavior. Unknown reporter flags and absolute interpreter spellings retain their conservative tier calculation. Quoted tilde handling and Git pathspec interpretation remain outside the relaxation.

## Peer review

Root independently read the complete parser delta and seven-case fixture and accepted the bounded source/forward behavior before publication. The review keeps the original reporter's options conservative; only the impossible quoted-glob rejection is repaired. Final direct PR review and protected exact-head checks remain required.

## Lead review

The earlier shell-token glob-position rejection remains in place. The later text-character check now honors that lexical proof for named filesystem operations and pytest invocation families. Unknown executable families and Git retain the previous character check. No early allow, reader status or investigation allowance was introduced. All actual and potential output paths still participate in ordinary task selection.

Pre-mortem-artifact: plans/quoted-pytest-nodes-1194.md#investigation-and-pre-mortem
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1194

## Quantified claims

The seven-case red-first fixture produced three actual failures before implementation: literal pytest selection, the reporter's absolute interpreter/options shape, and the sibling quoted filesystem operand. All seven passed after the parser correction in 7.953 seconds. The fixture invokes real hooks, not pytest; its filesystem case also executes a real touch in disposable scratch. Existing execution-risk eleven cases and own-operand nine cases passed. Existing task-keyed regression execution passed all 77 cases in 180.109 seconds. Raw logs are retained under /tmp/quoted-pytest-1194-*. No complete workflow, installation or native backend success is claimed.

## Canary and rollback

Classify the original quoted selector through the installed own-task callback only after normal publication. The operation must remain denied without ownership or with a foreign output. Reverting this source change restores the previous conservative operand check. No settings, source gates or live sessions were changed here.

## Final source and scanner review

Root accepted the runtime/test source and the bounded fourteen-finding scanner disposition. Source SHA-256: task_actions.py 3dcd0e2586266d738c8e0d6f725a8cd5eb6a4ca84e08efc885a15ec63f0d5f2b; quoted_mutation_operands.py 66a33e91f026fb6f76186bd46a3259100ae5b94fb380077e12b59cedf421065a. The full selected scan completed nonclean with one code-7 return finding and thirteen test-locator findings; no lexical finding, ignore option or exclusion was used.

The caught ValueError/SyntaxError in _python_read returns False and declines reader authority. The test-locator findings demand pytest.raises for internally handled exceptions in a unittest/CLI suite. This convention mismatch does not prove every reported exception branch was raised. All ExceptHandler ASTs, including multiplicity, were compared against reviewed parent d4feed76 and are identical; the new literal-family helper introduces no exception handler or suppression. Root independently repeated that exact handler comparison.

| Current line | Finding | Enclosing contract |
|---|---|---|
| 220 | code-7 return; test locator ValueError/SyntaxError | _python_read declines reader proof on parse failure |
| 438 | test locator SubprocessError/OSError | _git_toplevel retains its unavailable result |
| 572 | test locator Exception | released_read_verdict retains its conservative verdict |
| 643,653 | test locator OSError/ValueError/TypeError | _test_receipt_record retains source-bound receipt checks |
| 709 | test locator OSError/ValueError | _metadata_file retains existing metadata evidence handling |
| 862,1133 | test locator UnknownShape | _action retains its explicit unresolved-target error |

Raw selected scan SHA-256: e69c2b4bb3a2e0713321038eb3dd3baf54ee3ed7e1847bcc6896d77e344af1b8. Runtime/test blobs remain unchanged during the evidence append; the final staged index is scanned again in source mode. No clean source scan is claimed.

Generated-source-authority initially reported only missing new-test references in skills-inventory.json. The normal inventory producer added seven fixture-path references; no other generated content changed. Generated authority, review-risk metrics, build check, full package build and source/both-consumer hook validators then passed. Native receipt production at the committed head and protected full CI remain required; no native receipt is copied from the parent.

Verified-by: Executed new quoted-operand hook cases, existing task/execution-risk/own-operand cases, exact handler-AST comparison, build/freshness and source/consumer validators; raw logs named above.
