---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
---

# Self-review: #873 P3 -- resolve_project() primitive

## What changed
- `hooks/lib/resolve-think-gate.py`: add `resolve_project(repo_root, workspace)`
  (maps a repo to its project slug via git-origin match against
  projects/<slug>/PROJECT.md `repo:`, else 'umbrella'), plus `_origin_to_slug`
  and `_project_repo_field` helpers and a `--project` CLI mode.
- `hooks/_test/resolve_project.test.sh` (new): 5 scenarios.

## Why
D2: the skills/rules layer scopes by project (projects/<slug>/PROJECT.md,
build-validated unique repo:), but the gate layer had no project notion. This
primitive gives gates the same project identity, using the same match key the
build uses. It is the dependency for project-scoped gate files and for the KB
check (P5) to know which project it is in.

## Assumptions
- Match key is git origin org/repo, matching bin/build.py's PROJECT.md repo
  uniqueness. Verified: _project_repo_field reads the real siege-utilities
  PROJECT.md and _origin_to_slug normalizes both ssh and https to the same slug.
- claude-configs-public itself is the umbrella: resolve_project on its own repo
  returns 'umbrella' (no PROJECT.md claims its origin). Verified.

## Peer review (mechanics, correctness, craft floor)
- Syntax: `python3 -c "import ast; ast.parse(...)"` ok.
- resolve_project never raises: missing origin, missing projects dir, and
  unparseable frontmatter all return 'umbrella' / '' -- tested.
- The frontmatter reader is a line scan (no yaml dep in a hook-path lib),
  bounded to the first 4096 bytes and the --- fences.

## Lead review (adversarial: did this actually solve it?)
- Does it agree with the build's project matching? Yes -- same org/repo key;
  ssh and https forms both resolve to the declared repo: field (tested).
- Does it change any gate behavior yet? No -- this PR adds the primitive and CLI
  only; wiring project-slug into gate-file resolution is a P3 follow-up. No
  find_gate_for_repo path changed.
- Ambiguity handling? First matching PROJECT.md wins; build enforces repo
  uniqueness so there is no ambiguity in a valid tree; no match -> umbrella.

## Quantified claims
- "5/0" -- `bash hooks/_test/resolve_project.test.sh` -> `Results: 5 passed, 0 failed`

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| (none) | - | - | - | - |

## Trivial-investigation declaration
Not trivial -- investigation and pre-mortem for #873 exist.
