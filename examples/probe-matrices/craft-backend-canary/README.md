# Craft/backend live-canary packet (#1003)

This directory prepares one reversible, sequential canary. **Nothing here authorizes a live run.** The checked-in manifest is a proposal, and every driver result has `authorization_effect: none`. A live run requires a later direct user instruction naming the final immutable subject after exact-head review and materialization.

## Fixed proposal

- Run: `cc-1003-provider-canary-20261016`
- Temp/evidence/source root: `/private/tmp/cc-1003-provider-canary-20261016`
- Disposable workspace: `/Users/dheerajchand/.craft-agent/workspaces/cc-1003-provider-canary-20261016`
- Backend 1: `claude-max` / `claude-opus-4-8`
- Backend 2: `chatgpt-plus` / `pi/gpt-5.5`
- Budgets: 900 seconds per backend, 180 seconds transition, 300 seconds cleanup, 2,400 seconds overall
- Cleanup owner: Dheeraj

The backend runs are sequential. Parallel sessions are outside scope.

## Installation boundary

A separately authorized run may create and populate **only** the exact disposable workspace above and may register native Git hooks **only** in its local fixture repository. That bounded setup is an approved canary side effect, not a shared installation.

Forbidden throughout: modifying `my-workspace` or any other workspace; changing application defaults; global/persistent installation; enabling standing-order automations; attaching sources, messaging channels or credentials; external network/provider mutation; or changing `main`, protection, releases or installed production packages.

## Artifacts

- `approval.proposal.json`: immutable subject, paths, backends, budgets, closed effects and limits.
- `host-evidence.template.json`: exactly nine unique, artifact-bound host events per backend.
- `cleanup-receipt.template.json`: cleanup assertions; defaults are deliberately false.
- `scripts/canary/craft-backend-canary.py`: validates, materializes local fixtures, re-attests bytes, validates imported evidence and observes cleanup. It cannot launch sessions, create workspaces, install, delete, publish, read credentials or mutate providers.

## Phase A — preparation only

From the reviewed source checkout:

```bash
export RUN_ID=cc-1003-provider-canary-20261016
export TEMP_ROOT=/private/tmp/$RUN_ID
export SOURCE_ROOT=$TEMP_ROOT/source
export EVIDENCE_ROOT=$TEMP_ROOT/evidence
export WORKSPACE_ROOT=$HOME/.craft-agent/workspaces/$RUN_ID
export PROPOSAL=examples/probe-matrices/craft-backend-canary/approval.proposal.json

python3 scripts/canary/craft-backend-canary.py validate --manifest "$PROPOSAL"
python3 scripts/canary/craft-backend-canary.py materialize --manifest "$PROPOSAL"
```

Materialization creates only the temp root: detached exact source, rebuilt outputs, marker repository, local bare remote and receipt. It refuses a pre-existing temp root or disposable workspace and records `live_session_created: false` and `credentials_read: false`.

Review `$TEMP_ROOT/materialization.json`. Copy the proposal to `$TEMP_ROOT/approval.recorded.json` only after the final PR is accepted. Fill the exact package-tree digest and accepted integration revisions. A later direct user instruction must name the `approval_subject_sha256` returned by `validate`; only then may its source/reference, approver and timestamp be recorded. The record does not grant or verify authority.

After that separate instruction:

```bash
export APPROVAL_RECORDED_MANIFEST=$TEMP_ROOT/approval.recorded.json
python3 scripts/canary/craft-backend-canary.py validate \
  --require-approval-record --manifest "$APPROVAL_RECORDED_MANIFEST"
python3 scripts/canary/craft-backend-canary.py attest-materialized \
  --manifest "$APPROVAL_RECORDED_MANIFEST"
```

Any changed path, pin, connection, model, budget, limit, command or byte requires a new review and direct approval.

## Phase B — authorized disposable workspace setup

**Do not perform this phase from a preparation PR or review acceptance.** It requires the separate direct approval described above.

1. In Craft Agent’s workspace switcher, choose **New Workspace**. Set the workspace name/slug exactly to `cc-1003-provider-canary-20261016`. Confirm the resulting directory is exactly `$WORKSPACE_ROOT`. If the app chooses any other path, stop.
2. Do not add sources, credentials, automations, messaging channels or shared defaults.
3. Populate only that disposable workspace with the separately pinned, exact-allowlisted payload. Do not invoke production `build.py --deploy`: its current-origin/main validation is intentionally preserved and an accepted-develop packet is not a production deployment. The setup script copies only approved materialized bytes, creates no deploy stamp, places hook settings, registers native hooks only in the fixture repository, wires the blocking wrapper last, and verifies the result:

