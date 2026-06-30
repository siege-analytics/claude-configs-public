---
ticket_refs:
  - siege-analytics/claude-configs-public#591: open
type: pre-mortem
---

## Risk classification for #591: stderr redirect false positive

### Tiger 1: Revised pattern misses legitimate stdout redirects
- **Severity:** High
- **Urgency:** High — if we exclude too much, real mutations slip through
- Mitigation: test the revised pattern against all existing test cases; the pattern must still catch 'command > file' and 'command >> file'
- Falsification: if 'echo foo > bar.txt' is no longer caught, the fix is wrong
- **Status:** Addressed — test all 19 existing cases plus new stderr redirect cases

### Tiger 2: Bash regex doesn't support lookbehinds
- **Severity:** Medium
- **Urgency:** Medium — bash [[ =~ ]] uses POSIX ERE, no lookbehinds
- Mitigation: restructure the pattern to use alternation or character classes instead of lookbehinds
- **Status:** Addressed — use explicit patterns for stdout redirects instead of a broad > match

Implementation may proceed: YES
