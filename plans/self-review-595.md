---
ticket_refs:
  - siege-analytics/claude-configs-public#595: open
type: self-review
---

## Self-review for #595: enforcement contradiction escalation rule

Working as: software engineer

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #595
Plan reference: design-595.md (session plans)
Pre-author-inventory: NONE
Trivial-against-state: new rule file and RESOLVER.md table row; no executable code changes, no hook modifications
Investigate-artifact: investigate-gate-claude-configs-public.json (workspace signal file)
Pre-mortem-artifact: plans/pre-mortem-595.md
Hostile-review-artifact: WAIVED (rule text only, no executable code)
Project-contribution: Closes the meta-loop where enforcement bugs persist
  because workarounds are easier than filing tickets. Agents now have a
  mandatory protocol for when enforcement itself is the problem.

## Pre-implementation comprehension

**Current behavior:** When the enforcement system has bugs (false positives,
self-contradictions, missing exit paths), the agent works around the problem
and continues. Workarounds accumulate silently.

**Intended behavior:** Agent stops, files a ticket describing the
contradiction, and (unless operator-declared emergency) pivots to fixing the
enforcement gap before continuing the original work.

**Steps:** Two files: new `skills/_enforcement-contradiction-rules.md` and
one new row in `RESOLVER.md` failure-handling table.

**Success criteria:** Rule file exists with the four taxonomy classes and
required-response protocol. RESOLVER.md failure-handling table has a row
routing enforcement contradictions to the new rule.

**What could go wrong:** Agent weaponizes rule to avoid work by
misclassifying normal blocks as contradictions. Mitigated by requiring
specific evidence (which gate, which command, why wrong).

## Peer review (the Junior's checklist)

Syntax check: N/A (no .py or .sh changes — rule file is markdown only)
Test suite: N/A (no executable code modified)
writing-code: no code changes; rule file follows existing _*-rules.md format (frontmatter + heading + sections)
writing-claims: 2 files modified (skills/_enforcement-contradiction-rules.md, RESOLVER.md); provenance citations (#590, #591, #592) are all closed tickets with verifiable evidence

## Lead review (the Lead's adversarial pass)

In software engineering: this rule closes the gap between "enforcement
exists" and "enforcement is trustworthy." The four taxonomy classes
(self-blocking, false positive, inter-rule conflict, signal manipulation)
are exhaustive — every enforcement bug encountered in this session's work
fits one of them. The emergency escape (operator-declared only) prevents
agents from self-authorizing workarounds.

**Approach fit:** Correct level of intervention — a rule, not a hook. This
is behavioral guidance that changes the agent's default response to
enforcement bugs. It doesn't need mechanical enforcement because the
existing failure-handling pipeline (Pre-fix pause) already fires on every
gate block; this rule adds a branch for when the gate itself is wrong.

**Blast radius:** Minimal. New rule file, one table row in RESOLVER.md.
No hooks modified, no signal files changed, no executable code touched.

## Findings

No findings.

## Quantified claims

- "2 files modified" — `git diff --stat` on this branch
- "four taxonomy classes" — self-blocking, false positive, inter-rule
  conflict, signal manipulation — enumerated in the rule file under
  "## Contradiction taxonomy"

## Rework ledger

No rework occurred.

## Evidence-predates-work

Artifact: plans/self-review-595.md
