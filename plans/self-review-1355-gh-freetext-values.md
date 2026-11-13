---
ticket_refs:
  - siege-analytics/claude-configs-public#1355: pre-implementation artifacts with the design review (issuecomment-6847841788) and interim self-review (issuecomment-6847903748) posted; PR closes it
  - siege-analytics/claude-configs-public#1347: shared parser (PR #1356 head 47c45145) merged into this branch; this PR depends on #1356
---
# Self-review: gh free-text option values are not local mutation targets

Task: siege-analytics/claude-configs-public#1355
Review-Tier: C. The runtime change is in `hooks/lib/task_actions.py`, which is enforcement code. The first commit (`ca8e2c14`) was tests only, at Tier B.

## Assumptions

Goal source: #1355
Working as: software engineer (enforcement hooks)
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1355#issuecomment-6847841788
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1355#issuecomment-6847841788
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1355#issuecomment-6847841788
Hostile-review-artifact: plans/hostile-review-1355-gh-freetext-values.md

### Sources consulted

These are what I actually read, and what each one established.

- **#1355 body and both owner comments** (issuecomment-6845871452, issuecomment-6846801619): the properties to preserve, and the zero-arity scope, which covers known flags only.
- **`hooks/lib/task_actions.py` at develop `2a7c2ba4`:** both cause sites (`:2244-2252` and `:2416-2426`); `github_metadata_target` (`:1712`); and the tokenizer's rejection of `$` and backticks.
- **PR #1356 head `47c45145`:** the shared helper, its tests, and its review records. Its P3-1 is the zero-arity case.
- **Upstream cli/cli v2.104.0:** the flag definitions for `issue close|reopen`, `pr close|reopen|merge` and `release create`; `cmdutil.NilBoolFlag` (`NoOptDefVal "true"`); and the persistent flags on the root and the groups.
- **spf13/pflag** `parseLongArg` and `parseSingleShortArg`.
- **The installed gh** is 2.103.3 (pflag v1.0.10), reported by the code reviewer. The relevant command files and the parse code are equivalent to v2.104.0.
- **`hooks/lib/github-merge-queue.py`** and `resolve_action`: the pinned merge-queue route that runs before `action()`.

### Scope

- **Changed:** only the generic mutation branch's path scan for gh, and only for six subcommands with a verified flag table. For those subcommands:
  - text values are dropped;
  - path flags and positionals are kept;
  - a known zero-arity flag lets the following `-R/--repo` selector drop;
  - after an unknown option, the next token is kept;
  - scanning stops at `--`;
  - any command containing `--admin` is not modelled.
- **Unchanged:**
  - the cwd fallback and ownership;
  - the tilde and glob checks;
  - the tokenizer;
  - typed models, readers and the merge-queue route;
  - non-gh commands;
  - unmodelled subcommands, which behave exactly as under #1356.
- **Not implemented:** typed remote actions (option 2).

## Peer review

Shelf checks:

- **writing-tests:1/2 (red before green, negatives pinned):**
  - Every positive test was red on the pre-fix runtime and is green with the fix; the counts are below.
  - These negative tests passed on both the pre-fix and the fixed runtime, which pins behaviour that does not change:
    - `test_gh_path_values_and_operands_stay_targets`
    - `test_gh_unowned_genuine_text_command_target_still_refuses`
    - `test_gh_unknown_flags_and_shapes_keep_the_generic_model`
    - `test_gh_unmodelled_subcommands_and_executables_are_unchanged`
    - `test_gh_pinned_merge_policy_is_unchanged` (its gate half)
    - `test_gh_text_values_keep_expansion_and_substitution_checks`
    - `test_gh_release_assets_survive_bool_and_swallowed_flags`
    - `test_gh_admin_merge_keeps_the_1347_model`
- **writing-code:9 (no silently dropped input):** the helper returns `args` unchanged unless `args[0] == 'gh'` and the group is listed. A token is dropped only in two cases:
  - it is a grammar-valid selector;
  - it is the value of a table-listed 'text' flag of a modelled subcommand.
  Every other token is kept.
- **writing-claims:2 (countable claims):** every count in this record was read from a log in the worker session's `data/harness/` (`all1.out`, `all2.out`, `logs/*`) in the same work cycle. No count was inferred.