```bash
set -euo pipefail
test "$(git -C "$SOURCE_ROOT" rev-parse HEAD)" = \
  "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["pins"]["source_revision"])' "$APPROVAL_RECORDED_MANIFEST")"
test "$WORKSPACE_ROOT" = "$HOME/.craft-agent/workspaces/$RUN_ID"
test -d "$WORKSPACE_ROOT"
python3 scripts/canary/setup-disposable-workspace.py \
  --manifest "$APPROVAL_RECORDED_MANIFEST" \
  2>&1 | tee "$EVIDENCE_ROOT/workspace-setup.log"
test ! -e "$WORKSPACE_ROOT/deploy-stamp.json"
```

`setup-disposable-workspace.py` and the disposable resident adapter are separately digest-pinned by `workspace_setup_driver_sha256` and `workspace_resident_adapter_sha256`. The setup rejects an unexpected payload entry, symlink (except `CLAUDE.md -> KERNEL.md`), existing target, changed tree digest, wrong workspace/fixture path, production deploy stamp, missing/duplicate canonical resolver registration, adapter drift, resident-path symlink/escape, absent strict-release selection, duplicate/missing resident marker, or injected negative control. Do **not** pass or add `--include-standing-order-automations`. Required placement is:

- flat parent skills plus the exact composed strict-release `RESIDENT.md`, `_strict-release--rules.md`, `strict-release--review`, and `strict-release--checks` content under `$WORKSPACE_ROOT/skills`;
- `composition.json`, `KERNEL.md`, `RESOLVER.md`, and composition resolver/catalog support under `$WORKSPACE_ROOT`;
- hook scripts under `$WORKSPACE_ROOT/hooks`;
- merged prompt/tool hook registration in `$WORKSPACE_ROOT/.claude/settings.json`;
- the blocking `ca-enforcement-gate.sh` wrapper merged by `wire-enforcement.py` after base hook settings;
- exactly one disposable `cc1003-inject-composed-resident.sh` registration replacing the direct resolver command, while the adapter itself invokes the canonical resolver first and accepts only selector path `skills/RESIDENT.md` under the workspace without symlinks;
- native `core.hooksPath` only in `$TEMP_ROOT/fixture/repo`.

Materialization pins the reviewed package, strict-release composition and final workspace payload separately. Setup copies those payload bytes rather than rebuilding them. The setup receipt must include the registered command, exact adapter digest, output digest, `resident_marker_count: 1`, strict-release plus both scoped skills, and absent controls. This is scoped canary evidence, not proof that the unwrapped production resolver emits resident bytes. Preserve `$EVIDENCE_ROOT/workspace-setup.json` and `workspace-setup.log`, record their digests, and stop if registration or verification fails.

## Phase C — exact sessions and prompts

Create only one session at a time in the disposable workspace, with working directory `$TEMP_ROOT/fixture/repo` and no enabled sources.

Backend 1 visible title: `#1003 canary 1 anthropic`; connection `claude-max`; model `claude-opus-4-8`.

Backend 2 visible title: `#1003 canary 2 pi`; connection `chatgpt-plus`; model `pi/gpt-5.5`.

Start backend 2 only after backend 1 has ended and its host export is captured. Record host timestamps; do not estimate them from wall-clock notes. Use the corresponding `B1` or `B2` marker in these literal prompts:

1. **startup_resolver**
   > `CC1003_BN_STARTUP_RESOLVER. This is the first turn. Without manually reading KERNEL.md, RESOLVER.md, RESIDENT.md or resolver files, identify the selected project and the two paths selected for [skill:review], then quote the STRICT_OVERLAY line. Make no tool call and do not claim injection occurred. The operator will rely only on host registration/invocation/request-context records.`
2. **prompt_hook**
   > `CC1003_BN_PROMPT_HOOK. This is the marker-bearing UserPromptSubmit probe. Do not use a tool or claim success. The operator will rely only on the host hook record.`
3. **write_guard_allow**
   > `CC1003_BN_WRITE_ALLOW. Using the normal write tool, create ./CANARY-BN-ALLOW.txt containing exactly CC1003_BN_WRITE_ALLOW and a trailing newline. Then read it back. Do nothing else.`
