---
ticket_refs:
  - siege-analytics/claude-configs-public#1100: hardlinks and link creation escape the session scratch rule
---

## Pre-Mortem
Task: link copies and `ln` count both ends as targets, and a file with more than one link is not scratch, unless it is being removed.
Ticket: siege-analytics/claude-configs-public#1100

### Tigers

#### Tiger 1: legitimate scratch work starts blocking (Severity: medium)

Mitigation:
- Ordinary copies, writes, `mkdir` and `rm` inside `data/` are unchanged, and the allow cases stay green.
- Removing a hardlinked name is still scratch, because unlinking never writes the file.
- `ln` was never a scratch verb, since it is not in the self-managed set, so nothing that was allowed is lost.

#### Tiger 2: a link is still created or written through (Severity: high)

Mitigation:
- `read_allowlist.test.sh` pins `cp -l/--link/-al/-s/--symbolic-link`, `ln` with relative escapes, and writes, `tee`, `cp` and `chmod` onto an existing hardlink as must-block. 10 of these fail on develop.
- A symlink target was already caught by canonical paths.

#### Tiger 3: a TOCTOU race between the link count and the write (Severity: low)

The gate decides before the command runs. A link created inside the same command is caught by the operand rule, not the link count, so only an outside process racing the session could slip past, and that is not this gate's threat model.

### Launch-Blocking Assessment

None identified, provided the allowlist and task-keyed suites stay green.
