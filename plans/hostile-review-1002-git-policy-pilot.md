# Hostile review: #1002 exact Git policy pilot

## Attack surface

- mutable candidate policy, helper, workflow and generated package;
- stale or substituted candidate head/range;
- interior commits and merges;
- `--no-verify`, file-based messages, aliases and command chains;
- wrong repository, fork origin and host/port aliases;
- configured composition and unauthenticated capability values presented as authorization.

## Findings replayed

### Port alias collapsed into approved host

Initial URI parsing used `urlsplit(...).hostname`, which discarded a non-default port. `https://github.example.invalid:8443/synthetic-org/strict-release.git` could therefore resolve as the approved host. The adapter now rejects every explicit port, keeps canonical target separate from candidate source and requires exact equality for this same-repository pilot. A focused regression reproduces the former case.

### Candidate source confused with canonical target

A fork checkout's origin is the source repository, not the protected target. The adapter now accepts a distinct canonical target input for later binding to authenticated event data, derives source identity from the candidate origin, and rejects all fork/source differences in the bounded pilot. Local caller input remains non-authoritative because no local result can return final allow.

### Receipt-only generated agreement

The installed receipt is configured evidence, not artifact authorization. The adapter checks project identity, selected policy, effective values, parent lock, configured state and final `unknown`; stale, absent and mixed-lock receipts reject. It exposes parent/effective identities for #1004, but #852's immutable output identity remains separately required before artifact activation.

### Default-branch workflow source bypassed the adapter

Disposable #1019 head `14006b10e084393afb109d46d988295f110625ee` intentionally omitted ticket evidence, but hosted `pull_request_target` run `38861456348` passed without an adapter step. GitHub has sourced this event's workflow/ref from default branch `main` since 2025-12-08; the integrated develop YAML was never executed. The repair preserves the already registered topology step and moves adapter invocation behind the exact base's trusted topology entrypoint. Receipts now distinguish actual `GITHUB_WORKFLOW_REF`/`GITHUB_WORKFLOW_SHA`/workflow blob from the exact-base entrypoint and validator blobs.

### Portable event parsing

The first repair used Bash 4 `mapfile`; macOS Bash 3 failed before evaluation. Exact event parsing now uses portable `read` with validated tab-delimited fields. The registered-path fixture reproduces host event identities on both the local review environment and Linux CI.

## Remaining deliberate boundaries

- This checkpoint does not prove that the repaired provider path ran or is required for merge. The user's subsequent #1019 negative/replacement-head probe must produce the structured receipt and separately record actual ruleset/protection state.
- Fork PRs are unsupported and reject rather than guessing policy target/source relationships.
- Installed content authenticity is not inferred from its configured composition receipt; #852/#1004 bind exact output identities.
- The old authoritative guard remains until later-hosted evidence exists.
