---
ticket_refs:
  - siege-analytics/claude-configs-public#1098: fast skip misses quoted, backslashed and multi-space triggers
---

# Self-review: #1098 fast skip matches rebuilt spellings of its triggers

## Assumptions

Pre-author-inventory: in the electinfo#375 review, `git "add" .env` and `git  add .env` exited 0 through the fast skip on `no-sensitive-files`, where the detector behind it exits 2. The oracle suite from #1083 covered shell-quoted `gh` only for `coordinator-status-guard`. I wrote the #1083 fast skip, so this regression is mine.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1098
Pre-mortem-artifact: plans/pre-mortem-1098-fast-skip-quoting.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1098#issuecomment-6289210439
Project-contribution: the fast skip no longer lets a quoted or spaced trigger past the #1096 command-text detector or the other 12 guards, and a long command no longer risks the hook timeout.

- The normalized copy is only for the skip decision. The full path still gets the original command.
- Where normalization could change a match rather than add one (glued quotes), the full path is taken instead.

## Peer review

- **writing-code:** each of the 13 hooks gains the same lines inside its `# Fast skip (#1083)` block:
  - a 16 KiB cap first;
  - `$'` and glued-quote checks;
  - a normalized copy;
  - a raw-or-normalized match.

  The oracle's sed still removes the whole block.
- **writing-tests:**
  - Each hook and trigger pair gains 8 spellings: quoted second word (double and single), empty quotes and a backslash inside the first word, two spaces, an ANSI-C first word, a glued backslash before, and a glued quote after.
  - A 300 KB-then-trigger case must finish in under 8 s.
  - The fixture repo is now in every guard's scope, and hooks run under `C.UTF-8`.
- **Hostile review (first version: NOT-MERGE-SAFE):**
  - Superlinear UTF-8 cost past the hook timeout: fixed by the cap.
  - Glued quotes disagreed with the oracle: fixed by the raw match and the glued-quote rule.
  - The fixture repo was out of scope: fixed.

## Test plan

- `bash hooks/_test/git_hook_fast_skip.test.sh`: 327/0 here, 72 failures on develop.
- Timing of the reviewer's payloads under UTF-8:

  | Payload | Here | Develop |
  |---|---|---|
  | 300 KB heredoc then `git add -A` | 0.57 s | 4.2 s |
  | 300k `\"` | 0.69 s | 93 s |

- The full CI validate job, run locally.

## Lead review

- **Solves #1098:** yes, for every spelling the full guards can see.
- **Out of scope:** expansion-based spellings, which the full guards cannot resolve either.

## Quantified claims

- 13 hooks; 327 oracle cases; 72 develop failures.
