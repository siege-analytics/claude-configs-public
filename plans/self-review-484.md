---
ticket_refs:
  - siege-analytics/claude-configs-public#484: comment posted
---
## Self-Review: #484 — Artifact gates must verify ticket association

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #484
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/484#issuecomment-4815190462
Pre-author-inventory: NONE
Investigate-artifact: TRIVIAL (bug found during integration test, fix is mechanical)
Pre-mortem-artifact: ticket comment (inline with design note)

## Trivial-investigation declaration
The bug was discovered during the #482 integration test: pipeline-state-guard
accepted `pre-mortem-476.md` for ticket #482. The root cause is obvious
(glob match without ticket check) and the fix is mechanical (add ticket
field comparison). No investigation needed beyond reading the two affected
files, which was done inline.

## Peer review

### Shell correctness
- `bash -n hooks/bash/universal-mutation-gate.sh` → exit 0
- `bash -n hooks/resolver/pipeline-state-guard.sh` → exit 0
- Syntax check: N/A (no standalone .py changes)

### Test results
- Test 1: correct-ticket artifacts → exit 0 (pass)
- Test 2: wrong-ticket artifacts → exit 2 BLOCKED
- Test 3: no ticket field → exit 0 (backwards compat)

### Build validation
- `python3 bin/build.py` → exit 0
- `python3 bin/validate-hooks.py` → "All hooks valid."

### Changes
1. **universal-mutation-gate.sh**: replaced shell-level artifact existence
   checks with Python block that reads think-gate.json ticket field and
   verifies investigate-gate.json ticket match + pre-mortem file content match.
   Added CRAFT_AGENT_WORKSPACE/plans/ to plan_dirs search.

2. **pipeline-state-guard.sh**: added `current_ticket` extraction from
   think-gate.json. Replaced `find_artifact` with ticket-aware version that
   checks file content for ticket reference. Added investigate-gate.json
   ticket field check. Error messages now name the specific ticket.

## Lead review

The Junior's fix is correct: both gates now enforce ticket association.
The `file_references_ticket` function checks both the full reference
(`siege-analytics/repo#N`) and the short slug (`#N`) to handle both
frontmatter and body-text references.

The backwards-compatibility path (no ticket field → accept any artifact)
is important: older think-gate.json files that predate the ticket field
should not break. This is the right default.

**The real finding**: this bug class — "gate checks existence, not
association" — is exactly what the Vergil quote integration test was
designed to smoke out. The test worked. The pipeline caught its own
weakness during the first real exercise.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| 1 | P1 | Artifact gates accepted wrong-ticket artifacts | fixed |
| 2 | P3 | investigate-gate-guard.sh warns but doesn't block on empty verifiedShapes | noted — separate ticket needed |

## Quantified claims
- "3 test cases" — ran inline above (correct-ticket, wrong-ticket, no-ticket)
