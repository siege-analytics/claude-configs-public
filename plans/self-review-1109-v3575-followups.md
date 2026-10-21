---
ticket_refs:
  - siege-analytics/claude-configs-public#1109: command-text fail-closed and unwrapping, ln link-relative targets, macOS test portability
---

# Self-review: #1109 v3.5.75 follow-ups from the v3.5.74 release review

## Assumptions

Pre-author-inventory: CodeRabbit raised these five on #1106. On develop, the new cases fail 11 times: commit_detector 3, sensitive_files 4, broad_staging 2, read_allowlist 2.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1109
Pre-mortem-artifact: plans/pre-mortem-1109-v3575-followups.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1109#issuecomment-6299070260
Project-contribution: the git guards cannot be skipped by quoting a verb, wrapping it in `bash -c`/`eval`, or making their helper crash. A relative symlink cannot reach outside scratch through a link's own directory. Two tests run on stock macOS.

1. `command-text.py` exits 3 on any exception. The `command-text.sh` helpers treat any result other than a clean 0/1 (`--is-commit`) or 0 (the others) as a helper failure, and fall back to the over-matching path.
2. `git_add_targets` unwraps `bash -c`/`sh -c`/`eval` arguments before splitting segments. Its tokenizer drops a backslash the way the shell does.
3. `_strip_quoted` keeps the content of a quoted span with no whitespace in it (`"commit"`, `''`) and drops multi-word spans. A backslash outside quotes yields the escaped character.
4. `ln`: each relative operand is also resolved from the link's directory, and from the link itself in case it is a directory.
5. `broad_staging` and `session_anchor_mistag` use a `_tmo` wrapper that runs unbounded when `timeout` is missing.

## Peer review

- **writing-tests:** new cases in four suites.
  - **commit_detector:** 4 rebuilt verbs, an escaped-space ignore, and 3 crashing-helper variants.
  - **sensitive_files:** 3 unwrap/escape refusals, 7 hidden-`git add` refusals, 1 prose allow, and a broken helper.
  - **broad_staging:** 2 quoted verbs.
  - **read_allowlist:** 2 link-relative cases and 3 `ln -t` cases.
- **Hostile review (first version: NOT-MERGE-SAFE), all fixed:**
  - **B1:** splicing hid a later `git add`. Fixed with a raw plus balanced-unwrapped union and a lookbehind boundary.
  - **S1:** `--is-commit` failed open on a crash. Fixed with the sentinel.
  - **S2:** `ln -t` skipped the link-relative reading.
  - **S3:** an escaped space was split into two words.
  - **S4:** a boundary-character false positive.

## Test plan

- commit_detector 32/0, sensitive_files 23/0, broad_staging 11/0, read_allowlist 307/0, session_anchor_mistag 13/0, all here. The first-round cases fail on develop (11 failures).
- review_risk_test, skill-inventory and generated-source-authority `--check` pass.
- The full local validate job.

## Lead review

- **Solves #1109:** yes, all five items.

## Quantified claims

- 33 new cases; the 11 first-round cases fail on develop. The review-round cases guard against regressions of this branch, and develop already blocks most of them.
