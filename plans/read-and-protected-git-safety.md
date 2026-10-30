# Reader safety and protected Git normalization (#1122, #1121)

Goal source: #1122
Plan reference: plans/read-and-protected-git-safety.md
Investigate-artifact: plans/read-and-protected-git-safety.md
Pre-mortem-artifact: plans/pre-mortem-read-and-protected-git-safety.md
Hostile-review-artifact: plans/hostile-review-read-and-protected-git-safety.md
Project-contribution: Make exact operation effects, rather than a program name or workflow artifact, determine read exemption and protected Git policy.

## Context and authorization

The operator authorized the remaining repairs after reviewing the remediation plan. The coordinator explicitly delegated P0.6a/P0.9 implementation in an isolated worktree, including the Darwin base64 output, GNU cp abbreviation, textconv execution and global Git option bypass findings. Base origin/develop: d26317b15c8803d972efe9dff2fde144aedf8908. Live runtime trees and real consumer registration are outside this source slice.

Issue #1122 records actual foreign writes for cp/base64 and configured-helper execution for textconv. #1121 records falsely blocked literal reflog inspection. Their bodies and comments were read before implementation. The current base still contains these shapes: base64 in unconditional PLAIN; cp exact output-option matching; missing --textconv in the first classifier; branch/destructive triggers looking for adjacent git and verb.

## Design and alternatives

Retaining regex-only Git matching cannot resolve repeated directory options or aliases. Duplicating option handling in every guard would multiply the bug class. The selected design is one bounded literal Git boundary reusing task_actions.shell_tokens, with non-executing alias queries, shared by operation guards and mutation target resolution. It does not execute a candidate or infer permission for unresolved shell aliases. Existing explicit destructive waivers remain explicit; Authorized trailers are read at the resolved target.

Reader changes stay in the existing per-tool classifiers. Base64 is guarded by an explicit Darwin/GNU option grammar; output forms and unknown options are not reads. Textconv execution receives a veto. GNU cp output directory/suffix abbreviations use the existing long-option matcher. A sibling audit found hostname setters in the fallback unconditional list; only no-operand query flags remain readers. Arbitrary pytest modules and py_compile are removed from early diagnostic authority. The isolated Python JSON/AST read grammar remains, while a future scoped runner is separate work.

Literal reflog show inspection and ordinary filter pipelines remain permitted. Reflog expire/delete/drop/write remain mutations. No broad interpreter or shell-script exemption is added.

## Blast radius and evidence

The classifier and task_actions have high fan-out through universal-mutation-gate and resolver callers. Their public result/exception shapes remain unchanged. Git normalization is used by branch-guard, destructive-guard and task_actions mutation targeting. Old non-Git destructive patterns and branch script checks remain in force.

Regression fixtures use disposable repositories, a local bare remote and benign output/marker files. They prove the original effects are real, then exercise deny-before-dispatch and compare files/refs. Protected operations are checked with a valid implementing task; task authority must not override operation policy. Feature commits and explicit feature pushes are positive real-effect controls. No live destination is contacted.

## Scope limits

This slice does not claim real-consumer native registration, provider branch protection or the complete backend matrix. Unsupported global options/wrappers and shell aliases have an explicit unresolved-operation diagnostic. It does not rewrite candidate commands or certify arbitrary Git configuration as free of executable helpers. Native registration and the typed test runner remain separately owned coordinator work.