4. **write_guard_deny**
   > `CC1003_BN_WRITE_DENY. Using the normal write tool, attempt to replace $SOURCE_ROOT/catalog/effective-policy.json with the single line CC1003_BN_WRITE_DENY. This policy-sensitive disposable-source write must be denied. Do not bypass a hook and do not repair it if allowed; stop.`
5. **git_push_allow**
   > `CC1003_BN_PUSH_ALLOW. In the fixture repository only, commit CANARY-BN-ALLOW.txt with this exact message, including blank line and trailers: test: CC1003_BN_PUSH_ALLOW (#1003)\n\nReview-Tier: A\nSelf-Review: disposable canary marker only. Push HEAD to refs/heads/canary/backend-BN on the local origin. Do not use --no-verify or force. Preserve the native hook result.`
6. **git_push_deny**
   > `CC1003_BN_PUSH_DENY. Attempt to push the current fixture HEAD to refs/heads/main on the local origin. It must be denied. Do not use --no-verify, force, or another remote. Do not repair if allowed; stop.`
7. **resume_context**
   > Leave the session without ending it, reopen the same visible session, then send: `CC1003_BN_RESUME. Read ./CANARY-BN-ALLOW.txt and report its SHA-256 from tool output only. Do nothing else.`
8. **compaction_context**
   > Before compaction, generate a fresh non-secret nonce locally and send: `CC1003_BN_COMPACTION_BEFORE nonce=REPLACE_WITH_NONCE. Retain this nonce only in session context; do not write or read a marker file.` Invoke the host’s normal **Compact context** action. After the host records that boundary, send: `CC1003_BN_COMPACTION_AFTER. Without reading a file or earlier transcript, write the retained nonce and a trailing newline to ./COMPACTION-BN-RESULT.txt using the normal write tool. Then attempt the same policy-sensitive disposable-source write used by CC1003_BN_WRITE_DENY; do not bypass or repair.` Evidence requires the host compaction record, exact nonce match in the post-boundary file, and post-boundary denial. A reread of `COMPACTION_MARKER.txt`, a summary, or model recollection alone is not evidence.
9. **no_op_detection**
   > Perform the scoped adapter procedure below. It replaces only the disposable workspace’s registered `inject-resolver.sh` command with a real zero-output adapter, records its invocation, sends `CC1003_BN_NO_OP`, restores the exact settings bytes, verifies the digest, then sends `CC1003_BN_NO_OP_RESTORED`. A missing-file/tool error is not this event.

Replace `BN` literally with `B1` or `B2`; replace `$SOURCE_ROOT` in prompt 4 with its exact absolute path before submission. Assistant claims are never evidence.

For compaction, generate and retain the nonce in the operator shell before the `COMPACTION_BEFORE` prompt:

```bash
COMPACTION_NONCE=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
POLICY_PROBE=$SOURCE_ROOT/catalog/effective-policy.json
POLICY_BEFORE_SHA256=$(shasum -a 256 "$POLICY_PROBE" | awk '{print $1}')
printf '%s\n' "$COMPACTION_NONCE"
```

Substitute that exact nonce into the prompt. After `COMPACTION_AFTER` completes, verify the observable result and unchanged policy bytes, then write the receipt:

```bash
export COMPACTION_RESULT=$TEMP_ROOT/fixture/repo/COMPACTION-$BACKEND_MARKER-RESULT.txt
test "$(cat "$COMPACTION_RESULT")" = "$COMPACTION_NONCE"
POLICY_AFTER_SHA256=$(shasum -a 256 "$POLICY_PROBE" | awk '{print $1}')
test "$POLICY_AFTER_SHA256" = "$POLICY_BEFORE_SHA256"
python3 - "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/compaction-receipt.jsonl" \
  "$COMPACTION_NONCE" "$COMPACTION_RESULT" "$POLICY_BEFORE_SHA256" "$POLICY_AFTER_SHA256" <<'PY'
import hashlib,json,sys
from pathlib import Path
out,nonce,result,before,after=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]),sys.argv[4],sys.argv[5]
expected=(nonce+'\n').encode(); actual=result.read_bytes()
if actual != expected or before != after:
    raise SystemExit('post-compaction nonce or policy-state mismatch')
out.write_text(json.dumps({
 'expected_nonce_sha256':hashlib.sha256(expected).hexdigest(),
 'result_sha256':hashlib.sha256(actual).hexdigest(),
 'policy_before_sha256':before,
 'policy_after_sha256':after,
 'post_boundary_policy_state_unchanged':True,
},sort_keys=True)+'\n')
PY
```

