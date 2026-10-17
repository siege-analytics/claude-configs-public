# Pre-mortem: native Git hooks in Claude settings (#1038)

## Boundary

Managed `hooks/git/pre-push-*` scripts consume the native push-update protocol and must never remain in Claude event arrays. Other `hooks/git` guards may have canonical registrations in both surfaces. `bin/install-hooks.sh` must retire only the protocol readers while preserving operator hooks, canonical dual-use guards, and native `.githooks` registration.

## Failure modes

1. **Over-broad deletion:** basename-only matching deletes an operator helper. Require the exact `hooks/git/<managed-pre-push-name>` suffix or resolution into the current managed native directory.
2. **Old-root persistence:** matching only the current absolute package root misses commands left by a previous install. Exact path suffix handles old roots.
3. **Alias bypass:** a symlink outside the package points to a current managed native script. Resolve existing aliases before classification.
4. **Malformed-command bypass:** shlex errors become preserved opaque hooks. Fail before mutation.
5. **Native registration damage:** settings cleanup must not remove `.githooks/pre-push`, dependencies, or `core.hooksPath`.
6. **Operator loss:** settings keys and hook commands outside managed `hooks/git` remain unchanged; repeated installation is byte-stable.

## Proof

Extend the real native installer suite with old-root, relative, symlink-alias, operator-preservation, rerun-idempotence, and malformed-command/no-mutation cases. Run native push decisions, settings validation, build/freshness, all hook suites, and a real workspace reinstall. A bare Bash probe must not invoke the Git protocol reader.
