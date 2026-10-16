# Composed resident delivery

The registered `hooks/resolver/inject-resolver.sh` prompt hook keeps the
canonical safety kernel and invokes `bin/resolve-load-set.py --render-hook`
once. A matching composed package additionally supplies its
`skills/RESIDENT.md` and ordered, readable selected skill paths. The ordinary
selector JSON interface remains available to existing callers.

The renderer validates the complete load set before emitting project content.
It requires the exact normalized repository identity, matching project and
composition receipt, the fixed resident path, exact rendered bytes and counts,
and `configured` / `authorization_effect: none` receipt states. Selected files,
receipt, resident and catalog inputs must be regular package files; symlinks,
path escapes, missing inputs and a changed resident reject project rendering.
The resident has an 80,000-byte runtime ceiling, in addition to the composer’s
configured budget. The two pilot projects use 2,500 characters / 625 estimated
tokens. Their real hook fixtures also verify that the canonical kernel remains
present exactly once.

An unknown task may retain resident context when the project independently
matches exactly. It selects no task skills. Ambiguous, invalid and over-budget
selection emits no project content. `off` and `kernel-only` retain the kernel
alone; `canary` lists candidates without emitting resident text or load
instructions. No mode injects the full rules bundle. A missing or noncanonical
kernel still produces the existing sole structured blocking response.

K5 distinguishes Siege’s own `develop` → `main` and exact-current-main
installation rules from other consumers’ independently approved topology.
No project content, receipt, selector result or environment switch grants
permission to perform an operation. The scaffold’s deployment source guard is
unchanged.

The installed package is an input to this mechanism. Consistency between
jointly mutable receipt and content does **not** authenticate that package.
Use the accepted source/package/generation verification boundary separately.
Local hook tests establish emitted bytes and paths, not Craft registration,
model receipt, tool blocking or recovery. Those remain the separate #1003 live
canary acceptance criteria.

Run `python3 bin/_test/resident_delivery_test.py` for the two-project,
two-layout local adapter corpus. Rolling back this source slice restores the
prior kernel-only resident behavior; it must also remove any claim that the
registered hook delivers composed resident content.
