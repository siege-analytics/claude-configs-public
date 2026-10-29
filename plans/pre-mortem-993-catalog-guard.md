# Issue #993 catalog guard pre-mortem

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/993

Exact reproduction base: `0bae4ff108de5ad3b339a868818b05ea1e7c70bd`

Develop reconciliation: `origin/develop` was merged without force at `f97d194fedf1eda053a16e938851c6151f308d72` after hostile acceptance and before publication.

Integration boundary: draft pull request from `fix/993-catalog-guard-invocation` to `develop`. No merge, ready-for-review transition, main/release branch operation, deployment, or installation.

## Failure modes considered before implementation

1. **Quoted prose is treated as execution again.** A parser that only removes quotes still cannot distinguish `python3 -c "..."` from `grep "..."`. Mitigation: first classify each executable invocation, then apply write patterns only to programs that execute visible payloads. Negative tests cover grep, git messages, editors, and non-executing heredoc consumers.
2. **Pipeline position recreates the first-token blind spot.** Checking only the leading program misses an executor or object copy in a later segment. Mitigation: classify every top-level pipeline/control-list segment and recursively inspect command substitutions and payload executors. Tests place dangerous and harmless text in multiple segment positions.
3. **Wrapper handling over- or under-skips arguments.** `env`, assignments, `sudo`, and `xargs` can hide the effective program; careless skipping can interpret an option value as a command. Mitigation: bounded, explicit option handling with no `eval`, no shell execution, and adversarial wrapper tests.
4. **Heredoc content is parsed as independent shell commands.** A documentation or patch heredoc could contain a line beginning with `aws` or Python write syntax. Mitigation: extract heredoc bodies before segmenting. Inspect a body only when the owning invocation is a visible-payload executor such as Python or a shell.
5. **Malformed shell syntax creates a new false block.** Approximate parsing of unmatched quotes could classify prose as executable. Mitigation: fail open for syntactically malformed segments because the shell itself cannot execute them; keep already balanced command substitutions separately testable.
6. **Command substitution hides real execution.** Looking only at the outer `echo` or `grep` misses active `$(...)` or backtick payloads. Mitigation: recurse into substitutions that are active outside single quotes, without evaluating them; leave single-quoted substitution text literal.
7. **The direct-copy fix narrows the existing conservative direction policy.** Argument-aware parsing might accidentally block only writes and allow reads from managed buckets. Mitigation: preserve direction-blind matching for `aws s3 cp|sync` and `mc cp|mirror`; test both local-to-managed and managed-to-local forms.
8. **Tests report success while command extraction is empty.** A copied hook without `hooks/lib/extract-json.py` allows all inputs. Mitigation: full-hook fixtures independently decode the JSON and assert the command is nonempty before checking exit status. Classifier unit coverage accepts raw command input and therefore does not depend on JSON extraction.
9. **The library works but the installed consumer does not use it.** Mitigation: test both the raw classifier source and `catalog-guard.sh` as the JSON-consuming hook, and run source-authority/build validation plus the full repository suite.
10. **A fail-open helper error silently disables enforcement.** Mitigation: make classifier invocation errors nonzero and have the shell consumer propagate them; include malformed-but-valid input tests and shell syntax/static checks. Rollback is the isolated issue commit if unexpected consumer breakage appears; do not roll back to a direct-copy allowlist-only patch.
11. **The new decision-changing helper is misclassified below Tier C after F4.** Mitigation: add only `hooks/lib/classify-catalog-command.py` to the existing helper regex, audit its exact assignment/execution edge, and exercise direct, staged modification, deletion, rename-source, and declared-B rejection shapes.

## Intended evidence

- Before/after matrix with a separately asserted nonempty extraction control.
- Focused positive and adversarial negative tests for pipelines, wrappers, payload executors, heredocs, quoted prose, malformed quotes, substitutions, and direction-blind object copies.
- Independent hostile review of the final diff and focused evidence.
- Tier C full-suite result after the last code change, plus canary and rollback notes.
