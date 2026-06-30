---
ticket_refs:
  - siege-analytics/claude-configs-public#602: open
type: hostile-review
reviewer: claude-sonnet-4-6 (via call_llm, no author context)
reviewed_at: 2026-06-30
---

# Hostile Review: #602 — Block-Event Logging and Classification Guard

## Verdict

The change adds process overhead without delivering the invariant it claims. The classification is agent self-attestation, not mechanical verification. However, as a first slice, it creates an audit trail where none existed.

## S1 Findings (4)

### S1-A: Agent self-classifies with no verification
Agent can write `"classification": "normal"` for every block with no review. Still agent self-attestation in a different file.
**Author response:** Known limitation, documented in guard header. Value is in forcing the record to exist for operator audit.

### S1-B: source || true makes logging silently optional
If log-block.sh is missing, logging is skipped with no signal.
**Author response:** Fixed — added stderr warning on source failure. The `|| true` is retained because hooks must not crash on missing deps.

### S1-C: Python exception handling silences write failures
`except Exception: pass` means failed writes produce no record.
**Author response:** Fixed — added stderr warning in except block.

### S1-D: 2-hour cutoff drops unclassified blocks silently
Blocks older than the cutoff window disappear from classification pressure.
**Author response:** Increased to 4 hours and documented the design decision.

## S2 Findings (6)

### S2-A: Only last 3 blocks surfaced
Cap prevents overwhelming injection. Earlier blocks exist in log for audit. Accepted.

### S2-B: No schema validation on classification file
Malformed entries are silently ignored. Accepted for v1.

### S2-C: MATCHED_BLOCKS extraction in destructive-guard is fragile
Array is guaranteed non-empty at that point (exit 0 on line 140 if empty). Accepted.

### S2-D: Workspace path fallback brittle under symlinks
CRAFT_AGENT_WORKSPACE is the safe path; fallback is best-effort. Accepted.

### S2-E: No deduplication on block log
Retries create multiple entries. Accepted — each retry is a distinct block event.

### S2-F: Unverified exit 2 coverage
All 3 exit 2 points in universal-mutation-gate verified. Destructive-guard has 1 exit 2 point. Coverage confirmed.

## S3 Findings (4)

### S3-A: Log grows without bound
No rotation. Accepted for v1 — logs are small (one JSONL line per block).

### S3-B: Display truncation inconsistency
200 chars in log, 80 in display. Accepted — display cap is for injection brevity.

### S3-C: Timestamp collision risk
Sub-second blocks from same gate share IDs. Extremely unlikely in practice.

### S3-D: "Agent-independent" framing misleading
Changed to "automatic" in documentation. The log is agent-adjacent, not agent-independent.
