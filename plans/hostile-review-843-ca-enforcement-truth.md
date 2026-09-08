# Hostile review: #843 CA enforcement truth path

Frame: grumpy Scala/JVM reviewer who distrusts Bash wrappers, fake verifiers, and AI-written ceremony.

## Surface reviewed

- `hooks/resolver/ca-enforcement-gate.sh`
- `bin/verify-enforcement.sh`
- `bin/build.py` CA manifest condition
- `hooks/_test/ca_enforcement_gate.test.sh`
- `hooks/_test/verify_enforcement.test.sh`
- `hooks/_test/ca_enforcement_manifest.test.sh`

## Findings checked

### Registered wrapper truth

PASS. The verifier no longer stops at “some deployed canonical wrapper can block.” It extracts the settings-registered command and runs a live block probe through that exact wrapper copied into a mock resolver. A no-op registered wrapper fixture fails.

### Stdin replay

PASS. The wrapper captures stdin once and replays it to every child. The regression where the first child consumes stdin and the second child starves is covered.

### Child diagnostics

PASS with watch item. Stderr and nonzero child status are preserved in the blocking message. This is better than silent failure. If output bloat becomes a problem, add truncation later; do not go back to swallowing failures.

### No-design semantics

PASS. The lazy fix would have been to make every missing design note prompt-block, recreating global gate pain. This PR instead changes the manifest claim to match runtime policy: missing design is advisory until mutation gates; stale/expired/scope-mismatched signals are blocking.

## Verdict

PASS. This is a bounded #843 truth-path repair. It does not solve the whole crazy gate architecture, but it stops one class of false `ENFORCEMENT LIVE` claim and adds executable tests for the exact behavior.
