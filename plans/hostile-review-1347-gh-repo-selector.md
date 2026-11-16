---
ticket_refs:
  - siege-analytics/claude-configs-public#1347: design review posted (issuecomment-6845496410); code review summarized in the PR
---
# Independent reviews: gh -R/--repo selector is not a local target

Task: siege-analytics/claude-configs-public#1347

Both reviews were done by fresh-context reviewers that took no part in drafting the change. They worked read-only and were briefed to refute or break it. Neither ran Python or the test suites; the author ran those (see `plans/self-review-1347-gh-repo-selector.md`).

## 1. Design review of the planned approach (code not yet written)

- **Base:** develop `741893ba`, with the tests at `e1aab5fe`. `hooks/lib/task_actions.py` was unchanged from develop.
- **Read:**
  - the approach and the draft helper;
  - `task_actions.py` around the generic branch (2150-2430), the ssh grammar (850-860), the reader at 1210, and 2039-2088;
  - the #1347 tests;
  - upstream cli/cli `pkg/cmd/root/root.go` and `pkg/cmd/alias/shared/validations.go`.
- **Posted on the ticket** before any runtime edit: https://github.com/siege-analytics/claude-configs-public/issues/1347#issuecomment-6845496410 (06:00:44Z).

**Run 1: ACCEPT WITH CHANGES**

- **P1:** a selector directly after a bare value-taking option is that option's value. pflag hands a string flag the next token even when it starts with `-`.
  - In `gh release create v1 --title -R o/r`, `o/r` becomes an upload asset.
  - In `gh run download 9 -D -Ro/r`, gh writes into `./-Ro/r`.
  - The draft dropped both. Resolution: fixed. A selector right after a bare option is kept, unless that option was itself a dropped selector.
- **P3:** a nested `issue x` shell alias can route through a listed group. Not new exposure, because shell aliases already defeat the cwd model. Recorded, not fixed.
- **P3:** the scanned argument list must be computed after the `_project_execution_wrapper` rewrite. Satisfied: it is computed at `local = effective`.

**Run 2 (delta on the fixed design): ACCEPT**

- **P1 resolved** for:
  - `--title -R o/r`
  - `-D -Ro/r`
  - `-R -R o/r`
  - `-t -R o/r -R c/d`
  - `gh --foo -R o/r issue ...`
- **No new fail-open or leakage.** The `=` exception and the after-selector rule are sound.

## 2. Code-level hostile review

- **Reviewed:** `git diff origin/develop -- hooks/lib/task_actions.py hooks/_test/explicit_target_operands.py`.
  - HEAD was `a05a0643` (the develop `89410b9c` merge), and the review included the then-uncommitted runtime change.
  - Runtime blob reviewed: `744184707755621789b5a1da56e67e842eb75ac4`. It is unchanged in the published head.
- **Also read:**
  - `_action` (2270-2330, 2440-2490);
  - `_SSH_LABEL`/`_SSH_HOST`;
  - `bounded_write_targets`;
  - upstream cli/cli `repo_override.go`, `ruleset.go` and `cache.go`.
- **Verdict: ACCEPT.** No P1 or P2, and no fail-open path.

**Attacks that held**

- Indexing at i=1 and empty args.
- A trailing bare `-R`.
- Prefix order (`--repo=`, `-R=`, `-R`).
- Look-alike long flags (`--repository`, `--repo-x`).
- `--` handling.
- The bare-option rule checked against pflag. A token containing `=` never consumes the next argument.
- The cwd fallback, `bounded_write_targets`, the git branch and the glob/tilde checks all still use the original `args`.
- `scanned is args` for non-gh commands, including `env gh`, `command gh` and an absolute gh path.
- The regex: no catastrophic backtracking, and its lookahead applies only to the repo segment. The ASCII classes with `fullmatch` reject newlines and unicode.
- The tests pin the fix, and the unmodelled oracle is meaningful.
- Python 3.9 compatible.

**Findings and dispositions**

- **P3-1:** `--squash -Ro/r` and `-dRo/r` still give `/r` and are refused. Disposition: deliberate fail-closed behaviour (design P1). A per-group zero-arity allowlist would be a possible follow-up.
- **P3-2:** the look-alike flags were not pinned. Disposition: fixed. `--repository o/r`, `--repo-x=o/r` and `-dRo/r` were added to the grammar-negative oracle test. That was a test-only change after the review.
- **P3-3:** `prev != '--'` in `width_at` is unreachable. Disposition: kept as a harmless defence, rather than change reviewed runtime code.
- **P3-4:** untracked `.1051-test-*` directories in the worktree. Disposition: these are self-cleaning fixtures from concurrent suite runs, and staging is by explicit path only.

## Process disclosure

- The installed (v3.5.92) turn-start hook derived the Tier C junior-senior and artifacts-posted companions at 00:00:01 CST from the first, pre-implementation comment (issuecomment-6845368377). That comment's Senior section was the author's own planned checklist.
- That was 43 seconds before the design-review follow-up existed (00:00:44).
- The actual design review was posted before the runtime edit (00:01:38). The companions were re-derived at 00:08:33 CST, after the review was posted.
