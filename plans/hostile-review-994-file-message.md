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

## Resolution in the follow-up commit

- Shell operator characters are now identified in the raw command while single/double quote provenance still exists. Only unquoted operators make the narrow parser return unsupported; quoted operator characters remain literal message/path data.
- Added deny regressions for both exact incidental-author reproductions.
- Added paired ticketed/ticketless quoted-semicolon message and file-path cases plus malformed-quote handler coverage.
- The focused suite now passes 64/64; the commit detector passes 24/24.
- Re-ran the Tier C dependency audit, build/check, package byte comparison, three hook-tree validators, and all 44 hook suites on the fixed worktree.

## Current verdict

`b37aaebc7b0026b0350bd1ae7f2fe489303eb9c2` remains **NEEDS_REWORK** and must not be described as a pass.

The S1 fix has author-side test evidence, but no independent reviewer has yet verified the new commit/PR head. The required `Review #994 alias and command parsing` gate must review the exact pushed PR head before it is considered merge-safe. This artifact makes no exact-head PASS claim in advance of that review.

Dismissed risks after the local fix: FIFO handling is nonblocking and rejects non-regular descriptors before reading; relative paths use nested then top-level CWD; missing, unreadable, oversized, non-regular, stdin, duplicate-file, and mixed sources fail closed in tests; all 15 Finding #7 reads pass.

Residual risk: unsupported dispatch and editor-generated message shapes retain legacy behavior by design and remain outside #994.