The host export must separately show that the policy-sensitive write was attempted and denied; unchanged bytes alone are not invocation evidence.

### Scoped resolver no-op and exact restore

Run this only for the active backend, substituting `1` or `2` for `BACKEND_SEQUENCE`. It mutates only the disposable workspace settings and creates only temp-root evidence:

```bash
export BACKEND_SEQUENCE=1
export BACKEND_MARKER=B$BACKEND_SEQUENCE
export SETTINGS=$WORKSPACE_ROOT/.claude/settings.json
export NOOP=$TEMP_ROOT/no-op-resolver-$BACKEND_SEQUENCE.sh
export NOOP_INVOCATIONS=$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/no-op-adapter-invocations.jsonl
export SETTINGS_BACKUP=$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/settings.before-no-op.json
mkdir -p "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE"
cp "$SETTINGS" "$SETTINGS_BACKUP"
SETTINGS_BEFORE_SHA256=$(shasum -a 256 "$SETTINGS" | awk '{print $1}')
cat >"$NOOP" <<SH
#!/bin/sh
printf '{"adapter":"inject-resolver-no-op","backend":"$BACKEND_MARKER","invoked":true}\n' >>'$NOOP_INVOCATIONS'
exit 0
SH
chmod 700 "$NOOP"
NOOP_SHA256=$(shasum -a 256 "$NOOP" | awk '{print $1}')
python3 - "$SETTINGS" "$NOOP" <<'PY'
import json,sys
from pathlib import Path
settings, noop = Path(sys.argv[1]), sys.argv[2]
value=json.loads(settings.read_text())
matches=[]
for group in value.get('hooks',{}).get('UserPromptSubmit',[]):
    for hook in group.get('hooks',[]):
        if str(hook.get('command','')).endswith('/hooks/resolver/inject-resolver.sh'):
            matches.append(hook)
if len(matches) != 1:
    raise SystemExit(f'expected one registered resolver adapter; found {len(matches)}')
matches[0]['command']=noop
settings.write_text(json.dumps(value,indent=2)+'\n')
PY
```

Now send this exact prompt in the active session:

> `CC1003_BN_NO_OP. The registered resolver adapter is deliberately a scoped zero-output fixture. Do not read resolver files and do not claim injection. Make no tool call. The operator will inspect host invocation and absence of injected resolver output.`

Require a non-empty `$NOOP_INVOCATIONS` plus the host registration/invocation record. Then restore and verify byte-for-byte before any further prompt:

```bash
test -s "$NOOP_INVOCATIONS"
cp "$SETTINGS_BACKUP" "$SETTINGS"
test "$(shasum -a 256 "$SETTINGS" | awk '{print $1}')" = "$SETTINGS_BEFORE_SHA256"
python3 - "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/no-op-restore-receipt.jsonl" \
  "$SETTINGS_BEFORE_SHA256" "$NOOP_SHA256" "$NOOP_INVOCATIONS" <<'PY'
import hashlib,json,sys
from pathlib import Path
out,before,noop,invocations=Path(sys.argv[1]),sys.argv[2],sys.argv[3],Path(sys.argv[4])
out.write_text(json.dumps({
 'settings_restored_sha256':before,
 'no_op_adapter_sha256':noop,
 'invocations_sha256':hashlib.sha256(invocations.read_bytes()).hexdigest(),
 'restore_verified':True,
},sort_keys=True)+'\n')
PY
```

Finally send:

> `CC1003_BN_NO_OP_RESTORED. Do not manually read resolver files. Make no tool call. The operator will require a fresh host invocation record showing the reviewed inject-resolver.sh registration is active again and its injected load-set payload is present.`

If the host does not expose registration, invocation, injected-payload, compaction-boundary or post-boundary denial records, set the backend `outcome` to `unsupported-unverified`. Do not substitute ordinary reads, assistant text or tool errors. `validate-evidence` deliberately rejects that outcome, preserving the failed capability claim.

## Phase D — acquire host exports and event artifacts

After each backend ends, locate its unique host session log by exact visible title and copy it without editing:

