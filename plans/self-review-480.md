## Self-Review: #480 — NotebookEdit hooks + validate-hooks.py

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #480
Plan reference: #480 ticket description
Pre-author-inventory: NONE
Investigate-artifact: plans/self-review-477.md (hostile review findings)
Pre-mortem-artifact: plans/pre-mortem-476.md

## Peer review

### Shell correctness
- `bash -n` on all 31 hook scripts → exit 0 (via validate-hooks.py)
- `python3 bin/validate-hooks.py` → "All hooks valid."
- Syntax check for .py: `python3 -c "import ast; ast.parse(open('bin/validate-hooks.py').read())"` → exit 0

### Changes

1. **NotebookEdit matcher added** to settings-snippet.json: same write-guard,
   branch-guard, ticket-propagation-guard hooks as Write/Edit. Previously
   NotebookEdit was ungated — could bypass branch and ticket guards.

2. **bin/validate-hooks.py created**: validates hook paths exist, are
   executable, pass `bash -n`, checks lib helpers, reports unreferenced
   hooks. Enforces MIN_HOOK_COUNT=20 to catch silent truncation.
   Works on both repo (default) and consumer packages (`dist/claude-code/`,
   `dist/craft-agent/`).

3. **Fixed executable bits** on self-review.sh, decomposition-guard.sh,
   workspace-backup-guard.sh. The first was a blocking error (referenced
   in settings but not executable); the other two are currently unreferenced
   but should be executable regardless.

## Lead review

NotebookEdit was a genuine gap — it's a file mutation tool that had zero
PreToolUse hooks. The fix mirrors Write/Edit hooks exactly, which is the
correct approach (same guards apply to all file mutation tools).

The validate-hooks.py script serves two purposes: CI validation (catches
broken references before they reach users) and consumer package validation
(ensures dist packages are complete). The MIN_HOOK_COUNT floor is a
reasonable defense against silent truncation during build.

**Blast radius**: NotebookEdit operations will now be subject to write-guard,
branch-guard, and ticket-propagation-guard. This is intentional — notebooks
should not bypass the enforcement pipeline.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| 1 | P2 | 6 unreferenced hooks on disk — may be deprecated or optional | noted — not blocking; these are warnings, not errors |

## Quantified claims
- "31 hook paths" — `python3 bin/validate-hooks.py` → "Validated 31 hook paths"
- "6 unreferenced hooks" — same output, 6 WARN lines
