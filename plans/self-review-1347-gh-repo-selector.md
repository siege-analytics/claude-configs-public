---
ticket_refs:
  - siege-analytics/claude-configs-public#1347: pre-implementation artifacts and design review posted; PR closes it
  - siege-analytics/claude-configs-public#1355: sibling (free-text option values) filed, out of scope
---
# Self-review: gh -R/--repo selector is not a local mutation target

Task: siege-analytics/claude-configs-public#1347
Review-Tier: C. The runtime change is in `hooks/lib/task_actions.py`, which is enforcement code.

## Assumptions

Goal source: #1347
Working as: software engineer (enforcement hooks)
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1347#issuecomment-6845368377
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1347#issuecomment-6845368377
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1347#issuecomment-6845368377
Hostile-review-artifact: plans/hostile-review-1347-gh-repo-selector.md

### Sources consulted

These are what I actually read, and what each one established.

**Reproduction** (`action()` at develop `741893ba`):

- `gh issue close 5 -R|--repo|--repo= example/target` produced `<cwd>/example/target` plus `<cwd>`, both from a non-repo cwd and from a clone. The cause is the slash-operand pass in the generic branch.
- `-Rexample/target` produced `/target`, through the cwd-fallback option-attached pass. The source gate refused it even from a clone the task owns.

**Upstream cli/cli trunk:**

