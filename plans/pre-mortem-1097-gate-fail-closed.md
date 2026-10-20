---
ticket_refs:
  - siege-analytics/claude-configs-public#1097: universal-mutation-gate fails open when it cannot read its own input
---

## Pre-Mortem
Task: make universal-mutation-gate exit 2 when its extractor is unreadable, when python3 is missing, or when a non-empty payload is not a JSON object.
Ticket: siege-analytics/claude-configs-public#1097

### Tigers

#### Tiger 1: legitimate events start blocking (Severity: high)

A real hook payload is always a JSON object, from Claude Code or from Craft through ca-enforcement-gate's stdin replay. The new parse check runs only when no command came back and stdin is non-empty.

Mitigation:
- Write/Edit and other non-Bash events, empty stdin and `{}` still exit 0 (fixture cases).
- The corpus replay of 2,845 real commands runs old against new in two gate states and must show zero exit-code changes.

#### Tiger 2: a whole host goes dark because python3 is absent (Severity: medium)

A host without python3 had a gate that allowed everything. It now blocks every Bash call.

Mitigation:
- That is the documented policy (#477: no emergency disable; the only off switch is an auditable settings edit).
- The message names python3, so the cause is visible rather than silent.
- Every supported host already needs python3 for the rest of the hook tree.

#### Tiger 3: the probe reads fields differently from extract-json.py (Severity: high)

The probe replaces three extractor calls. If it disagreed with them on any input, decisions would drift.

Mitigation:
- It follows the extractor's rules line for line.
- The corpus replay must show zero changes.

#### Tiger 4: a large Write breaks the resolver (Severity: medium)

An exported value over 128 KiB makes every later exec fail with `E2BIG`.

Mitigation:
- Only the slim copy is exported, with every string over 4 KiB emptied except the command.
- Commands over 64 KiB block, with a message that names the size.
- The fixture pins both, including a padded ungated Write that must still block.

#### Tiger 5: latency (Severity: low)

One probe replaces three extractor starts, so a Bash call gets cheaper, not dearer. Timed at 119 ms per call here, against 163 ms on develop.

### Launch-Blocking Assessment

None identified, provided the corpus replay shows zero changes and the hook suites stay green.
