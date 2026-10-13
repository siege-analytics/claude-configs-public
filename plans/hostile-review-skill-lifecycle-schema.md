# Hostile review: skill lifecycle schema and migration ratchet

## Scope

Independent adversarial review of `bin/skill-lifecycle.py`, schema/policy catalogs, fixtures, and hosted CI integration. Generated 198-row reports were excluded from review prompts but validated separately for freshness.

## Round 1

Found that regenerated exceptions could grow, non-project items inherited tier/owner, project tiers could conflict, the validator did not consume its published schema, and inventory paths/freshness were trusted.

Resolution: added explicit post-baseline approvals; project-only inheritance; project-tier conflict checks; schema-backed required/enumerated values; canonical root-contained paths; and same-command inventory freshness.

## Round 2

Found that bootstrap membership remained editable and completed items could later re-enter the bootstrap exception pool.

Resolution: pinned the bootstrap file by SHA-256 and introduced mandatory completion records plus metadata-regression rejection.

## Round 3

Found that deleting a completion record in the same change as a metadata regression reopened the bootstrap exception.

Resolution: compare completed paths with the protected PR base, previous push SHA, or merge-group base and reject removals.

## Round 4

Found two final fail-open paths: unavailable/shallow base history and expansion of an existing exception's missing/invalid field set.

Resolution: validation now fetches full history and fails if the previous ref is unreadable; gap sets may shrink but expansion requires an explicit approved-exception record.

## Final disposition

All identified S1/S2 findings were addressed. Fixtures cover new unapproved gaps, approved future gaps, project-only inheritance, project-tier conflicts, schema case sensitivity, path traversal, required completion recording, completed-metadata regression, completion-record deletion, and unapproved gap-set expansion.
