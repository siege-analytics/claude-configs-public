# Self-review: #1003 fixture-local Claude project registration

Pre-mortem-artifact: plans/pre-mortem-1003-claude-project-registration.md
Hostile-review-artifact: plans/hostile-review-1003-claude-project-registration.md

## Assumptions

- Fresh ordinary Craft sessions created with the fixture repository as explicit working directory provide that repository as Claude SDK `sdkCwd`; imported/fallback/stale sessions are separate and cannot satisfy this proof.
- The reviewed payload, absolute workspace/temp roots and setup driver remain bound by the existing external approval subject and fresh materialization attestation.
- Fixture registration is configured preparation evidence only. Host registration, invocation and injected request-context records remain mandatory; Pi has no supported command/result adapter.

## Classification

Tier C. This code prepares the settings file a future Claude SDK process may consume and validates host-evidence claims. A false allow could claim enforcement that was never registered or invoked.

## Dependency closure

- Setup/registration authority: `scripts/canary/setup-disposable-workspace.py`
- Evidence and cleanup validation: `scripts/canary/craft-backend-canary.py`
- Real-file and isolated-home tests: `bin/_test/craft_backend_canary_test.py`
- Immutable driver pins: `examples/probe-matrices/craft-backend-canary/approval.proposal.json`
- Host evidence schema fixture: `examples/probe-matrices/craft-backend-canary/host-evidence.template.json`
- Cleanup schema fixture: `examples/probe-matrices/craft-backend-canary/cleanup-receipt.template.json`
- Operator procedure: `examples/probe-matrices/craft-backend-canary/README.md`

All executable paths are already covered by Tier C review-risk patterns. Generated risk/source-authority outputs must be refreshed before publication.

## Findings and corrections

- Direct fixture wiring was rejected because `wire-enforcement.py` derives its command root from the destination. The implementation wires only the exact workspace payload, validates the complete result, then copies identical bytes.
- Path-substring checks were insufficient. The implementation independently reconstructs the complete expected JSON from the pinned payload base snippet and pinned generated enforcement snippet, requires exact equality, parses every command, and accepts only one exact executable under the workspace.
- A target-appearance race could be overwritten by `os.replace`; the implementation uses a completed temporary file plus exclusive hard-link publication. It never deletes a race-created target.
- Independent review reproduced a parent-directory swap that made path-based `os.link` follow a replacement `.claude` symlink and write outside the fixture. Publication now holds no-follow fixture-parent/fixture/`.claude` descriptors, creates/links/checks/removes descriptor-relative, and rejects re-opened directory identity drift before linking. The exact swap reproducer now proves no outside `settings.json`, no success receipt and no temporary residue in the held directory.
- Read-only review found that the verifier parsed one settings read but originally returned the digest of a second unvalidated read. It now parses, validates, digests and returns one regular-file snapshot; a final inode/path/byte comparison can only reject drift. Real-file regressions mutate bytes and replace the inode with identical bytes between snapshot and handoff.
- A later source-change race could still publish stale bytes; registration re-reads and byte-compares the source immediately before publication.
- Workspace-only startup/no-op evidence could previously pass structural validation. Backend 1 must now bind the fixture destination path/digest from `workspace-setup.json`; those fields are forbidden on Pi.
- Cleanup previously relied only on parent temp-root absence, then accepted any SHA-shaped claimed settings digest. It now binds the preserved setup receipt digest, the setup-registered digest and an independently observed pre-removal digest; validation requires registered/observed equality and exact fixture settings absence before broader root absence.

## Evidence

- Fourteen focused tests pass with caller bytecode suppression absent.
- Real-file tests cover exact inventory, appended shell commands, foreign interpreters, foreign paths, extra groups, changed executable bytes, parse-to-handoff byte mutation, same-byte inode replacement, existing targets, symlinked `.claude`, target-appearance races, `.claude` parent rename/symlink redirection, source-change races, no outside/partial target, descriptor-relative cleanup and temporary-file cleanup.
- An end-to-end test runs materialize → attest → payload copy → real install/wire/verify → fixture registration → receipt under an isolated temporary `$HOME`; it creates no real Craft workspace.
- Evidence negatives reject the workspace assembly path and reject transfer of Claude registration fields to Pi.

## Peer review

Working-source review reproduced and then cleared two blockers: an unvalidated second settings read between parse and digest, and a parent-directory swap that redirected path-based publication outside the fixture. Exact committed-head independent review remains pending after draft publication.

## Lead review

The slice reuses the accepted install → wire → verify route and adds no second resolver, evaluator, lifecycle state or host adapter. Complete canonical settings equality and command vectors are checked before registration. Descriptor-relative publication and cleanup prevent replacement parents from redirecting writes or unlinks. Receipts remain non-authorizing and separate Claude configuration from Pi capability.

## Quantified claims

- Fourteen focused tests pass, including real byte/inode/source/target/parent interleavings and an isolated temporary-home end-to-end setup.
- The independent parent-swap reproducer changes from `accepted` with an outside write to `rejected` with no outside `settings.json`.
- Package generation 19/19, provider 11/11, native registration 16/16, all 33 Python test files and all 36 hook suites passed before the final descriptor fix; exact committed-head replay is required before draft handoff.
- Proposal validation remains non-authorizing and rejects missing external approval.

## Non-claims

`configured-unverified` is not host invocation, injected context, authorization, or Pi support. No live workspace/session, credentials, app patch, shared/default installation, provider mutation, release, deployment, `develop`, or `main` change is performed by this source review.

## Pending publication checks

Run build/freshness, full Python tests, all hook suites, workflow policy suites, scanner corpus, package/provider/native/protected-policy fixtures, whitespace and clean-tree checks. Publish a draft and obtain independent exact-head review before integration.
