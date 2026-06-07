# Self-review: scaffold-project.py (#373)

## Lead

- **As tech lead:** Single new file (`bin/scaffold-project.py`), no existing
  code modified. Blast radius is zero -- the script only creates new files
  and directories; it never edits existing ones. Fully reversible (delete
  the script). Three subcommands (`init`, `satellite`, `add-skill`) cover
  the three consumption patterns identified in the electinfo/pour-now
  leakage postmortem.

- **As domain expert:** Templates match the canonical in-tree pattern
  (siege-utilities PROJECT.md frontmatter, _rules.md with overrides table)
  and the flat-sync satellite pattern (UPSTREAM.md sync tracker, two-layer
  PROJECT.md). Generated PROJECT.md passes `build.py --check` validation
  (tested: ProjectManifest required fields present, repo uniqueness holds).

## Checklist

- [x] `init` creates PROJECT.md with all REQUIRED_FIELDS (name, description,
      repo, owners) -- validated against `ProjectManifest.REQUIRED_FIELDS`
- [x] `init` creates _rules.md with overrides table matching siege-utilities
      pattern
- [x] `init` creates skills/ directory with .gitkeep
- [x] `satellite` generates UPSTREAM.md with sync state table, sync history,
      step-by-step sync instructions, assessment policy
- [x] `satellite` generates PROJECT.md with two-layer integration policy
- [x] `satellite` generates README.md with layout diagram and sync policy
- [x] `add-skill` creates SKILL.md with correct frontmatter (name includes
      project slug for disambiguation)
- [x] Error paths: existing directory detected and rejected (exit 1)
- [x] Error paths: nonexistent project detected with helpful message
- [x] No unused imports (removed `os`)
- [x] ASCII-only verified (perl check, no non-ASCII characters)
- [x] Python parse verified (`ast.parse`)
- [x] `build.py --check` passes with scaffolded test project
- [x] Test artifacts cleaned up after validation

## Gaps

- The `satellite` subcommand hardcodes `siege-analytics/claude-configs-public`
  as the upstream repo. If a different upstream is needed in the future, add
  a `--upstream` flag. Not needed today -- there is only one upstream.
- The `add-skill` subcommand does not validate that the skill slug is valid
  (e.g., no spaces, lowercase). This matches existing behavior -- `build.py`
  handles validation at build time, not at creation time.
