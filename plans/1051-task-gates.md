---
ticket_refs:
  - siege-analytics/claude-configs-public#1051
propagation: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252933479
---
# Task-keyed gates: design and investigation record

Design: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252889539
Fact Sheet: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252915590
Pre-mortem: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252933479

## Pre-author inventory
Verified base main 056b5337b08bb960fb7796b6bb00c971e22664f1; target develop dbe21c1968cb1c04ba6eeb780169ae37929cc7b1 has identical principal sources.

- Gate resolver: session / repo filename, project / local / workspace fallbacks; no task identity. Callers: think, investigate, review, skill-enforcement, pipeline-state, universal-mutation and git self-review guards. CRITICAL fanout.
- Bash payload: tool_input.command + cwd + runtime session identity. Canonical paths must account for cd, git -C, redirects and tool target paths; unknown shell constructs fail closed.
- Think signal: task/ticket, session/sessionId, repo_root, status. New fields: scope_paths, task_id. Canonical task directories, exact identity; legacy session file remains a read source only.
- Artifact signals: investigate, junior-senior, artifacts-posted, review; pipeline-state writes the middle two plus unreachable stamps. Writer must be session/task keyed and atomic.
- Hub payload: target sessionId; state cap/open_threads/last_activity. New structured task identity and parent/worker/traffic-cop relationships; never infer exemption from prose.
- Additional test evidence: git test-guard root singleton; commit/testing-frameworks guidance. Migrate alongside named gates.
- Knowledge loci: hooks/README.md; think/investigate/pre-mortem/self-review/cross-review/commit/testing-frameworks skill instructions.
- Test boundary: real hook subprocesses and resolver filesystem fixtures. Existing root-authorization fixtures require deliberate migration; no mocks of changed functions.

## Pre-mortem
Severity: classifier hidden execution and foreign-task fallback are launch-blocking until negative tests pass. Mitigations: bounded positive grammar, restricted non-evaluated Python AST; exact identities; canonical path-component containment; all mutation targets owned by one task; ties block with diagnostics; root legacy diagnostic-only; artifacts only beside selected task gate; atomic writers and serialized hub bookkeeping. No release or activation.

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#1051
Goal source verification: PASS: ticket siege-analytics/claude-configs-public#1051 is fit for execution
Plan reference: approved design above
Pre-author-inventory: plans/1051-task-gates.md#pre-author-inventory
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252915590
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252933479
Project-contribution: independent task enforcement without fleet-wide artifact coupling.

## Test plan
Implement every design case and acceptance negative, then run all hook suites, hook validator, source-authority checks, generated freshness/build, review-risk and independent hostile exact-SHA review. No live workspace canary; fixture-only canary and additive rollback.

## Peer review
Pending implementation; this record is committed before work to preserve provenance.

## Lead review
Pending implementation and independent hostile review.

## Quantified claims
No verification counts claimed before execution.

## Rework ledger
Ticket evaluator initially blocked missing Design line; coordinator corrected body and rerun passed. No exemption.
