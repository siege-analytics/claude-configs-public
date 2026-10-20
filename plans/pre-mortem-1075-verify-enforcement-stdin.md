---
ticket_refs:
  - siege-analytics/claude-configs-public#1075: sync-workspace-hooks.sh hangs from a terminal; the verify-enforcement probe reads the caller's stdin
---

## Pre-Mortem
Task: stop `bin/verify-enforcement.sh`'s local block probe from reading the caller's stdin.
Ticket: siege-analytics/claude-configs-public#1075

### Tigers

#### Tiger 1: Closing stdin changes what the probe verifies

The probe asserts that the gate emits `continue:false` on a STALE DESIGN fixture. In CI, stdin is already empty, and that is the condition the assertion was written and passing under. `< /dev/null` reproduces exactly that input, so the asserted behavior is unchanged. Evidence: `verify_enforcement` passes 39/39, and the wired-fixture and STALE DESIGN probes pass as before.

#### Tiger 2: The regression test hangs CI instead of failing

The new case runs the probe under `timeout 120` with an open, silent stdin. The writer process holds only the pipe it feeds and is killed afterwards. The first draft let the writer hold the test's stdout, and the suite took 601 s; this version takes 29 s. Without the fix, the case fails with exit 124 in about 120 s rather than hanging.

### Paper Tigers

- The second probe (line 232) already pipes a payload, so it is unaffected.

### Launch-Blocking Assessment

None identified.
