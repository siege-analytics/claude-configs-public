---
ticket_refs:
  - siege-analytics/claude-configs-public#1087: classifier and legacy safelist admit git remote/tag/config writes, date, printf -v, --ext-diff, option-word globs
---

## Pre-Mortem
Task: veto the write and execute forms that #1055's adversarial fixtures caught in the released read classifier, so neither the classifier nor the legacy safelist admits them.
Ticket: siege-analytics/claude-configs-public#1087

### Tigers

#### Tiger 1: The fix misses a spelling (Severity: high)

Mitigation:
- Write subcommands are rejected anywhere after `git remote` (REMOTE_WRITE). Tag creating, signing and deleting options are matched as long-option prefixes and as short clusters. `git tag NAME` is a veto.
- Each fix is a veto (exit 3), so the legacy `SAFE_PATTERNS` git regex can no longer admit it.
- `read_allowlist` gains 18 must-block cases. All 18 fail on develop and pass here.

#### Tiger 2: Ordinary reads start being blocked (Severity: medium)

Mitigation:
- 16 allow cases are pinned: `git remote -v`, `git remote show|get-url`, `git tag [-l]`, `date [+FMT|-d|-u|-I]`, `printf FORMAT`, `rg foo src/*.py`, `ls *.md`, `git config --get`.
- A replay of 2,845 real commands, with no gate and with a designing gate, shows 0 verdict changes.

### Launch-Blocking Assessment

None identified, provided the suites stay green at the head.
