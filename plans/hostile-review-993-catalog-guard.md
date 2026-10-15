# Hostile review: issue #993 catalog guard invocation classification

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/993

## Review target

Final working tree relative to merged `origin/develop` at `f97d194fedf1eda053a16e938851c6151f308d72`, covering:

- `hooks/infrastructure/catalog-guard.sh`
- `hooks/lib/classify-catalog-command.py`
- `hooks/_test/catalog_guard.test.sh`
- the narrow F4 Tier C policy, graph audit, metrics, and audit documentation changes.

## Reviewer prompt

Find one concrete bypass or false block at a time. Supply an exact classifier input and expected/actual result. Challenge pipelines, compound lists, wrappers, xargs, shell/Python payload boundaries, kubectl stdin forwarding, heredocs, here-strings, substitutions, file-descriptor precedence, process substitutions, literal producer/consumer flow, malformed input, extraction controls, fail-closed dependency behavior, and the F4 Tier C dependency boundary. Return `ACCEPT` only when no concrete finding remains.

## Rework summary

The hostile loop rejected successive candidates for concrete dataflow and precedence gaps. Every valid finding became a regression before re-review. Classes fixed included:

- cat/tee pass-through and xargs literal/template execution;
- left-to-right stdin/stdout redirection and fd-specific overrides;
- heredoc/here-string, fd duplication, and cross-fd payload promotion;
- input/output/nested process-substitution flow;
- inherited stdin through shell `-c`, compound lists, and downstream pipelines;
- bounded stdin-consumption state through nested inline/process script paths;
- inherited heredoc documents and process-substitution script output;
- kubectl stdin forwarding and Python/shell source precedence.

One proposed stdout-to-stderr false block was reproduced against the current candidate and shown invalid (actual exit 0); it was nevertheless retained as a passing regression.

## Published-review remediation

Review `5529528446` on published SHA `3abbcf741b641e7f2a172173258f9db1bc18a430` identified recursion, utility-wrapper/eval, and literal-`#` gaps. Review `5530995977` then identified an AWS streaming-upload operand shift through `--expected-size`. All findings were reproduced before repair and became block/pass regressions.

Independent exact-SHA reporter review `5531747431` subsequently **rejected** frozen SHA `415e1262baabad38af36a64bcd1311a03c149142`. Its R1–R6 commands all reproduced through exact/nonempty extraction, the raw classifier, and the full hook:

- R1: clustered shell `-o` values (`bash -euo pipefail -c`), including kubectl wrapping;
- R2: imported/aliased Python executors, literal/split argv, and `os.exec*` payloads;
- R3: executed Spark writes in callbacks, lambdas, methods, plus `-W`/`-X` values containing `c`;
- R4: `${#...}` and brace/parameter words containing literal `#`;
- R5: ANSI-C escaped quotes and arithmetic `<<` misread as heredocs;
- R6: AWS `--cli-binary-format` value operands before or within `s3 cp`.

The remediation used explicit shell lexical state and bounded Python AST binding/execution state. Follow-on hostile review found additional statically knowable aliases, argv composition/parameters, class/instance overrides and restoration, constructors, `foreachBatch`, imported/shadowed `exec`/`eval`, contextual execution state, chained writer methods, and named expressions. Every valid exact command was first reproduced, then added with a blocking or non-blocking control. One alleged aliased-module shadow false positive was falsified locally and not used as a mutation reason.

Fresh CodeRabbit exact-SHA analysis then **rejected** replacement SHA `90997cc4781a1a745d31afb21715d1f5220b0f5e`: `os.execv(path, argv)` was classified from attacker-controlled `argv[0]` instead of the executable `path`, so an AWS path plus an `echo` decoy passed while the path executed. The finding reproduced with exact/nonempty extraction, raw-classifier exit 0, full-hook exit 0, and a controlled executable stub.

The repair now models the whole bounded class using Python's actual `os.exec*` signatures: executable identity comes from path/file; `argv[0]` is discarded as a process-name decoy; trailing `execle`/`execlepe` environments are excluded; static string/byte paths and vectors are supported; and literal, assigned, function-bound, wrapper-call, vararg, and split-vector expansions retain static sequence state. Each follow-on command was reproduced through extraction, classifier, hook, and controlled execution before mutation, received a paired block/pass regression, and the final bounded hostile pass returned **ACCEPT**. An out-of-policy `aws s3 rm` example was not accepted as a finding; its corrected managed `s3 cp` shape was reproduced and fixed.

## Final verdicts

All acceptance verdicts predating a later finding are superseded. The final complete working-tree review after the last behavioral change returned **ACCEPT** and explicitly confirmed that the classifier parses input as data and never executes or evaluates it. No valid finding is waived.

## Final evidence supplied to reviewer

- Focused catalog suite: `398 passed, 0 failed`; this preserves all former `364/364` and `290/290` cases and adds the exact-SHA `os.exec*` rejection/follow-on regressions.
- Full-hook extraction control: `369/369` exact and nonempty.
- Reconstructed issue matrix: current `20/20`; extraction `20/20` exact/nonempty. Historical authored-base evidence remains `10/20`; the independent reporter reconstruction recorded `7/20`.
- Deterministic malformed fuzz: seed 993; 500 classifier cases repeated twice plus 100 full-hook cases; 100/100 exact nonempty full-hook extractions; exits exactly 0/2; zero tracebacks.
- F4 authoritative risk suite: `review_risk_test: PASS`, including direct, modification, deletion, rename-source, and declared-B rejection coverage for the classifier.
- Full current-develop validation: `18/18` Python fixtures on Python 3.13 (hosted CI uses 3.12), `36/36` hosted-equivalent non-publishing gates, and all `37/37` hook suite files passed.

## Canary and rollback

Canary: both `dist/claude-code` and `dist/craft-agent` package copies block direct, `--expected-size`, string-`os.execv`, and byte-vector-`os.execv` managed-bucket copies with exit 2, allow quoted grep prose with exit 0, extract all ten commands exactly/nonempty, and classify the helper as valid Tier C.

Rollback: revert the isolated issue #993 implementation commit. Do not force-push, weaken to a direct-copy-only allowlist, deploy, install, release, merge, or affect `main` as part of rollback.
