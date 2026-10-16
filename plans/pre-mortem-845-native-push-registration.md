# Pre-mortem: #845 native push registration and range semantics

## Scope

Make the accepted range-aware self-review hook the only native pre-push review adapter, register it explicitly in a selected consumer repository, and verify it through real pushes to a disposable local bare remote. This remains bypassable local feedback; #1002's protected provider is the server-side acceptance boundary.

## Failure modes and controls

1. **Generated wrapper still calls command-string gates.** Bind review validation to `hooks/git/pre-push-self-review.sh`; preserve stdin and exit status. Retain existing branch/test dispatch pending separate migration; this does not establish their native branch behavior. Remove the native range hook from tool-JSON settings.
2. **Missing runtime dependencies fail open.** The wrapper rejects absent/non-executable range hook, risk helper, or policy instead of skipping enforcement.
3. **Installer mutates the configs repo while claiming a consumer install.** Direct mode targets the configs repo only; workspace mode performs no native registration unless `--git-repo` names an exact consumer repository.
4. **Relative hooks path resolves against the wrong repository.** Consumer registration uses an absolute packaged `.githooks` path and verifies its real path.
5. **A green head hides an older bad commit.** The acceptance probe pushes a multi-commit range whose interior commit lacks required evidence and observes that the remote ref is absent/unchanged.
6. **Direct invocation passes but Git never invokes the hook.** Tests use ordinary `git push` into a local bare remote with `core.hooksPath` configured in the disposable consumer.
7. **A no-op or substituted hook is reported live.** Verifier checks exact registered path and real push behavior; mutation tests replace the adapter with `exit 0` and require failure.
8. **Repair remains impossible after denial.** The same disposable repository resets to the remote base, creates a valid reviewed range, pushes successfully, and records the advanced remote ref.
9. **Local success is misreported as protected authorization.** Output and docs state native hooks are bypassable feedback and never satisfy `protected-range-validation`.
10. **Other remotes hide invalid history.** Use the exact destination advertisement, never local tracking/all-remotes. Unknown destination objects and malformed native updates fail closed.
11. **Project customization disappears.** Merge settings idempotently, quote command paths, and reject conflicting settings/native hook registrations before writes.
12. **Risk authority changes escape Tier C.** Installer, verifier, generator, canonical wrapper, native probe tests, and risk-policy classification all require Tier C evidence and mutation coverage.

## Rollback

Revert the #845 commit to restore the previous generated package and installer/verifier behavior. No existing consumer is modified by implementation or CI. The protected #1002 workflow and retained topology guard are unchanged.
