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

## CodeRabbit review remediation

Review `5529528446` on published SHA `3abbcf741b641e7f2a172173258f9db1bc18a430` identified three concrete gaps, all reproduced before repair:

- recursion limits did not fail closed with a dedicated reason through every path, including `_process_command_consumes_stdin`;
- `timeout`, `nice`, `stdbuf`, and `setsid` were not unwrapped, and `eval` payloads lacked execution context;
- `shlex` comment handling dropped mid-word `#`, including a managed AWS operand.

All three became hostile regressions. The hostile loop then found additional bounded static/dataflow cases involving executor substitutions, echo/printf escapes, Python/Spark AST writes, subprocess/exec/eval payloads, function/lambda invocation, callable aliases, and call-time closure bindings. Fresh exact-SHA CodeRabbit review `5530995977` found one further AWS streaming-upload operand shift through `--expected-size`; operand inspection was generalized and covered with block/pass regressions. Every valid finding became a regression; invalid syntax findings were reproduced and rejected rather than waived.

## Final verdicts

Parser/dataflow candidate after the original implementation: **ACCEPT**.

Frozen CodeRabbit-remediation candidate after the last behavioral change: **ACCEPT** from an exact post-change hostile completion. Earlier verdicts that produced subsequent findings are treated as superseded, not as acceptance evidence.

No valid finding is waived.

## Final evidence supplied to reviewer

- Focused catalog suite: `290 passed, 0 failed`.
- Full-hook extraction control: `277/277` exact and nonempty.
- Original 20-case matrix: base `10/20`, current `20/20`; extraction `20/20` exact/nonempty for both.
- Deterministic malformed fuzz: seed 993; 500 classifier cases repeated twice plus 100 full-hook cases; 100/100 exact nonempty full-hook extractions; only exit 0/2; zero tracebacks.
- F4 authoritative risk suite: `review_risk_test: PASS`, including direct, modification, deletion, rename-source, and declared-B rejection coverage for the classifier.
- Full current-develop validation: `18/18` Python fixtures, `29/29` CI build/check/package gates, and all `37/37` hook suite files passed.

## Canary and rollback

Canary: both `dist/claude-code` and `dist/craft-agent` package copies block direct and `--expected-size` managed-bucket copies with exit 2, allow quoted grep prose with exit 0, extract all six commands exactly/nonempty, and classify the helper as valid Tier C.

Rollback: revert the isolated issue #993 implementation commit. Do not force-push, weaken to a direct-copy-only allowlist, deploy, install, release, merge, or affect `main` as part of rollback.
