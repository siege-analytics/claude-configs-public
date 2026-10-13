# Pre-mortem — #980 shelf ownership and path integrity (Tier C)

Base: `develop` 022fb81bfcbdf829fccdfefe4c18dfcca899ceb2. Integration only; no main/release/publish/deploy/install.

## Failure shapes and containment

1. **False ownership from names/routers:** isolate the 83 category/book source paths from the meta-router; verify an active non-shelf source and verbatim scoped consultation evidence or record a reasoned quarantine. Refuse duplicates, missing/deleted sources and inactive owners. Keep resolver unchanged. Negative fixtures include router/self ownership and bare path evidence.
2. **False local reads:** parse actionable Markdown links and backticked `.md` paths in shelf SKILL/reference surfaces. Resolve book-relative or explicit repository-root paths, exempt explicit upstream URLs and qualified unavailable historical citations; test missing promises, orphan nonempty references, stale empty-placeholder exceptions, and shorthand.
3. **Destructive deduplication:** retain all four one-byte placeholder files with reasons rather than delete them; link eleven substantive previously unmentioned references from their respective book entries. Do not canonicalize without link migration.
4. **Runtime-context claim inflation:** separately measure tracked shelf bytes and real hook injection. Base shelf tracked bytes 6,064,932; added metadata is not automatically loaded. Compare same five load scenarios and three hook injections against base rather than claim token savings.
5. **Release boundary or CI regression:** change only the validation job targeting `develop`, never publish job or resolver. Run full 12 existing + 2 new Python suite files, 36 hook suite files, 2 workflow suites, all tracked-catalog freshness, and `git diff --check` before push.

Rollback: revert this feature commit from `develop` if review discovers false path handling or source drift; no release consumer or installation changes are in scope.
