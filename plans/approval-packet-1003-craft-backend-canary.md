# Approval packet: #1003 Craft/backend canary

## State: preparation proposal — not authorized

This packet is reviewable preparation only. One future live run requires accepted prerequisite integrations, final source/build/driver digests, exact materialization, independent review of the published head, and a later direct user instruction naming the immutable approval subject. A manifest may record that instruction but cannot create or verify its authority.

## Proposed immutable run

- ID: `cc-1003-provider-canary-20261016`
- Temp/source/evidence: `/private/tmp/cc-1003-provider-canary-20261016`
- Workspace: `/Users/dheerajchand/.craft-agent/workspaces/cc-1003-provider-canary-20261016`
- Sequence 1: `claude-max` / `claude-opus-4-8`
- Sequence 2: `chatgpt-plus` / `pi/gpt-5.5`
- Budgets: 900 seconds per backend; 180 transition; 300 cleanup; 2,400 overall
- Cleanup owner: Dheeraj

Current preparation pins are in `approval.proposal.json`. Exact materialized package bytes and external operator approval remain deliberately null. The proposal cannot pass `--require-approval-record`; all commands return `authorization_effect: none`.

## Prepared driver operations

1. `validate`: proposal paths, closed effects/limits, backend order, budgets and pins.
2. `materialize`: only the exact temp root, detached source, rebuilt outputs, strict-release composition, exact allowlisted workspace payload, canonical synthetic fixture over local transport, control markers, local bare remote and receipt; no Craft workspace/session.
3. `validate --require-approval-record`: checks a separately supplied approval record bound to the exact subject without granting authority.
4. `attest-materialized`: checks the existing exact source/package/fixture bytes.
5. `validate-evidence`: requires two sequential runs, exactly nine unique expected events each, unique confined artifact files with matching SHA-256, and recorded per-backend/transition/overall durations within the pinned budgets.
6. `verify-cleanup`: deletes nothing; checks a matching imported receipt and directly observes exact path absence.

## Future disposable setup boundary

After separate approval only, the operator may create and populate the named disposable workspace and register native hooks only in its local fixture repository. The separately digest-pinned `setup-disposable-workspace.py` copies only the exact materialized payload, rejects unexpected entries/symlinks/existing targets, invokes the reviewed hook/wiring/verifier tools, and forbids a production deploy stamp. Immediately before mutation it reruns the shared attestation over exact source HEAD/full clean tree, package, composition, payload, canonical fixture origin and exact local bare push transport; `workspace-setup.json` binds that fresh receipt. Materialization and attestation independently invoke the canonical final-payload hook and require one canonical kernel, one byte-identical strict-release resident, both scoped skills and no controls. It does not call production `build.py --deploy` or weaken canonical `KERNEL.md` validation. This does not permit shared/default workspace changes, global/persistent installation, standing-order automations, sources, credentials, messaging, provider mutation, release, `main` or protection changes; live host registration/request-context evidence still requires separate run-specific approval.

## Literal run and evidence acquisition

The runbook at `examples/probe-matrices/craft-backend-canary/README.md` contains:

- exact UI workspace/session names, connections, models and working directory;
- nine literal marker-bearing prompts per backend;
- selected strict-release resident/skill content with foreign/global injection controls;
- allowed and denied write/push probes confined to disposable state, including mandatory native commit trailers;
- resume, host compaction and deliberate missing/no-op probes;
- exact session-log discovery by visible title;
- deterministic extraction of one host-log slice per marker;
- artifact paths/digests matching `host-evidence.template.json`;
- timeout, interrupt, stop and cleanup commands.

Assistant/model assertions are never evidence. Every event must have a host-native artifact file. Imported host exports remain `evidence-consistent-unverified`; structural validation cannot authenticate provenance or establish provider/runtime authorization.

## Closed side effects

Only the exact disposable workspace/temp root, its pinned-source deployment, hook registration in that workspace and fixture repository, local bare remote/disposable refs, host metadata artifacts and exact cleanup are permitted. Shared/persistent installation, credentials, external systems/messages, `main`, protections and releases remain prohibited.

## Stop and cleanup

Any timeout, identity mismatch, absent host record, credential prompt, external request, overlap, unexpected write/ref mutation or false no-op stops the run. Do not repair in place or continue to backend 2. End/archive disposable sessions, delete only the exact workspace through the UI, delete only the exact temp root, verify real absence and unchanged external state, and retain only redacted receipt/digest text.

## Authorization decision requested later

Do **not** authorize from this document. The later request will name accepted integration SHAs, exact proposal/source/package/driver/attestation digests, reviewed PR head, materialization receipt and final commands. Only a direct user instruction naming that immutable subject may authorize one run. Replacement bytes or identities require a new request.
