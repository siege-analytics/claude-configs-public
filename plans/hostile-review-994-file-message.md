---
ticket_refs:
  - siege-analytics/claude-configs-public#994: file-backed commit messages
---

# Hostile review: #994 file-backed commit messages

**Reviewer:** two independent isolated LLM reviews, separate from the authoring pass. Both were read-only and reviewed the frozen staged diff.

**Scope:** direct literal `git commit` message resolution for `-m`, `-F <file>`, `--file <file>`, and `--file=<file>`; retained fast prefilter, detector, scope and amend handling; fail-closed file errors; #1107 exclusions; Tier C and package integration.

## Findings in the first version

1. **Unreadable fixture depended on non-root execution.** A mode-`000` file can still be opened by root, so the test did not prove the requested denial in every environment.
2. **Attached `-F` lacked a deny pair.** `-F"ticketed message.txt"` passed, but no attached ticketless form was asserted.
3. **Incidental argv needed another negative.** The author field was covered, but pathspec text resembling `#994` was not.

A suggestion to change bare editor-driven commits was rejected as scope expansion. The operator brief covers explicit message sources only; aliases, wrappers, expansion, dynamic dispatch, and other unresolved shapes retain legacy handling and remain #1107 work.

## Resolution

- The resolver checks the opened descriptor's mode and rejects a regular source with no read permission bits, even under a privileged runner.
- Added `git commit -Fno-ticket.txt` as the attached deny pair.
- Added `git commit -m "subject only" -- path-#994.txt` to prove pathspec text is not message evidence.
- Re-ran the focused suite: 58/58 passed.
- Re-ran the Tier C dependency audit, build/check, package byte comparison, and all 44 hook suites.

## Final verdict

**PASS — no S1 or S2 findings.**

Dismissed risks: FIFO handling is nonblocking and rejects non-regular descriptors before reading; relative paths use nested then top-level CWD; missing, unreadable, oversized, non-regular, stdin, duplicate-file, and mixed sources fail closed; all 15 Finding #7 reads pass.

Residual risk: unsupported dispatch and editor-generated message shapes retain legacy behavior by design and remain outside #994.
