# Resident delivery pre-mortem — #1003

The failure being repaired is observable in the final payload: the selector
names a composed resident but the registered hook emits only the generic
kernel. Adding a second selector or another policy evaluator would increase
the mismatch risk. Reuse the existing selector, with one checked render mode.

The main risks are project leakage, partial output before a late path failure,
stale or tampered resident content, guessed repository aliases, canonical
kernel replacement and applying Siege’s repository topology to other projects.
Validate the complete project result before printing it. Keep the fixed
resident path, canonical kernel comparison and non-authorizing receipt state.
Keep exact accepted policy independent of content. Scope every kernel
exact-main statement to scaffold installation, including the precedence text.

Tests use real generated packages and real hook invocations. Negative controls
cover foreign/absent/port-aliased identities, stale bytes/counts, symlinks,
escape paths, missing runtime inputs, ambiguous/over-budget/invalid results,
unavailable selectors and disabled/candidate-only modes. A no-op hook produces
no delivery evidence. No live host or shared workspace is touched.

Rollback is a normal revert of this bounded source change and regeneration of
its catalogs. Prior local/provider evidence stays recorded; any new resident
delivery claim is withdrawn with the adapter. Main/deployment rules remain
unchanged throughout.