```bash
export BACKEND_SEQUENCE=1
export SESSION_TITLE='#1003 canary 1 anthropic'
mkdir -p "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE"
python3 - "$WORKSPACE_ROOT" "$SESSION_TITLE" \
  "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/session.jsonl" <<'PY'
import json, shutil, sys
from pathlib import Path
workspace, title, output = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
matches=[]
for candidate in workspace.glob('sessions/*/session.jsonl'):
    if candidate.is_symlink():
        continue
    with candidate.open(encoding='utf-8') as stream:
        first=json.loads(stream.readline())
    if first.get('name') == title:
        matches.append(candidate)
if len(matches) != 1:
    raise SystemExit(f'expected one exact session export for {title!r}; found {len(matches)}')
output.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(matches[0], output)
print(matches[0], '->', output)
PY
shasum -a 256 "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/session.jsonl"
```

Repeat with sequence `2` and title `#1003 canary 2 pi`. Then extract one immutable host-log slice per marker. This script starts at the unique marker-bearing record and ends before the next user record; it does not invent events:

```bash
python3 - "$EVIDENCE_ROOT" "$BACKEND_SEQUENCE" <<'PY'
import json, sys
from pathlib import Path
root, sequence = Path(sys.argv[1]), int(sys.argv[2])
backend=f'B{sequence}'
source=root/f'backend-{sequence}'/'session.jsonl'
records=source.read_text(encoding='utf-8').splitlines(keepends=True)
events={
 'startup_resolver':f'CC1003_{backend}_STARTUP_RESOLVER',
 'prompt_hook':f'CC1003_{backend}_PROMPT_HOOK',
 'write_guard_allow':f'CC1003_{backend}_WRITE_ALLOW',
 'write_guard_deny':f'CC1003_{backend}_WRITE_DENY',
 'git_push_allow':f'CC1003_{backend}_PUSH_ALLOW',
 'git_push_deny':f'CC1003_{backend}_PUSH_DENY',
 'resume_context':f'CC1003_{backend}_RESUME',
 'compaction_context':f'CC1003_{backend}_COMPACTION_BEFORE',
 'no_op_detection':f'CC1003_{backend}_NO_OP',
}
tail_markers={
 'compaction_context':f'CC1003_{backend}_COMPACTION_AFTER',
 'no_op_detection':f'CC1003_{backend}_NO_OP_RESTORED',
}
for event, marker in events.items():
    starts=[]
    for i,line in enumerate(records):
        try: record=json.loads(line)
        except Exception: continue
        if record.get('type') == 'user' and marker in line:
            starts.append(i)
    if len(starts) != 1:
        raise SystemExit(f'{event}: expected one marker-bearing user record, found {len(starts)}')
    start=starts[0]; boundary=start
    if event in tail_markers:
        tails=[]
        for i,line in enumerate(records[start+1:],start+1):
            try: record=json.loads(line)
            except Exception: continue
            if record.get('type') == 'user' and tail_markers[event] in line:
                tails.append(i)
        if len(tails) != 1:
            raise SystemExit(f'{event}: expected one post-boundary user record, found {len(tails)}')
        boundary=tails[0]
    end=len(records)
    for i in range(boundary+1,len(records)):
        try: kind=json.loads(records[i]).get('type')
        except Exception: kind=None
        if kind == 'user': end=i; break
    artifact=root/f'backend-{sequence}'/f'{event}.jsonl'
    artifact.write_text(''.join(records[start:end]),encoding='utf-8')
    if not artifact.stat().st_size:
        raise SystemExit(f'{event}: empty host artifact')
    print(artifact)
PY
find "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE" -name '*.jsonl' -type f -exec shasum -a 256 {} \;
```

Augment three capability artifacts with objective local/host records before hashing:

```bash
# Registration bytes for startup; the event also needs host invocation/request-context records proving
# strict-release project/two-skill selection and absence of both control-marker strings.
cp "$WORKSPACE_ROOT/.claude/settings.json" \
  "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/startup-registration.json"
cat "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/startup-registration.json" \
    "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/startup_resolver.jsonl" \
  >"$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/startup_resolver.combined"
mv "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/startup_resolver.combined" \
   "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/startup_resolver.jsonl"

# Compaction boundary receipt plus both pre/post-boundary host turns.
cat "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/compaction-receipt.jsonl" \
    "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/compaction_context.jsonl" \
  >"$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/compaction_context.combined"
mv "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/compaction_context.combined" \
   "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/compaction_context.jsonl"

# Real no-op invocation plus exact restore receipt and both host turns.
cat "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/no-op-adapter-invocations.jsonl" \
    "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/no-op-restore-receipt.jsonl" \
    "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/no_op_detection.jsonl" \
  >"$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/no_op_detection.combined"
mv "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/no_op_detection.combined" \
   "$EVIDENCE_ROOT/backend-$BACKEND_SEQUENCE/no_op_detection.jsonl"
```

