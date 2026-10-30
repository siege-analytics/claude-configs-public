# Task-scoped approval comment repair

Pre-mortem-artifact: plans/task-scoped-approval-comment-1139.md
Hostile-review-artifact: plans/task-scoped-approval-comment-1139.md

## Assumptions

The operator authorized routine PR work through its owning task. The documented structured approval comment remains a separate shared-resource acknowledgment. Parsing its inert final comment must never supply task identity, status, scope or artifacts. No shared-resource deny rule is removed.

## Pre-mortem

Discarding text after a comment could hide a later executed line. The accepted form fullmatches only a final one-line structured marker followed by blank whitespace. Missing/empty fields, ordinary comments, extra suffix text and subsequent commands stay rejected. Prefix substitutions and out-of-scope effects remain subject to existing parsing and task checks.

## Peer review

Independent task_gate_review accepted the exact narrow lexer diff. Its focused real-hook method passed in7.148s. An in-memory protected HEAD lexer rejected the documented form; current executable-prefix tokens were equal for touch, compound AND and redirection controls. No source revert or live configuration changes were used for that control.

## Lead review

The root focused real-hook method passed in7.472s. It composes the mutation and destructive guards for PR create/merge classification without executing GitHub. The implementing owner is admitted; another designing task, no scoped task, mixed out-of-scope writes, malformed comments, subsequent commands and substitutions are denied. Only parser syntax acceptance changes. Generated freshness checks passed after ordered refresh.

## Quantified claims

The focused method contains positive and negative guard decisions, not remote PR execution. The existing complete task/hub suite must rerun at the committed head, followed by protected CI and exact-main release/install. Earlier v3.5.80 runtime, GA and native-terminal acceptance is separate. No passing scanner claim or live GitHub mutation is inferred from these checks.

## Test plan

Run the full task/hub suite through the real source-bound evidence producer, retain the selected-source scanner result and review each finding, pass native push checks and protected CI, promote through develop/main, install exact main and test the documented approval in the original Craft session. Preserve unrelated tasks and existing user work.

## Selected-source scan

Complete selected-index scan exited1 with three findings; raw output is retained in plans/approved-pr-scan-output-1139.txt (SHA256 cfaab8b58bc9f5adb7bba497e7c5b27d962d32c134ba6834ff071fc6f3562941). Scanner executable/configuration are unchanged from main57fd875; no ignore modifier was supplied.

Independent review bound source blob3d4ebcba3cec9e6ba1c6ea0115de44e847db70bb (SHA2567ebb92520bc47eef382ae129158f173ddf6a5442944365fc7b62dbc2a6b4079f) and verified the relevant entire function ASTs equal accepted main:

- F23, line214: the Python-read parser returns False on invalid AST input; refusing to prove a read is its explicit error result, not swallowed failure.
- F24, line160: shape's offset is read by its generator closure; the own-scope-only scanner misses that capture.
- F25, line214: test discovery misses the actual hooks/_test suite; those resolver/real-hook fixtures exercise the helper.

These are individual inherited dispositions, not a count waiver. The scan is not clean. Independent receipt: approved-pr-scanner-independent-review.md retained privately with the run logs.
