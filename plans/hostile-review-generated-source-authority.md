# Hostile review: generated-source authority

## Scope

Independent adversarial review of the authority generator, isolated build support, fixtures, and CI integration. The repetitive generated catalog was excluded from prompts but validated for deterministic freshness.

## Round 1

Found that existing or partial `dist` bytes could be certified, source/output member symlinks could escape boundaries, inventory discovery was trusted without a freshness proof, and destination prefixes were too permissive.

Resolution: every write/check now validates Phase 0 inventory freshness, runs a new isolated full build, hashes only that fresh tree, rejects symlink chains/members, and requires exact form-specific destination shapes.

## Round 2

Found that unowned directory symlinks were skipped by file filtering and that `..` after a valid prefix could cross from one layout into another.

Resolution: reject symlinks before type filtering; reject traversal/wildcards; require resolved paths beneath the declared form's `skills` root. Added negative fixtures.

## Round 3

Found that reserved generated skills-root support files were excluded from hashes.

Resolution: canonical `skills/RULES.md` and `skills/_coverage.md` now have independent nested, flat, Claude Code, and Craft Agent hashes. Every generated skills-root file must have exactly one owner; unexpected support files fail.

## Final disposition

All identified S1/S2 findings were addressed. Current measured coverage is 198 inventory sources plus 2 support sources, 724 source-owned files, 800 artifact snapshots, and 2,896 generated file mappings, with zero collisions and zero unowned generated files.
