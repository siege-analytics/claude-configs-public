---
ticket_refs:
  - siege-analytics/claude-configs-public#994: file-backed commit messages
---

# Hostile review: #994 file-backed commit messages

**Reviewer:** two independent isolated LLM reviews, separate from the authoring pass. Both were read-only and reviewed the frozen staged diff.

**Scope:** direct literal `git commit` message resolution for `-m`, `-F <file>`, `--file <file>`, and `--file=<file>`; retained fast prefilter, detector, scope and amend handling; fail-closed file errors; #1107 exclusions; Tier C and package integration.

## Pre-commit staged-review findings

1. **Unreadable fixture depended on non-root execution.** A mode-`000` file can still be opened by root, so the test did not prove the requested denial in every environment.
2. **Attached `-F` lacked a deny pair.** `-F"ticketed message.txt"` passed, but no attached ticketless form was asserted.
3. **Incidental argv needed another negative.** The author field was covered, but pathspec text resembling `#994` was not.

Those findings were fixed before the first commit. A suggestion to change bare editor-driven commits was rejected as scope expansion. The operator brief covers explicit message sources only; aliases, wrappers, expansion, dynamic dispatch, and other unresolved shapes retain legacy handling and remain #1107 work.

## Exact-SHA finding on the first commit

The independent regression reviewer returned **NEEDS_REWORK** against `b37aaebc7b0026b0350bd1ae7f2fe489303eb9c2`:

- **S1 fail-open:** `shlex` removed quote provenance before the token-level shell-operator check. A quoted literal `;` was therefore mistaken for command syntax, the resolver returned unsupported, and `ticket-required.sh` fell back to scanning unrelated argv.
- Reproductions that incorrectly allowed were `git commit -m ";" --author="Refs: #994 <test@example.com>"` and `git commit -F ";" --author="Refs: #994 <test@example.com>"`, even though the first message is ticketless and the second file is missing.
- A separate static reviewer initially reported PASS but withdrew it after the executable reproduction. The effective verdict for `b37aaebc7b00` is NEEDS_REWORK.

## Resolution in the first follow-up commit

- Shell operator characters were identified in the raw command while single/double quote provenance still existed.
- Added deny regressions for both exact incidental-author reproductions plus paired quoted-semicolon message/path and malformed-quote coverage.
- The focused suite passed 64/64 before push.

## Exact PR-head review at a857c0ef

The required `Review #994 alias and command parsing` gate returned **REJECT** against `a857c0ef63dd305f050192051a0339c4596737d9`:

1. **B1 fail-open:** other quoted shell characters and unhandled message spellings still returned unsupported, so the hook re-scanned unrelated argv. The blocker covered multiline/single-quoted shell characters, double-quoted expansion, canonical heredoc, `--message`/prefix forms, and clustered `-am`.
2. **B2 message mismatch:** the helper retained words after an unquoted Bash comment, did not consume value-taking options, ignored `--trailer`, and did not apply CLI or configured cleanup modes.
3. **B3 stale metrics:** `catalog/review-risk-metrics.json` did not reflect the Tier C policy length change, so hosted validation stopped before Linux hook scenarios.
4. **B4 topology:** the feature did not contain current canonical main. CI required a normal main-to-feature merge; no rebase or history rewrite was permitted.

The gate also required README/CHANGELOG claims and the self-review record to match only supported behavior. That verdict supersedes every earlier PASS statement for the PR.

## Rework after the exact-head rejection

- Direct literal `git commit` now fails closed when its message cannot be modeled; legacy argv fallback remains only for non-direct dispatch shapes outside #994.
- Raw quote-aware scanning handles word-start Bash comments, literal multiline/single-quoted shell characters, and rejects unmodeled expansion. A bounded parser preserves the canonical quoted-delimiter heredoc body.
- The option model resolves `--message` and unambiguous prefixes, clustered `-am`, value-taking options, trailers, and CLI/configured `strip` or `scissors` cleanup. Message-producing options outside the model fail closed.
- The expanded real-hook suite passes 106/106, including every B1/B2 deny reproduction, paired allows, and three real-Git cleanup ordering/scissors regressions; the 15 read controls remain included.
- The rejected-head reviewer's isolated real-Git differential harness was rerun against the rework. Every F1-F7 and G1-G8 blocker row reports `pr_correct=true`, all 15 reads remain allowed, and only the directed follow-ups remain mismatches.
- `bin/review-risk-metrics.py` regenerated the single stale `policy_characters` field, and the check passes.
- Canonical main was merged into the feature with a normal merge commit after CI required it. The PR diff against develop remained the same nine #994 paths.
- README and CHANGELOG now state the modeled forms, 1 MiB regular-file bound, cleanup/trailer behavior, fail-closed boundary, and deferred dispatch/editor scope.

## Current verdict

Both reviewed heads remain rejected: `b37aaebc7b0026b0350bd1ae7f2fe489303eb9c2` is NEEDS_REWORK and `a857c0ef63dd305f050192051a0339c4596737d9` is REJECT.

The rework above has author-side evidence only. No independent reviewer has verified the next pushed PR head, and this artifact makes no PASS claim for it. The `Review #994 alias and command parsing` gate must run again at that exact head before merge consideration.

Residual scope: `-qF`, tilde expansion, large-message pipe behavior, compound `cd &&`, editor mutation, #1107 dispatch, and the pre-existing amend/no-edit skip remain follow-up work as directed by the exact-head review.
