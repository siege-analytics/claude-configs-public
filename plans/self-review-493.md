---
ticket_refs:
  - siege-analytics/claude-configs-public#493
---
## Self-Review: #493 — brittle think-gate claims

## Assumptions
Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #493
Goal source verification: ticket body describes brittle claim patterns from #1125 dogfood
Plan reference: #493 ticket body
Pre-author-inventory: #1125 session where _require_reportlab claim failed against inline guard
Investigate-artifact: investigate-gate.json (ticket siege-analytics/claude-configs-public#493)
Pre-mortem-artifact: plans/pre-mortem-493.md (workspace)

## Peer review

writing-code: documentation addition to skills/think/SKILL.md — new subsection "Writing robust claims" with brittle vs robust examples.

### Syntax check
- File is markdown, no executable syntax to validate.

### Logic verification
- Brittle example matches the actual failure from #1125 (_require_reportlab vs REPORTLAB_AVAILABLE)
- Robust example uses REPORTLAB_AVAILABLE which is the invariant — present regardless of guard mechanism
- Guidance is "grep for the invariant" — general principle, not prescriptive per-claim rules
- Inserted after the existing Schema A section (line 304) — natural reading flow

## Lead review

Documentation-only change to an existing section. Adds concrete good/bad examples drawn from a real failure. The guidance follows the existing pattern of the skill (examples embedded in prose, not a separate reference). No executable behavior change.

Blast radius: agents reading the think skill will see the new guidance on their next invocation.

## Findings

No findings.

## Quantified claims
- "1 section added" — diff shows ~35 lines added after line 304

## Rework ledger

No rework cycles.

## Evidence-predates-work
Artifact: plans/self-review-493.md
First-added commit: (same commit)
Work commit: (pending)
