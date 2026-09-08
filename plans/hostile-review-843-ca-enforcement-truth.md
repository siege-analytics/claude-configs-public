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

## Follow-up after external hostile review

External hostile review on PR #853 found three valid gaps before main promotion:

1. The verifier copied the settings-registered wrapper into a mock resolver, but did not prove the registered path was the deployed workspace wrapper. Follow-up fix: verifier now canonicalizes the registered path and requires it to equal `$HOOKS_ROOT/resolver/ca-enforcement-gate.sh`; external registered wrappers fail until #848/#851 define an explicit override contract.
2. The wrapper ignored child `continue:false` JSON unless magic text was also present. Follow-up fix: child JSON with `continue:false` now triggers blocking.
3. Nonzero stderr-only child failures were diagnostic text but not blocking. Follow-up fix: nonzero child status fails closed and includes stderr/status diagnostics.

Follow-up validation:
- `bash hooks/_test/ca_enforcement_gate.test.sh` -> 11 passed, 0 failed.
- `bash hooks/_test/verify_enforcement.test.sh` -> 9 passed, 0 failed.
- `bash hooks/_test/ca_enforcement_manifest.test.sh` -> 2 passed, 0 failed.

Second external hostile review on PR #855 found one additional valid gap: the verifier parsed a path substring from the settings command and ignored shell suffixes/redirections that break CA's single-JSON stdout contract. Second follow-up fix: settings command parsing now uses `shlex.split`, accepts exactly one shell token resolving to `ca-enforcement-gate.sh`, rejects suffix/redirection/control forms, and `build.py` quotes generated CA wrapper paths so workspace paths with spaces stay one shell token.

Second follow-up validation:
- `bash hooks/_test/ca_enforcement_gate.test.sh` -> 11 passed, 0 failed.
- `bash hooks/_test/verify_enforcement.test.sh` -> 11 passed, 0 failed.
- `bash hooks/_test/ca_enforcement_manifest.test.sh` -> 2 passed, 0 failed.

## Verdict

PASS after follow-up. This remains a bounded #843 truth-path repair. It does not solve the whole crazy gate architecture, but it stops one class of false `ENFORCEMENT LIVE` claim and adds executable tests for the exact behavior.