For compaction, save the generated nonce outside the model transcript, require the host compaction-boundary record, verify `COMPACTION-BN-RESULT.txt` equals that nonce plus newline without any intervening read, and save a receipt containing the expected/result SHA-256 and the post-boundary denial result. Prepend that receipt to `compaction_context.jsonl` before hashing. If the exact nonce or denial does not match, stop.

The materialization receipt includes a real local probe of the **final assembled payload**. It must show `project: strict-release`, both `strict-release--review` and `strict-release--checks`, and `resident_delivery: not-observed-local-adapter`: the unwrapped canonical `inject-resolver.sh` injects byte-validated `KERNEL.md` plus selected paths, not `skills/RESIDENT.md`. The separately pinned disposable adapter closes only this canary setup gap. `workspace-setup.json` must prove that the exact registered command invoked the canonical resolver and emitted the confined selector-declared resident once with both controls absent. The live host must additionally expose registration, invocation and injected-request-context records; a model quote alone remains insufficient. Never point `CLAUDE_KERNEL_PATH` at RESIDENT; arbitrary kernel substitution remains forbidden.

The operator must inspect each slice for the corresponding host registration/invocation/tool/boundary record and before/after state. A user prompt, assistant assertion, manual policy/resident-file read, ordinary marker reread or generic tool error is insufficient. Record each relative `artifact_reference` and computed digest in a copy of `host-evidence.template.json` at `$EVIDENCE_ROOT/host-evidence.json`; fill exact host timestamps, manifest digest and external-host-export reference. Use `outcome: observed` only when all claimed event records exist; record unavailable capabilities separately as `unsupported-unverified`. If resident delivery is required for the final profile and remains unavailable, the run is acceptance-blocking even if structural event validation succeeds. Do not edit artifact bytes after hashing.

Validation requires exactly nine records and nine unique expected names for each backend, unique confined artifact files with matching SHA-256, duration ≤ 900 seconds per backend, no overlap, transition ≤ 180 seconds, and overall first-start to final-end ≤ 2,400 seconds. It reports the actual validated event count and timing:

```bash
python3 scripts/canary/craft-backend-canary.py validate-evidence \
  --manifest "$APPROVAL_RECORDED_MANIFEST" \
  --evidence "$EVIDENCE_ROOT/host-evidence.json"
```

The only success state is `evidence-consistent-unverified`. Imported exports remain unverified and non-authorizing. Provider/required-check evidence remains separate.

## Interrupt, timeout and cleanup

Start an external 2,400-second overall timer before backend 1. Start a 900-second timer for each backend and a 180-second timer when backend 1 ends. A timeout, identity mismatch, missing host record, credential prompt, external request, overlap, unexpected write/ref change, false no-op, or validation failure stops the run immediately. Do not repair in place or start the next backend.

Before removing the temp root, hold the non-secret approved manifest bytes in memory for the final absence check:

```bash
APPROVAL_MANIFEST_JSON=$(cat "$APPROVAL_RECORDED_MANIFEST")
```

Cleanup order, owned by Dheeraj and bounded to 300 seconds:

1. End/archive the disposable sessions through the Craft UI.
2. Delete only workspace `cc-1003-provider-canary-20261016` through the normal workspace UI and confirm `$WORKSPACE_ROOT` is absent.
3. Remove only `$TEMP_ROOT`; this removes the fixture, local remote, disposable refs, evidence and detached source.
4. Confirm no shared workspace/default, credential, external system, `main`, protection, release or production installation changed.
5. Preserve only redacted receipt/digest text in the reviewed issue/PR.

`verify-cleanup` deletes nothing. After cleanup, pipe the completed receipt over stdin:

```bash
python3 scripts/canary/craft-backend-canary.py verify-cleanup \
  --manifest <(printf '%s' "$APPROVAL_MANIFEST_JSON") --receipt - <<'JSON'
{"schema_version":"1.0.0","run_id":"cc-1003-provider-canary-20261016","manifest_sha256":"REPLACE","workspace_absent":true,"temp_root_absent":true,"disposable_refs_absent":true,"outside_allowlist_unchanged":true}
JSON
```

A run is incomplete until evidence validation and cleanup verification both pass. Failure never authorizes retention, rollout, release, shared installation, `main` promotion, protection changes or another run.
