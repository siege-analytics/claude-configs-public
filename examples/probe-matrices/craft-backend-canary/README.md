# Craft/backend live-canary packet (#1003)

This directory prepares a reversible, sequential canary. **Nothing here authorizes a live run.** The checked-in packet is deliberately `status: proposal`, leaves prerequisite integration revisions and exact materialized package bytes unresolved, and records no operator approval. A later approval record is externally supplied evidence only; this tool cannot grant authority.

## Fixed proposal identity

- Run: `cc-1003-provider-canary-20261016`
- Temp/source/evidence root: `/private/tmp/cc-1003-provider-canary-20261016`
- Disposable Craft workspace: `/Users/dheerajchand/.craft-agent/workspaces/cc-1003-provider-canary-20261016`
- Backend 1: `claude-max` / `claude-opus-4-8`
- Backend 2: `chatgpt-plus` / `pi/gpt-5.5`
- Backend timeout: 900 seconds each
- Transition timeout: 180 seconds
- Cleanup timeout: 300 seconds
- Overall deadline: 2,400 seconds
- Cleanup owner: Dheeraj

The two backend runs are sequential. Parallel sessions are outside scope.

## Artifacts

- `approval.proposal.json`: exact paths, current immutable inputs, proposed connection/model choices, timeout budget, closed side-effect set, cleanup owner, and non-authorization.
- `host-evidence.template.json`: every required host-observed event for both runs. Defaults remain non-passing.
- `cleanup-receipt.template.json`: exact cleanup assertions. Defaults remain non-passing.
- `scripts/canary/craft-backend-canary.py`: validates packets, materializes immutable local fixtures, binds an externally supplied approval record to exact built bytes, checks imported host evidence for internal consistency, and observes local cleanup absence. Every result has `authorization_effect: none`; imported host exports remain unverified. It cannot create sessions, register workspaces, read credentials, publish, install, mutate GitHub, or delete anything.

## Preparation phase (safe before live approval)

After #1002 and #845 are independently accepted and integrated, update all four full revisions and all three content digests in the proposal from exact accepted `develop`. The proposal validator rejects live authorization while either prerequisite revision or exact package tree digest is absent.

Validate the proposal:

```bash
python3 scripts/canary/craft-backend-canary.py validate \
  --manifest examples/probe-matrices/craft-backend-canary/approval.proposal.json
```

Materialize the exact detached source, rebuilt Craft package, marker repository and local bare remote under the single temp root:

```bash
python3 scripts/canary/craft-backend-canary.py materialize \
  --manifest examples/probe-matrices/craft-backend-canary/approval.proposal.json
```

Materialization performs local-only side effects. It refuses an existing temp root or existing disposable workspace. Its receipt records exact source/package pins, source/candidate/remote refs, canonical package digest, exact post-build package-tree digest, `live_session_created: false`, and `credentials_read: false`.

Copy the proposal to an out-of-repository run manifest only after reviewing that receipt. Fill the exact materialized package digest and accepted provider/native integration revisions. After the user explicitly approves the complete immutable packet outside this file, record `status: approval-recorded`, the external source kind/reference, approver, time, and the SHA-256 of the packet with `operator_approval` excluded. Do not change paths, connections, models, limits, deadlines, or pins without a new external approval.

Then require a consistent external approval record and re-attest the already materialized bytes:

```bash
python3 scripts/canary/craft-backend-canary.py validate \
  --require-approval-record --manifest "$APPROVAL_RECORDED_MANIFEST"
python3 scripts/canary/craft-backend-canary.py attest-materialized \
  --manifest "$APPROVAL_RECORDED_MANIFEST"
```

The manifest and attestation digests identify the proposed run, but both remain non-authorizing records. The operator's direct instruction is the authority; the manifest cannot create it. Any byte or field change invalidates the recorded subject.

## Live phase (requires separate user authorization)

The driver deliberately has no launch command. Only after fresh direct user authorization naming the final packet may the operator create the exact disposable workspace through the normal Craft UI and run the two recorded connections in order. Do not attach GitHub, external sources, credentials, or messaging channels.

For each backend, collect host-native records—not model claims—for exactly these events:

1. `startup_resolver`: selected project/load-set paths and file digests observed by the host.
2. `prompt_hook`: marker-bearing prompt/event input and the host hook result.
3. `write_guard_allow`: one write inside the exact fixture/workspace allowlist and its before/after digest.
4. `write_guard_deny`: one attempted write outside the allowlist, with unchanged before/after state.
5. `git_push_allow`: one feature-ref push to the local bare remote, with remote before/after refs.
6. `git_push_deny`: one protected-ref or invalid-range push, with unchanged remote refs.
7. `resume_context`: host-observed resumed session identity and preserved marker.
8. `compaction_context`: host-observed compacted/restored marker state.
9. `no_op_detection`: a deliberately disconnected/no-op adapter whose absence must be reported rather than inferred as success.

Record timestamps so backend 2 starts only after backend 1 ends. Copy and complete `host-evidence.template.json` under the exact evidence root. The validator requires 18 externally exported, SHA-256-bound host-event records, exact backend identity/order, no overlap, and `model_self_report_used: false`. Structural success is reported only as `evidence-consistent-unverified`; imported, synthetic, or model-reported material never becomes verified host evidence:

```bash
python3 scripts/canary/craft-backend-canary.py validate-evidence \
  --manifest "$APPROVAL_RECORDED_MANIFEST" \
  --evidence /private/tmp/cc-1003-provider-canary-20261016/evidence/host-evidence.json
```

A green #1019 provider probe and required-protection state remain separate evidence. This canary cannot establish GitHub provider authority.

## Interrupt and cleanup

Stop immediately on timeout, identity mismatch, unexpected side effect, credential prompt, external network/source request, overlapping session, missing host event, or no-op falsely represented as active. Do not repair in place; record the failed observation and proceed to cleanup.

Cleanup order, owned by Dheeraj:

1. End/archive the two disposable sessions through the normal Craft UI.
2. Remove the exact disposable workspace through the normal Craft workspace path.
3. Remove only `/private/tmp/cc-1003-provider-canary-20261016`, including its local bare remote and refs.
4. Confirm no exact workspace or temp path remains and that `main`, protections, releases, installed packages, credentials, other workspaces and external systems are unchanged.
5. Preserve only redacted receipt/digest text in the reviewed issue/PR; preserve no credentials or prompt contents.

`verify-cleanup` performs no deletion. After cleanup, pipe a completed receipt over stdin so the receipt itself need not survive outside the allowlist:

```bash
python3 scripts/canary/craft-backend-canary.py verify-cleanup \
  --manifest "$APPROVAL_RECORDED_MANIFEST" --receipt - <<'JSON'
{ "schema_version": "1.0.0", "run_id": "cc-1003-provider-canary-20261016", "manifest_sha256": "REPLACE", "workspace_absent": true, "temp_root_absent": true, "disposable_refs_absent": true, "outside_allowlist_unchanged": true }
JSON
```

A run is not complete until evidence validation and cleanup verification both pass. Failure or interruption does not authorize retention, rollout, release, installation, `main` promotion, protection changes, or another run.
