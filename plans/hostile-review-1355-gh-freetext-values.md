---
ticket_refs:
  - siege-analytics/claude-configs-public#1355: design review posted (issuecomment-6847841788); code review summarized in the PR
---
# Independent reviews: gh free-text option values are not local targets

Task: siege-analytics/claude-configs-public#1355

Every review was done by a fresh-context reviewer that took no part in drafting the change. They worked read-only, were briefed to refute or break it, and ran no Python or tests. The author ran the suites (see `plans/self-review-1355-gh-freetext-values.md`). A cross-family review was not used: the cross-review source's last connection test had failed (the #1337 failure mode), and its server runs from a checkout this worker was told not to touch.

## 1. Design review of the planned approach (code not yet written)

- **Base:** develop `2a7c2ba4` plus the tests-only commit `ca8e2c14`, with a draft helper kept outside the repository. Posted on the ticket before any runtime edit: issuecomment-6847841788.
- **Run 1: ACCEPT WITH CHANGES.**
  - P2-1: an `--admin` merge reached through a non-literal prefix would have been newly allowed. Fixed: any command with an `--admin` token is never modelled.
  - P2-2: tests were missing. Added: asset-preservation and zero-arity rows.
  - P3s: fixed.
- **Run 2 (delta): ACCEPT.** Its P3 was the docstring scope and an over-trigger row. Both adopted.

## 2. Code-level hostile review

- **Reviewed:** `git diff f974ae4a` of `hooks/lib/task_actions.py`, `hooks/_test/explicit_target_operands.py` and `catalog/skills-inventory.json`, plus `git show ca8e2c14`.
  - HEAD was `f974ae4a`: develop `b030b261` plus #1356 `47c45145` plus `ca8e2c14`.
  - Blobs, confirmed with `git hash-object`: `task_actions.py` `ae7a86b22b662486d2d3567779ae11b74382e7be`, test file `72069b223951e546a9679c2081dec3446a042658`.
- **Verdict: ACCEPT.** No P1 or P2 in the change.

**Findings and dispositions**

- P3-1: no test pins that a 'bool' entry does not swallow a positional, or the per-subcommand `-r` split. Fixed: new test `test_gh_flag_kinds_are_per_subcommand_and_bools_take_no_value`. Bool entries keep the next positional; `-r` is text for `issue close` and bool for `pr merge`.
- P3-2: untested paths: `-` alone in a modelled subcommand, a selector right after a path flag (`-F -Ro/r`), and `--help`. Fixed: rows for `gh pr close - -c a/b`, `gh pr merge 5 -F -Ro/r`, `--help` and `-h` in the same test.
- P3-3: the reason in the comment on `_GH_HELP_FLAGS` is wrong, because `--help=false` runs the command. Fixed: the comment now says `--help` is a persistent bool with no shorthand.
- P3-4: the `--admin` entry in the `pr merge` table is dead. Fixed: a comment above the `pr merge` entry says `--admin` is listed for completeness only.

**Outside this change:** [Withheld: a second, separate gap in the pinned merge-queue admin refusal was found during review and reported privately to the Siege Claude Hub; not in scope for #1355.]

*Disclosure redaction (2026-11-13, directed by the Siege Claude Hub):* the paragraph above was edited after the review to withhold details of an out-of-scope security gap. The edit does not change any verdict, finding or disposition for #1355.

**Attacks that held**

- Every table entry matches cli/cli v2.104.0. The installed gh is 2.103.3 with pflag v1.0.10, and its parse code is equivalent.
- pflag cluster, `=` and NoOptDefVal handling.
- Equivalence with #1356 when no flags are modelled.
- Subcommand lookup.
- The `--admin` guard.
- `scanned` is used only for the two path passes; the tilde/glob checks still see the original arguments.
- The cwd fallback is always added.
- Callers of `action()` read only `read_only` / `metadata_only`.
- The merge-queue route is unchanged.
- The scanner SHA constants are unchanged from develop.
- Python 3.9.
- Every test expectation was re-derived.

## 3. Delta code review of the P3 fixes

- **Reviewer:** the same reviewer, read-only and briefed to break.
- **Blobs**, confirmed with `git hash-object`; these are the committed bytes:
  - `task_actions.py` `030bcb9bf48c9c28d2066fd3a5dc26331ef27145`
  - test file `252bef34bb5b829436473f6947a9244e6d72a19a`
- **Verdict: ACCEPT.**
  - The runtime delta is two comments only. The table, helpers, walk, `--admin` guard and call site are unchanged.
  - Every new test row was traced against the code and pflag v1.1.0.
- **P3 (optional, no change):** the `--help=false -ca/b` row does not pin the `--help` table entry, because `=` sets no pending state either way. The `--help -c a/b` row already pins it.
