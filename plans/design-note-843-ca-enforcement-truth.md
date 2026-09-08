# Design note: #843 CA enforcement wrapper/verifier truth path

## Goal source

siege-analytics/claude-configs-public#843

## Problem

The verifier could claim `ENFORCEMENT LIVE` without proving the exact settings-registered CA wrapper path blocks, and the wrapper could starve later child gates by not replaying stdin. Child stderr/nonzero diagnostics were also hidden, making gate failures hard to diagnose.

## Design

- Capture UserPromptSubmit stdin once in `ca-enforcement-gate.sh` and replay it to every child gate.
- Capture child stdout and stderr together; preserve nonzero child status diagnostics.
- Keep CA wrapper blocking based on existing blocking output patterns and `continue:false` JSON.
- Extend `verify-enforcement.sh` so settings registration is not just path existence: copy the exact registered wrapper into a mock resolver and prove it emits `continue:false` under a blocking child.
- Align the generated think-gate manifest condition with real policy: missing design note is advisory at prompt time until mutation gates; stale/expired/scope-mismatched design signals are blocking.

## Non-goals

- Do not redesign all gate contracts (#851).
- Do not fix package artifact truth (#844), native pre-push range semantics (#845), scanner source truth (#850), or shared classifier work (#846).
- Do not make missing design note globally prompt-blocking, because the recent direction is to avoid blocking exploration/clarification and reserve hard blocks for mutation surfaces.

## Verified shapes

- PROBED: old wrapper failed to replay stdin to second child gate; new wrapper blocks when the second child sees the replayed payload.
- PROBED: old wrapper swallowed stderr/nonzero diagnostics; new wrapper includes stdout/stderr/status in the blocking system message.
- PROBED: verifier rejects an executable no-op settings-registered wrapper even when the real deployed wrapper exists.
- PROBED: manifest no longer falsely claims missing design note is the CA blocking condition.

## Tigers

### Tiger 1

Severity: HIGH
Likelihood: MEDIUM
Risk: preserving child stderr/stdout could create noisy block messages or expose too much output.
Mitigation: diagnostics are included only in the wrapper systemMessage when a child matches existing blocking patterns; clean/no-output gates remain silent.
Fallback: keep stderr capture but truncate in a follow-up if messages become too large.

### Tiger 2

Severity: HIGH
Likelihood: MEDIUM
Risk: changing no-design semantics to block would reintroduce overbroad prompt-time blocking.
Mitigation: this PR aligns manifest text to current advisory behavior instead of making a broad behavior change.
Fallback: if operator wants prompt-time missing-design hard blocks later, require a separate design under #851 gate-contract taxonomy.
