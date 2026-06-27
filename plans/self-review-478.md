## Self-Review: #478 — Consumer packages (claude-code, craft-agent)

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #478
Plan reference: #478 ticket description
Pre-author-inventory: NONE
Investigate-artifact: plans/self-review-477.md
Pre-mortem-artifact: plans/pre-mortem-476.md

## Peer review

### Syntax checks
- `python3 -c "import ast; ast.parse(open('bin/build.py').read())"` → exit 0
- `python3 bin/build.py` → exit 0 (full build completes)
- `python3 bin/validate-hooks.py dist/claude-code/` → "All hooks valid."
- `python3 bin/validate-hooks.py dist/craft-agent/` → "All hooks valid."

### Changes

1. **`build_consumer_packages()` in build.py**: Assembles `dist/claude-code/`
   and `dist/craft-agent/` with hooks, lib helpers, settings-snippet.json,
   skills (flat layout), validate-hooks.py, package manifest, and root files.

2. **CA_ONLY_MATCHERS filtering**: `mcp__session__send_agent_message` (and
   other CA-only MCP matchers) stripped from claude-code settings. Verified:
   claude-code has 30 hooks vs craft-agent's 31.

3. **Craft-agent skill stripping**: Craft-incompatible frontmatter keys
   stripped from skills in the craft-agent package (same as deploy_to_workspace).

4. **CI workflow updated**: Added hook validation steps (full build +
   validate-hooks.py on both packages + repo). Added consumer package
   release branches (release/claude-code, release/craft-agent). Added
   consumer package tags and tar.gz archives in GitHub Releases.

5. **Wired into main()**: `build_consumer_packages()` called after
   `build_ca_enforcement()`.

## Lead review

The consumer packages are assembled from already-built dist/flat/ content
and repo hooks. The build order is correct: flat layout first, then CA
enforcement (which writes to dist/craft-agent/), then consumer packages
(which reads from dist/flat/ and copies hooks from repo root).

The CA_ONLY_MATCHERS list is conservative — only matchers that reference
`mcp__session__*` tools are filtered, since these tools don't exist in
Claude Code. If new CA-only matchers are added to settings-snippet.json,
they must be added to CA_ONLY_MATCHERS or they'll leak into the claude-code
package.

The CI workflow adds 4 new steps to the validate job (full build + 3
validate-hooks runs) and 2 new publish steps (consumer package branches).
The additional ~30s of CI time is justified by catching broken hooks before
they reach consumers.

**Blast radius**: New dist/ output directories; no changes to existing
dist/nested/ or dist/flat/ content. CI changes are additive.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| 1 | P3 | CA_ONLY_MATCHERS must be manually updated when new CA-only matchers are added | noted — document in CONTRIBUTING.md |
| 2 | P3 | _test/ directory copied to consumer packages — adds weight but useful for post-install validation | noted |

## Quantified claims
- "30 hooks vs 31" — validate-hooks.py output: claude-code validated 30, craft-agent validated 31
- "46 hook scripts each" — build.py output: "claude-code: 46 hook scripts"
