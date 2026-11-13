---
ticket_refs:
  - siege-analytics/claude-configs-public#1371: pre-implementation artifacts with the design review posted (issuecomment-6850953261); PR closes it
  - siege-analytics/claude-configs-public#1372: class ticket for the merge-flag parsing defect; PR closes it
  - siege-analytics/claude-configs-public#1370: shared gh option parser (head e5c7dba4) merged into this branch; this PR depends on #1370
---
# Self-review: refuse an admin merge in every gh spelling

Task: siege-analytics/claude-configs-public#1371 (with #1372)
Review-Tier: C. This is enforcement runtime: `hooks/lib/task_actions.py`, `hooks/lib/github-merge-queue.py`, `hooks/lib/resolve-think-gate.py` and `hooks/bash/destructive-guard.sh`.

## Assumptions

Goal source: #1371, #1372 and #1207 AC3 ("any form with `--admin`" stays denied)
Working as: software engineer (enforcement hooks)
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1371#issuecomment-6850953261
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1371#issuecomment-6850953261
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1371#issuecomment-6850953261
Hostile-review-artifact: plans/hostile-review-1371-admin-refusal.md

### Sources consulted

These are what I actually read, and what each one established.

- **#1371 and #1207 AC3:** the required outcome. The canonical pinned CLI form and the GraphQL enqueue forms must keep working.
- **`hooks/lib/github-merge-queue.py` and `resolve_action` at develop `3154162a`:** the refusal was reached only through a literal `gh pr merge` prefix, and `merge_flags` had its own value-skipping rule.
- **`hooks/bash/destructive-guard.sh`:** it had no admin-specific refusal, and every one of its patterns can be waived.
- **#1370 head `e5c7dba4` (`task_actions.py`):** the pflag flag table for `pr merge`, the selector parser and `_gh_option_effect`. These are shared here, not duplicated.
- **`hooks/_test/github_merge_queue.py`:** the existing contracts. A body value of `--admin` is data, and an echo of it is ordinary.
- **cobra/pflag behaviour,** as recorded by the #1355 review (cli/cli v2.104.0): value flags take the next token; a short cluster ends in its value letter; leaf flags may come before the group.

### Scope

- **Changed:**
  - One shared predicate, `gh_merge_refusal`, called:
    - first by `resolve_action`, now a wrapper around the original body (`_resolve_action`), where a piped-program refusal is applied only when the gate would otherwise admit;
    - at the top of `parse()`;
    - by a new non-waivable destructive-guard block (helper protocol: 0 = clear, 3 = refuse, anything else falls back to text).
  - `merge_flags` no longer refuses on its own; it only selects pins for the canonical form.
- **Unchanged:**
  - the canonical queue exemption grammar;
  - GraphQL enqueue parsing;
  - `action()`'s models;
  - the tokenizer;
  - the other publication guards.

## Peer review

Shelf checks:

- **writing-tests (red before green, negatives pinned):**
  - The new `test_admin_merge_is_refused_in_every_spelling` was run against the pre-fix tree (develop `5c90061c` plus #1370; HEAD `ce4d34d9`). The source UMG admitted 33 of the rows from an owned cwd. These included every #1371 selector form, every #1372 cluster form, pipe and newline composition, and binary-name and whitespace variants.
  - With the fix, all 85 rows are refused by the UMG (exit 2), by the helper (exit 3) and by destructive-guard, even when a waiver marker or the waiver environment is present.
  - Rows without a pipe or heredoc also name the predicate in the UMG message ("Pinned merge denied: pinned merge queue: …"). Piped rows may first report the UMG's own, more specific refusal.
  - Allow rows (`test_queue_forms_admin_data_and_ordinary_commands_still_pass`): the canonical CLI with and without a selector, and both GraphQL forms, still pass the UMG and destructive-guard and write their audit rows. Data and ordinary rows stay clear.
  - Failure protocol (`test_guard_refusal_survives_a_missing_or_broken_helper`): with a missing, syntax-broken, import-failing or faulting helper, `pwd` still passes and admin forms are still refused.
- **Contracts:** all 24 pre-existing tests in `github_merge_queue.py` pass unchanged, including the `--body "--admin"` and echo contract.
- **Generators:**
  - `bin/build.py` succeeded with the pinned PyYAML venv.
  - `--check` passes for build, skill-inventory, generated-source-authority, sync-skill-references, kernel-budget and review-risk-metrics.
- **Full suites:** all 88 `hooks/_test/*.test.sh` were run on the final code bytes, from a scratch runner with the PyYAML venv on PATH and host-session variables stripped (finished 09:08 CST). 87 exited 0. ca_enforcement_runtime exited 1 with its known baseline of 12 passed / 4 failed; its test file is unchanged by this PR, and it is not claimed green.
  - An earlier full run caught the ssh stdin-script regression, now fixed.
  - Another run was cut short by a host time limit. The suite that was running when it stopped (ticket_required) passed on its own in 98 s.

Findings, all fixed before publication:

- The design review (ACCEPT WITH CHANGES) found tokenizer whitespace, wrapped invocations, helper exit codes, renamed binaries and aliases.
- The code review (REQUEST CHANGES) found argument-supplying wrappers, shell scripts and eval, shell aliases, unparseable text, the fallback pipe and fault handling.
- Code-review rounds 2-7 found wrapped and stdin-fed program runners, runner and wrapper lists, option-letter case, and the admission mirror.
- The full suite caught one regression in the allowlisted-ssh stdin-script shapes; it is fixed and was re-run.
- All of these reviews are in the hostile-review record.

## Lead review

- **Correctness (security engineer):** pflag sets `--admin` only from an unconsumed `--admin`/`--admin=` token. The walk shares #1355's arity table, and unknown options never consume. Anything the guard cannot model around `pr`/`merge` is refused rather than modelled.
- **Compatibility (maintainer):** the existing allow forms and contracts are unchanged. The new over-refusals are deliberate and fail closed: heredoc bodies that quote merge forms; plain-argument tokens such as a `merge` operand next to an `--admin` token outside gh; gh run under an argument supplier unless the group or subcommand is visibly not a merge.
- **Residuals (stated, not fixed):**
  - scripts in files;
  - gh aliases already present in the user's config;
  - commands assembled at runtime (the UMG refuses expansion shapes; destructive-guard covers them only through its text fallback);
  - the shell-tokenizer whitespace class in other guards (routed to Workspace Config's hook-defect lane);
  - other publication guards that still trigger on a contiguous `gh pr (create|merge)`.
- **Protection boundary:** the guarantee is local. The real control is server-side: no bypass actors and non-admin tokens. Protection takes effect only after promotion and install.
