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

## Remaining deliberate boundaries

- This checkpoint does not prove that a host invoked the adapter or required its result for merge. #1003 must use a subsequent PR after the base-controlled workflow exists and record actual ruleset/protection state.
- Fork PRs are unsupported and reject rather than guessing policy target/source relationships.
- Installed content authenticity is not inferred from its configured composition receipt; #852/#1004 bind exact output identities.
- The old authoritative guard remains until later-hosted evidence exists.
