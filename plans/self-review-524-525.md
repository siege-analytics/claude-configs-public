---
ticket_refs:
  - siege-analytics/claude-configs-public#524
  - siege-analytics/claude-configs-public#525
---
## Self-Review: #524 + #525 — WARNING-to-BLOCK promotions

## Assumptions
Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: tickets #524, #525
Goal source verification: tickets describe WARNING-only checks that should be BLOCKs
Plan reference: #524 and #525 ticket bodies
Pre-author-inventory: investigate-gate.json (ticket siege-analytics/claude-configs-public#524)
Investigate-artifact: investigate-gate.json (ticket siege-analytics/claude-configs-public#524)
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/524#issuecomment-4838377695
Trivial-against-state: no — promotes two warnings to blocks + fixes regex

## Peer review

writing-code: WARNING-to-BLOCK promotions in self-review.sh

### Syntax check
- `bash -n hooks/git/self-review.sh` → exit 0

### Logic verification — Design-Note-Source (#524)
- **[no-review] exemption**: wraps entire Design-Note-Source block in `if ! echo "$COMMIT_MSG" | grep -qF '[no-review]'`. Promote commits with `[no-review]` skip the check entirely.
- **BLOCK behavior**: `exit 2` replaces `# WARNING only — do not exit 2`.
- **Error message**: updated to say "BLOCKED" and references #524.

### Logic verification — Tiger severity regex (#525)
- **Regex fix**: `'\*?\*?severity:\*?\*?\s*(HIGH|MEDIUM|LOW|CRITICAL)'` — adds optional `\*?\*?` markers to match markdown bold `**Severity:**`. Tested: matches both `Severity: HIGH` (plain) and `**Severity:** Medium` (bold).
- **BLOCK behavior**: `exit 2` replaces `# WARNING only — formatting varies`.
- **Error message**: updated to show `**Severity:**` format example.

### Cross-check: existing pre-mortems
- pre-mortem-518.md: `**Severity:** Medium` → matches fixed regex (TIGER_COUNT > 0)
- pre-mortem-519.md: `**Severity:** Medium` → matches fixed regex (TIGER_COUNT > 0)
- Both also have `### Tiger` headers → TIGER_HEADER_COUNT > 0 (double pass)

## Lead review

One file changed. Two WARNING-to-BLOCK promotions. The Design-Note-Source promotion is conditional on `[no-review]` absence — the right exemption for promote commits. The severity regex fix is a genuine bug fix (the regex never worked for the standard format).

## Findings
No findings.

## Quantified claims
- "1 file changed" — hooks/git/self-review.sh
- "2 promotions" — Design-Note-Source (v1.5 → v2) and Tiger severity (WARNING → BLOCK)

## Rework ledger
No rework cycles.
