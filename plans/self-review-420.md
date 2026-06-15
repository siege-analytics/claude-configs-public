# Self-Review: #420 — Conditional reviewer activation

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#420
Goal source verification: PASS: ticket siege-analytics/claude-configs-public#420 is fit for execution
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/420#issuecomment-4712149786
Pre-author-inventory: NONE
Trivial-against-state: Additive prose section in self-review SKILL.md. No existing sections modified, no code changes, no data shapes or config affected.
Investigate-artifact: TRIVIAL

## Trivial-investigation declaration

Category: config-only
Cannot produce error: The change adds a new `## Conditional review routing` section between "Peer review uses the shelves" and "## Lead review." It is 118 lines of additive prose — no existing text is modified, no code files are changed, no hook logic is altered.
Evidence: `git diff --stat` shows `skills/self-review/SKILL.md | 118 +++` with zero deletions. The insertion point is between two existing sections with a blank line boundary.
Falsification: An existing self-review workflow breaks because the new section interferes with the hook's structural completeness checks (which parse section headers).

Pre-mortem-artifact: TRIVIAL

## Trivial-investigation declaration

Category: config-only
Cannot produce error: The new section uses `##` and `###` headers. The pre-push hook checks for `## Assumptions`, `## Peer review`, `## Lead review`, `## Quantified claims`, and `## Findings`. The new section header `## Conditional review routing` does not collide with any checked header.
Evidence: `grep -c '## Conditional review routing' hooks/git/self-review.sh` returns 0 — the hook does not reference this header.
Falsification: The hook's structural completeness check fails because it interprets `## Conditional review routing` as a required section or counts it as extra content.

## Peer review (the Junior's checklist)

### writing-prose
- No AI-typographic Unicode in the diff.
- Checklist items are concrete and specific (3-5 items each per the acceptance criteria).
- Domain names match existing conventions in CLAUDE.md (geospatial cross-cut, SU-1 error handling).

### writing-claims
- writing-claims:1: "7 domain checklists" — counted from routing table: Geospatial, SQL safety, Lazy-loading integrity, Credential safety, Error handling, Notebook coherence, Packaging truth.
- writing-claims:2: "118 insertions" — from `git diff --stat`.

### Mechanical gates
Syntax check: N/A (no .py changes, no .sh changes)
Test suite: N/A (no test suite in claude-configs-public)
Doc build: N/A (no docs/ changes)
Notebook API check: N/A (no notebook changes)

## Lead review (the Lead's adversarial pass)

### Phase A: Internal coherence

- **Design note → implementation**: Design note specifies a routing table with 7 domains, each with 3-5 checklist items, placed between Peer review and Lead review. The diff matches exactly.
- **Ticket acceptance → implementation**: Ticket says "routing table mapping diff patterns to domain checklists" (present), "3-5 specific items" (all checklists have 3-4), "grep-based" (activation section shows git diff commands), "universal Lead checklist always runs" (explicitly stated), "at least one references existing skill" (Geospatial checklist references the geo/ module patterns; Error handling references SU-1 from CLAUDE.md).

### Phase B: External verification

1. **Did the Junior fix the problem or move it?** The problem is that review applies uniform depth regardless of diff content. The routing table adds targeted depth for 7 domains. The universal checklist still always runs. Additive, not substitutive.

2. **What was dismissed?** Nothing — this is a pure addition with no tradeoffs to dismiss.

3. **Knowledge loci**: Self-review SKILL.md is both the deliverable and the knowledge locus. Updated directly.

4. **Mechanical gates**: No applicable gates for a .md-only change beyond structural presence, which the hook checks.

## Findings

No findings.

## Quantified claims

- "118 insertions" — `git diff --stat` output.
- "7 domain checklists" — counted from routing table rows.
- "1 file changed" — `git diff --stat` output.
