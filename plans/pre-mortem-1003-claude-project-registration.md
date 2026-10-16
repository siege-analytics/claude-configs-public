# Pre-mortem: #1003 fixture-local Claude project registration

## Scope

Preparation-source only: register the already-wired, verified workspace settings bytes at the disposable fixture repository path resolved from a fresh ordinary Claude session's `sdkCwd`. No live setup, session, approval, host patch, Pi adapter, provider mutation, release, deployment, or `main` change.

## Failure modes

1. **Wrong settings root** — wiring directly at the fixture makes commands point at absent fixture hooks.
   - Prevention: wire only in the exact copied workspace payload; byte-copy the verified final settings to the fixture.
2. **Substring validation accepts a shell substitution** — a command can contain the expected path plus an appended command, interpreter, or foreign argument.
   - Prevention: reconstruct the full expected settings object from both canonical artifacts, require exact object equality, parse each command with `shlex`, and require one exact executable.
3. **Registered executable differs from the pinned payload** — correct-looking paths can address changed bytes.
   - Prevention: require regular executable files under the workspace, map each to the same payload-relative file, and require byte identity plus SHA-256 inventory.
4. **Conflict, symlink or parent swap redirects publication** — setup silently merges/replaces operator state or follows a raced `.claude` parent outside the fixture.
   - Prevention: reject a symlinked/non-directory `.claude`, any existing target and path escape; hold no-follow descriptors for the fixture parent, fixture and `.claude`; create/link/check/remove only descriptor-relative; re-open and compare directory identities before exclusive atomic publication.
5. **TOCTOU publishes stale or partial bytes** — settings change between JSON validation and digest handoff, source changes before copy, or target appears before publication.
   - Prevention: parse, validate, digest and return one regular-file byte snapshot; later identity/byte reads may only reject drift. Re-read source bytes before the atomic link, reject a raced target, remove only our temporary/linked file, and test byte mutation, inode replacement, source change and target appearance with real files.
6. **Workspace-only evidence is mistaken for project registration** — startup/no-op artifacts bind a file the Claude SDK does not read for fixture `sdkCwd`.
   - Prevention: setup receipt labels workspace settings assembly-only; evidence must name the exact fixture destination and digest.
7. **Claude evidence is transferred to Pi** — the unsupported Pi bridge is treated as consuming Claude project hooks.
   - Prevention: keep Pi `unsupported-unverified` in setup and forbid Claude registration metadata on Pi host events.
8. **Cleanup destroys conflicted bytes** — a changed fixture target is deleted without diagnosis, or a claimed SHA-shaped value substitutes for an actual comparison.
   - Prevention: preserve the setup receipt digest and registered destination digest; independently hash the fixture file immediately before removal; require recorded registered/observed equality; stop and report mismatch; verify exact target absence before broader temp-root absence.

## Stop conditions

Stop on any inventory mismatch, malformed JSON, foreign/extra hook group, non-exact command vector, missing/non-executable/changed payload dependency, symlink, existing target, race, stale attestation, fixture path mismatch, workspace-only host evidence, Pi evidence transfer, or cleanup digest conflict.

## Rollback

This slice changes source only. Before any future approved setup, rollback is branch deletion. During an approved disposable setup, failure must leave no usable partial fixture target; cleanup remains restricted to the exact disposable workspace and temp root after conflict checks.
