# Focused self-review: expired writing migration notes

## Assumptions

Review tier: B (standard skill/rule change)
Domain(s): software engineering, writing policy
Working as: software engineer
Goal source: approved Skill Library Simplification Plan, Phase 6 first thematic batch
Goal source verification: the approved plan names global writing rules first and requires small reversible batches with before/after tokens, consumers, tests, and rollback.
Affected consumers: unchanged; all five canonical source paths, rule identifiers, cross-references, overrides, and generated destinations remain.
Scope: remove only five `## Migration note` blocks that say they are retained for v2.0.x and removed in v2.1.0. Current release is v3.5.63. `CHANGELOG.md` retains the permanent migration table and explicitly states the addendums expire.

## Test plan

- `hooks/_test/writing_migration_cleanup.test.sh` rejects any returning migration-note heading in `_writing-*-rules.md`.
- run token/reference build check, inventory/lifecycle/authority freshness, kernel/progressive/review metrics, package validation, and all hook suites;
- verify generated rules-bundle characters decrease while kernel and deterministic load sets remain unchanged;
- rollback by reverting this commit; no alias, source path, lifecycle status, or consumer mapping changes.

Measured authored change: 171,313 -> 168,557 characters, down 2,756 characters / approximately 689 estimated tokens.
