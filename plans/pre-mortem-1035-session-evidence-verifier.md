# Pre-mortem: session evidence verifier scope (#1035)

## Boundary

`bin/verify-enforcement.sh` must verify active Craft instruction surfaces without rewriting or treating immutable session evidence as policy. The only new exclusion is the exact path shape `sessions/<one segment>/data/**`.

## Failure modes

1. **Over-broad glob hides policy.** Shell `*` can span `/`; do not use a `sessions/*/data` path glob. Parse relative path segments and require `sessions`, one non-empty session segment, then `data`.
2. **Session-root bypass.** `sessions/<id>/CLAUDE.md` and `AGENTS.md` remain active and must fail unless canonical.
3. **Lookalike bypass.** `database`, `Data`, and `sessions/<id>/archive/data` remain scanned.
4. **Symlink concealment mismatch.** Apply the same exact evidence predicate to instruction files and descendant directory symlink checks.
5. **Evidence destruction.** Never delete or rewrite stored review/audit files to make verification pass.

## Proof plan

Extend `hooks/_test/verify_enforcement.test.sh` with a passing evidence fixture containing noncanonical instruction names and a directory symlink, plus failing session-root and lookalike/deeper-path fixtures. Run the complete verifier suite, build/freshness checks, and the real workspace verifier after separately backing up and canonicalizing the stale root `AGENTS.md`.

## Out of scope

No gate decision, runtime policy, registration command, provider setting, or authorization semantics change. The root `AGENTS.md` conflict is genuine local configuration and is not suppressed by this patch.
