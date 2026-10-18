# Pre-mortem: #1042 Craft skill frontmatter

## Scope

Repair the canonical `shape-space-audit` skill and make the authority inventory reject missing Craft-required metadata for every canonical skill kind.

## Predicted failures and controls

1. **Workspace-only patch hides a release defect.** Change canonical source, rebuild both layouts, verify published consumer bytes after release, then reinstall exact main.
2. **One-file fixture misses the next invalid skill.** Enforce `name` and `description` centrally in `make_item` for general, router, shelf, reference-shelf, and project skill kinds.
3. **Rule files are rejected as skills.** Apply the requirement only to skill kinds; rule kinds retain their current format.
4. **Shelf references become ambient commands.** Preserve nested shelf paths and the parent-router loading contract; do not flatten reference books into workspace-root slugs.
5. **Project flattening escapes validation.** Include a missing-description project-skill fixture and verify flattened project skills with Craft's native validator.
6. **Generated evidence goes stale.** Regenerate inventory and build outputs, then run generated-source authority and build freshness.
7. **A local pass is mistaken for host integration.** Require native `skill_validate` plus a fresh Craft session that reads the exact installed `shape-space-audit/SKILL.md` after release.
8. **Unrelated local project skill bytes are overwritten.** Preserve the separately maintained `siege-utilities--hostile-review` divergence and report it rather than forcing release bytes over it.
