# Self-review: #1042 Craft skill frontmatter

## Defect evidence

Craft's native validator rejected `skills/shape-space-audit/SKILL.md` from the exact v3.5.65 workspace with `name: Required` and `description: Required`. The same missing frontmatter exists in canonical source, `dist/flat`, and immutable `v3.5.65-flat@86f76958bbbf38706b9552e77f81aa364aebb2ac`; this is not local drift.

## Repair

- Add concise `name` and `description` metadata to the canonical skill.
- Reject missing metadata centrally for every canonical skill kind discovered by `skill-inventory.py`.
- Add negative fixtures for a direct skill missing all metadata and a flattened project skill missing `description`.
- Preserve rule-file and nested shelf semantics.

## Review questions

- Does the check cover every source path that can become a consumer skill?
- Can a rule file or archived/ignored source be rejected accidentally?
- Do flat and nested builds retain exact metadata?
- Does the installed Craft workspace resolve the direct skill in a fresh session?
- Are unrelated local project skill bytes preserved?

## Evidence required before acceptance

Focused inventory tests, regenerated inventory freshness, full build/check, generated-source authority, skill lifecycle/quality tests, all hook suites, clean staged scan, native validator pass, exact flat-release comparison, and fresh-session invocation after exact release installation.

## Author evidence

- `skill_inventory_test.py` passes new direct and project missing-metadata negatives plus existing collision/shelf fixtures.
- Full build and `--check` pass; flat and nested `shape-space-audit/SKILL.md` copies both contain exact required metadata.
- Regenerated inventory and generated-source authority are current: 198 sources, 804 artifact snapshots, and 2,916 generated mappings.
- Skill lifecycle, review-risk, review-risk metrics, kernel budget, and generated-source authority fixtures pass.
- All 36 hook suites and source/Craft/Claude hook validation pass.
- Current v3.5.65 workspace integration probes loaded direct, flattened-project, shelf-router, and flat-layout skills in fresh Craft sessions; this repair still requires post-release native validation and fresh invocation of `shape-space-audit` itself.

## Hostile-review correction

The first independent review found that quoted interior whitespace such as `name: "   "` remained truthy after quote stripping. The replacement predicate strips the parsed value before testing emptiness, and the exact hostile input is now a negative fixture. The prior exact-head ACCEPT is historical and does not transfer.

## Promotion-review YAML correction

Promotion review found that comment-only YAML (`name: # pending`) was accepted because the dependency-free parser treated the comment as text. The additive parser now strips comments only outside quoted scalars, maps unquoted `null`/`~` to null, and preserves quoted hashes or quoted `null` as strings. Exact name/description comment-only and null fixtures were added. All prior feature and promotion verdicts are historical and do not transfer.

## Author verdict

Accept for fresh independent hostile review after a clean staged scan. Do not claim the local invalid skill repaired until an exact corrected release is installed.
