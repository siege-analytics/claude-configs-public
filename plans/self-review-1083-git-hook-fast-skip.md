---
ticket_refs:
  - siege-analytics/claude-configs-public#1083: hooks start python3 ~33 times per Bash call
---

# Self-review: #1083 fast skip for trigger-specific Bash hooks

## Assumptions

Pre-author-inventory: on v3.5.71 (main 8b2b84e), installed in a mock workspace, a Bash `ls -la | head` ran 16 PreToolUse hooks with 33 python3 starts, about 3.8 s in total. The operator's Mac, on v3.5.70, measured 2.6 s per Bash call, with python3 starting in about 50 ms.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1083
Pre-mortem-artifact: plans/pre-mortem-1083-git-hook-fast-skip.md
Hostile-review-artifact: plans/self-review-1083-git-hook-fast-skip.md
Project-contribution: an ordinary Bash call in every consumer workspace goes from 33 python3 starts to 8, and its hook time drops by about 70%.

- The harness serialises tool payloads with JSON that does not escape ASCII letters. Payloads containing `\u` take the full path in case that assumption is wrong.
- Each hook's own trigger logic after the skip is unchanged.

## Peer review

- **writing-code:** the skip is inserted directly after `INPUT=$(cat)` in 13 hooks. No hook logic changed, and no new helper or edge was added.
- **writing-tests:** `git_hook_fast_skip` passes 213/213.
  - Its oracle is a copy of `hooks/` with the fast-skip blocks deleted. Every case must give the same exit code from both, run from a git repo on `main`.
  - It also asserts zero python3 starts for skips and at least one for the full path.
- **Gate evidence:**
  - every hook suite passes, 38/38 after `bin/build.py`;
  - review_risk_test PASS;
  - review_risk_policy 12/12;
  - metrics current;
  - build --check and generated-source-authority current.
- **Replay:** 0 exit-code differences between develop 310b9e0 and this branch, across 2,845 commands and 13 hooks.

## Hostile review

An independent reviewer read every skip predicate against the hook's own logic and ran crafted payloads. It found three gaps, all now fixed and pinned:

1. **Form feed.** A `\f` escape (`git\frevert`, `gh\fpr\fcreate`) is whitespace to the original `[[:space:]]+`, but the skip did not see it as whitespace. post-error-revision-required and pr-base-guard went from rc=2 to 0.
   - **Fix:** any JSON escape other than `\n \t \r \" \\ \/` takes the full path. That covers `\u`, `\f` and `\b`.
2. **Empty or misplaced command.** fix-shape-guard, self-review and test-tracking-guard treat an empty command in a repo as `git push`, but the skip ran first.
   - **Fix:** skip only when `tool_input`'s first key is a non-empty `"command"`.
3. **Shell-quoted gh.** coordinator-status-guard tokenises with shlex, so `g''h`, `"g"h` and `g\h` all mean `gh`. Its blocks went from rc=2 to 0.
   - **Fix:** that guard also tests the command with quote and backslash characters removed.

The reviewer also found the test weak: it only counted python3 starts and never compared verdicts. It has been rebuilt around the oracle above.

The escape handling was run under bash 5.2.21 and under bash 3.2.57, the macOS version, in the official `bash:3.2` image. Results were identical.

## Lead review

- **Solves #1083 for the Bash hooks:** yes.
  - Before and after, on the mock install, two runs each:
    - `ls -la | head`: from 33 to 8 python3 starts, 3.84–3.96 s down to 1.07–1.08 s;
    - `git status`: the same figures.
  - Prompt and Edit hooks are unchanged.
- **Out of scope:**
  - UserPromptSubmit (20 starts; ca-enforcement-gate has 9);
  - the mutation gate (4 starts) and the destructive guard (3 starts);
  - interpreter selection.

## Quantified claims

- Test cases: 213, all compared with the pre-#1083 oracle.
- Replay runs: 73,970, with 0 differences.
- python3 starts per Bash read: 33 before, 8 after.
