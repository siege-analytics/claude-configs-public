# Approval packet: #1003 Craft/backend canary

## State: preparation proposal — not authorized

This packet becomes reviewable for one live run only after accepted #1002/#845 revisions and final `develop` source/build/script digests replace the current proposal pins, materialization records exact built bytes, an independent reviewer accepts the exact source head, and the user directly approves the immutable subject. The manifest may record that external instruction but cannot create or verify its authority.

## Proposed immutable run

- ID: `cc-1003-provider-canary-20261016`
- Temp/source/evidence: `/private/tmp/cc-1003-provider-canary-20261016`
- Workspace: `/Users/dheerajchand/.craft-agent/workspaces/cc-1003-provider-canary-20261016`
- Sequence 1: `claude-max` / `claude-opus-4-8`
- Sequence 2: `chatgpt-plus` / `pi/gpt-5.5`
- Per backend: 900 seconds; transition: 180; cleanup: 300; overall: 2,400
- Cleanup owner: Dheeraj

Current immutable preparation pins in `approval.proposal.json` are:

- accepted provider head `9b541dff6452b4782a732356d3e1089e828f9293`, integrated as `b97c99dfce05ca6f5f6e8fe7839b9dc2585065a8`;
- accepted native head `0fa16ce6a07b1083a31d80a3f40dd5dbf1639744`, integrated in `develop@cd014600d7262492c7ce95512ba308b307a8efa5`;
- source-tree SHA-256 `42ea856dbd140e8445c611bf55dc0f6acd9c90852d85f07d93fad8a0626421bf`;
- canonical Craft package SHA-256 `49acf0788df5fe33582e4b35eda226544909e1232a6215682545c5859adb5d2c`;
- approval driver SHA-256 `bf3feb5f37c1b34fe4542932d865654ccfe5b391f90759daf8170edbca188f4b`.

Exact materialized package bytes and external operator approval remain deliberately null. The proposal cannot pass `--require-approval-record` and no script result can grant live authority.

## Prepared commands

1. `validate`: validates proposal structure, exact paths, closed effects, backend sequence, deadlines and current pins.
2. `materialize`: creates only the exact temp root; detached exact source, rebuilt package, marker repository, local bare remote and receipt. It refuses pre-existing roots and does not create a Craft workspace/session.
3. `validate --require-approval-record`: checks that a separately supplied operator instruction is recorded against the exact packet subject; it returns `authorization_effect: none`.
4. `attest-materialized`: binds that record to existing exact source/package/fixture bytes while remaining non-authorizing.
5. `validate-evidence`: checks two sequential imported backend records for all nine digest-bound events and unchanged external state, returning `evidence-consistent-unverified`.
6. `verify-cleanup`: deletes nothing; it checks a matching imported receipt and directly observes exact local path absence without treating the receipt as verified authority.

## Planned observations

Each backend must yield an external host export for startup resolution, prompt-hook invocation, allowed/denied writes, allowed/denied local pushes, resume, compaction and deliberate no-op detection. The driver can validate structure/digests but cannot authenticate imported host provenance. Model and synthetic records are excluded from host claims. Provider activation and required protection remain #1019/#1002 evidence, not canary output.

## Closed side effects

Only the exact workspace/temp root, local bare remote/disposable refs, host metadata receipts and their exact cleanup are permitted. Credentials, external sources/messages, `main`, protections, releases, installations, other workspaces and parallel sessions are prohibited.

## Stop and cleanup

Any identity mismatch, timeout, unexpected side effect, credential prompt, external request, overlap, missing host event or false no-op success stops the run. End/archive sessions through the UI, remove the exact workspace through the normal path, remove the exact temp root, then verify workspace/temp/refs absent and external state unchanged. Retain only redacted digests.

## Authorization decision requested later

Do **not** authorize from this document. The final request will include: accepted integration SHAs, exact proposal/source/package/driver/attestation digests, reviewed source PR head, materialization receipt, final commands, and a request for one direct user instruction naming that immutable subject. Only after that instruction may its source/reference be recorded. Any replacement byte or identity requires a new request.