Gate evidence:

- **Syntax check:** `hooks/lib/task_actions.py` and `hooks/_test/explicit_target_operands.py` were imported and executed by python 3.11.11 in every run below, so both parse. A Python 3.9 syntax review was done by the code reviewer: the walrus in `elif`, `list[str]` and dict unpacking are all valid.
- **Red/green, all action-classification only; no real close, merge or release ran:**
  - Tests only, on unfixed develop `2a7c2ba4`: 108 failing subtests, all positive.
  - Final tests against the pre-fix runtime (`f974ae4a` tree, sandbox copy): 119 failing subtests, all positive. The asset, `--admin`, unknown-flag and substitution tests pass.
  - With the fix, on the final bytes: `explicit_target_operands.py` 41/41 OK.
- **Full hook suites:** all 87 `hooks/_test/*.test.sh`, run with the PyYAML venv (python 3.11.11) on PATH, from the session scratch runner (#1171), after `bin/build.py`.
  - On the reviewed blob `ae7a86b2`: 86 exit 0, 1 exit 1.
  - On the final bytes (`task_actions.py` `030bcb9b`, tests `252bef34`), after a fresh `bin/build.py`; started after 02:52 and finished by 03:16 CST: 86 exit 0, 1 exit 1.
  - The one failure in both runs is `ca_enforcement_runtime.test.sh`, which fails 4 process-ancestry checks (the spoofed CRAFT_* and PATH-ps cases). That suite and the scripts it copies are byte-identical to develop `b030b261` and do not reference `task_actions.py`. The runner descends from a real Craft Agents process, so its ancestry probe sees a genuine Craft ancestor. Inference: environment-dependent and not caused by this change. Hosted CI is the authority.
- **Freshness and validation, all exit 0 on the final bytes:**
  - `bin/build.py --check`, `bin/skill-inventory.py --check`, `bin/generated-source-authority.py --check`, `bin/sync-skill-references.py --check`, `bin/ontology.py --check`, `bin/kernel-budget.py --check`, `bin/review-risk-metrics.py --check`, `bin/skill-lifecycle.py --check`;
  - `bin/_test/review_risk_test.py` and `bin/_test/skill_inventory_test.py`.

## Lead review

Standards applied by the enforcement-hooks role:

- Fail closed on every unknown flag or shape.
- Classify flags from upstream source, not memory.
- Leave the cwd fallback and ownership untouched.
- Give no new allowance to anything the pinned merge-queue policy refuses.
- Extend the reviewed #1356 parser, not replace it; with no flags modelled, it is token-for-token equivalent.
- Keep the change narrow: six subcommands, one table.

## Findings

- **Design review, run 1: ACCEPT WITH CHANGES.**
  - P2-1: `--admin` through a non-literal prefix. Fixed by the guard.
  - P2-2: test rows. Added.
  - P3s: fixed.
- **Design review, run 2: ACCEPT.**
- **Code review: ACCEPT, no P1 or P2.** Four P3s, all fixed.
- **Delta code review: ACCEPT.** Runtime delta is comments only.
- **Hub conditions at checkpoint (b), all pinned by tests:**
  - "opaque" means kept;
  - substitution in dropped text values is still refused;
  - `--admin` forms behave exactly as under #1356;
  - #1356's `--squash -Ro/r` row is flipped on this branch only.
- **Outside this change (reported to the hub):**
  - non-literal `gh pr merge` prefixes skip the admin refusal;
  - [Withheld: a second, separate gap in the pinned merge-queue admin refusal was found during review and reported privately to the Siege Claude Hub; not in scope for #1355.]

## Rework ledger

- **Tests:** `--match-head-commit` moved out of the "passes" set, because the pinned merge-queue route refuses it before `action()`.
- **Draft helper, revision 1 to 2** (design review): the `--admin` guard, the rename to `_gh_path_scan_args`, `-h` removed, and comments.
- **After the code review:** comment fixes and one new test (P3-1 to P3-4).
- **Timestamp corrections:** times in the design note and one hub message were corrected after `date` checks.
- **Inventory:** `catalog/skills-inventory.json` regenerated for the new test text (two test-path entries).