- `pkg/cmdutil/repo_override.go` registers `cmd.PersistentFlags().StringP("repo", "R", "", "Select another repository using the [HOST/]OWNER/REPO format")`. The value is parsed by `ghrepo.FromFullName` and never as a path.
- `cmdutil.EnableRepoOverride` is called in issue, pr, release, run, workflow, label, secret, variable, cache and ruleset.
- The flag is persistent, and cobra finds subcommands after stripping flags. The installed gh accepted the global-position form `gh -R owner/repo issue view 1347` (#1347 comment of 2026-11-13T05:02Z).

**Existing tests:**

- `hooks/_test/task_keyed_gates.py:139-161` pins that unmodelled gh state transitions refuse from an unowned cwd. This change keeps that.

### Scope

- Only the generic mutation branch, and only those ten groups.
- A selector value is dropped from local path scanning only when all of these hold:
  - it matches `[HOST/]OWNER/REPO` exactly;
  - it comes before `--`;
  - it does not directly follow a bare option that could own it as its value.
- It may appear after the group or before it (the global position).
- Unchanged:
  - the cwd fallback and its ownership;
  - the glob/tilde checks;
  - genuine path operands;
  - non-grammar values;
  - other groups, extensions and absolute gh paths;
  - all typed remote models;
  - readers.
- Not implemented:
  - typed remote-action policy (issue option 2);
  - repo_root resolution;
  - free-text option values (#1355).

## Test plan

Executed checks:

- **Red/green on the final test file** (`hooks/_test/explicit_target_operands.py`, 27 tests):
  - On unfixed HEAD `a05a0643` (develop `89410b9c` merged): exit 1, with 119 failing subtests, all in the six positive tests.
  - With the fix: 27/27 OK (system python3 3.9.6, 00:11 CST).
- **Full hook suites:** all 87 `hooks/_test/*.test.sh` with the PyYAML venv (python 3.11.11) on PATH, 00:04-00:28 CST.
  - 86 exit 0.
  - `ca_enforcement_manifest.test.sh` exit 1, because `dist/` did not exist yet. It was exit 0 after `bin/build.py`.
  - This run included the runtime fix. The test file gained only the look-alike cases (P3-2) after its suite ran, and was rerun at 27/27.
- **Freshness and build:** each exited 0.
  - `bin/sync-skill-references.py --check`
  - `bin/build.py --check`
  - `bin/build.py`
  - `bin/validate-hooks.py` (dist/claude-code/, dist/craft-agent/, and source)
  - `bin/_test/settings_drift_test.py`
  - `bin/_test/registered_scanner_execution_test.py`
- **Inventory:**
  - `bin/skill-inventory.py --check` and `bin/generated-source-authority.py --check` first reported a stale `catalog/skills-inventory.json`. The new test text mentions `gh pr merge` and `--delete-branch`, so the file is now listed under the `merge` and `branch` skills.
  - The committed change is byte-identical to the generator's output, and both checks then exited 0.
- **Limitation:** local runs are not hosted CI. CI (Python 3.12, pinned requirements) is the authority.

## Peer review

- **writing-tests:**
  - Every positive test was red on unfixed source and is green with the fix. The 119-subtest red result and the 27/27 PASS are listed above.
  - Negative tests passed on both unfixed and fixed source, which pins behaviour that does not change:
    - `test_gh_selector_grammar_negatives_keep_the_generic_model`
    - `test_gh_groups_without_repo_override_are_unchanged`
    - `test_gh_genuine_paths_and_unproven_selectors_stay_targets`
    - `test_gh_unowned_genuine_target_still_refuses`
    - the swallowed-selector half of `test_gh_selector_after_a_bare_option_may_be_its_value`
  - `test_gh_repo_selector_keeps_the_owned_cwd_requirement` checks both sides:
    - its refusal (exit 2 from an unowned cwd) holds on both sources;
    - its denial-text assertion (no `<cwd>/example...` target) is red on unfixed source. That accounts for its 10 failing subtests in the red run.
- **writing-code:**
  - The helper only acts when `args[0] == 'gh'` and the group is a listed one; otherwise it returns `args` unchanged.
  - The full 87-suite run had no regressions: 86 PASS, plus 1 that passes after the build.
- **writing-claims:** every count in this record comes from a log in the worker session's `data/harness/logs`. No count was inferred.

## Lead review

- The Siege Claude Hub (coordinating session) approved the approach at checkpoint (b) and ruled on sequencing, scope (global position, tests 1-5) and history recomposition.
- It did not review the code. Code-level review is independent; see Independent review.

## Quantified claims

- 10 gh groups, verified upstream to call `cmdutil.EnableRepoOverride`.
- 5 selector spellings, accepted both after the group and before it.
- Final test file:
  - 27 tests;
  - 119 failing subtests in 6 positive tests on unfixed source;
  - 27/27 pass with the fix.
- Full run: 87 suites, 86 exit 0, and 1 that exits 0 after the build.
- Runtime blob reviewed and published: `744184707755621789b5a1da56e67e842eb75ac4` (`hooks/lib/task_actions.py`).

## Findings

P1: a selector after a bare value-taking option was dropped although pflag gives it to that option (design review run 1); Resolution: fixed

- **P3 (design):** a nested shell alias under a listed group is recorded, not fixed; it is not new exposure.
- **P3-1 (code):** `--squash -Ro/r` stays refused. This is deliberate fail-closed behaviour and a possible follow-up.
- **P3-2 (code):** look-alike flags were not pinned. Fixed with tests.
- **P3-3 (code):** an unreachable `prev != '--'`. Kept.
- **P3-4 (code):** stray fixture directories. Staging is by explicit path.

## Independent review

Two fresh-context reviewers, neither of whom drafted the change:

1. **Design review** before any runtime edit: ACCEPT WITH CHANGES, then ACCEPT after the delta. Posted at https://github.com/siege-analytics/claude-configs-public/issues/1347#issuecomment-6845496410.
2. **Code-level hostile review** of the diff against develop `89410b9c` (HEAD `a05a0643`, runtime blob as above): ACCEPT, with no P1 or P2.

Details are in `plans/hostile-review-1347-gh-repo-selector.md`.

### Tree identity

The local commits were recomposed before the first push (hub-approved) so that every commit carries the installed pre-push trailers. The recomposed head has the same tree as the pre-recomposition backup branch, and `git diff <backup> HEAD` is empty.

This file is part of that tree, so it cannot contain its own tree hash. The reviewed runtime is pinned instead by the blob hash above, and the tree hash is reported in the PR body.

## Process disclosure

- The installed (v3.5.92) turn-start hook derived the Tier C companions at 00:00:01 CST from the pre-implementation comment, whose Senior section was self-planned.
- That was 43 seconds before the design-review follow-up existed (00:00:44).
- The actual design review was posted before the runtime edit (00:01:38). The companions were re-derived at 00:08:33 after it.
