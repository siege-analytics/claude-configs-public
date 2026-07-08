---
ticket_refs:
  - siege-analytics/claude-configs-public#457
---

## Self-Review: #457 — Tier B IDE consumer package

## Assumptions

Working as: software engineer
Domain(s): software engineering, build/release infrastructure
Geospatial cross-cut: no
Goal source: ticket #457
Goal source verification: operator request to add first-class IDE consumer support with CI
Plan reference: plans/pre-mortem-457.md
Pre-author-inventory: NONE
Trivial-against-state: no — new consumer runtime packaging
Investigate-artifact: investigate-gate.json (ticket #457)
Pre-mortem-artifact: plans/pre-mortem-457.md
Project-contribution: Ships a validated Tier B install path so hookless IDEs receive the same skill corpus, resolver, and rules bundle as hook-capable runtimes — extending mechanical discipline to environments where PreToolUse gates cannot run but advisory skills and User Rules can still compel process.

## Peer review

Shelf references: writing-releases:5 (verify published artifact loads in consumption environment — validate-cursor.py + install dry-run), writing-code:4 (symbol exists — build_cursor_package references dist/flat paths that build.py creates), packaging-rules:1 (consumer package self-contained layout mirrors claude-code/craft-agent).

### Build validation

- `python3 bin/build.py` → exit 0; cursor package reports 72 skill directories
- `python3 bin/validate-cursor.py dist/cursor/` → PASS

### Spot checks

- `dist/cursor/skills/think/SKILL.md` — `allowed-tools` stripped from frontmatter
- No loose `_*-rules.md` at `dist/cursor/skills/` root
- `dist/cursor/RESOLVER.md` present (fallback from repo root when flat template missing)
- `dist/cursor/bin/install-cursor.sh` executable

### Syntax check

- `python3 -c "import ast; ast.parse(open('bin/build.py').read())"` → exit 0
- `python3 -c "import ast; ast.parse(open('bin/validate-cursor.py').read())"` → exit 0
- `bash -n bin/install-cursor.sh` → exit 0

## Lead review

Package mirrors claude-code/craft-agent publish pattern: validate in CI, release branch,
consumption tag, tarball on GitHub Release. Install script explicitly avoids
`~/.cursor/skills-cursor/`. Tier B limitation documented in cursor/CURSOR.md.

Residual risk: install merges skill dirs without `--delete` — documented in CURSOR.md.

## Quantified claims

- Skill directories in package: 72 (build-info.json skill_count)
- SKILL.md files under dist/cursor/skills/: 155 (validate-cursor.py output)
- New scripts: 2 (install-cursor.sh, validate-cursor.py)
- New doc files: 3 (CURSOR.md, user-rule.md, project-rule.mdc)
- CI workflow steps added: 2 (validate cursor, publish release/cursor)
