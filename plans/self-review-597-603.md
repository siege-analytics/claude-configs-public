---
ticket_refs:
  - siege-analytics/claude-configs-public#597: open
  - siege-analytics/claude-configs-public#598: open
  - siege-analytics/claude-configs-public#599: open
  - siege-analytics/claude-configs-public#600: open
  - siege-analytics/claude-configs-public#601: open
  - siege-analytics/claude-configs-public#602: open
  - siege-analytics/claude-configs-public#603: open
type: self-review
---

## Self-review for #597–#603: enforcement contradiction rule hardening

Working as: software engineer

## Assumptions

Domain(s): software engineering, enforcement pipeline design
Geospatial cross-cut: no
Goal source: tickets #597–#603 (filed from cross-review findings)
Plan reference: hostile-review-595.md, hostile-review-595-gpt55.md (session plans)
Pre-author-inventory: NONE
Trivial-against-state: rewrite of rule file and RESOLVER.md table row; no executable code changes, no hook modifications
Investigate-artifact: cross-review findings from Sonnet + GPT-5.5
Pre-mortem-artifact: WAIVED (rule text only, no executable code)
Hostile-review-artifact: plans/hostile-review-595.md (Sonnet), plans/hostile-review-595-gpt55.md (GPT-5.5)
Project-contribution: Closes the gaps identified by two independent hostile reviews of the enforcement contradiction escalation rule. Makes the rule resistant to gaming by requiring evidence before escalation, routing by blast radius, and defining fix guardrails.

## Pre-implementation comprehension

**Current behavior:** The enforcement contradiction rule (#595) allows agents to self-certify contradictions with no evidence threshold, mandates pivoting for ALL contradictions regardless of severity, has 4 taxonomy classes that miss common real-world failures, provides no fix guardrails, and depends entirely on agent judgment with no mechanical enforcement.

**Intended behavior:** Evidence packet required before escalation. Triage by blast radius (pivot only when blocking + reproducible + same surface + agent-owned). 7 taxonomy classes covering transient, context mismatch, and unresolvable prerequisite. Fix guardrails requiring regression tests. Explicit cascade depth limit. Mechanical enforcement documented as future requirement.

**Steps:** Two files: rewrite `skills/_enforcement-contradiction-rules.md` and update one row in `RESOLVER.md` failure-handling table.

**Success criteria:** Rule file addresses all 7 tickets. RESOLVER.md row matches the new rule structure. No executable code changed.

**What could go wrong:** Agent weaponizes new complexity to claim "I couldn't figure out the classification" and stalls. Mitigated by: the detection threshold is binary (gate fired or it didn't), and transient/context-mismatch classes have self-resolution paths that don't require tickets.

## Peer review (the Junior's checklist)

Syntax check: N/A (no .py or .sh changes — rule file is markdown only)
Test suite: N/A (no executable code modified)
writing-code: no code changes; rule file follows existing _*-rules.md format (frontmatter + heading + sections)
writing-claims: 2 files modified (skills/_enforcement-contradiction-rules.md, RESOLVER.md); all 7 ticket numbers cited; cross-review provenance from two independent reviewers (Sonnet session 260610-tidy-coyote, GPT-5.5 session 260630-ruby-ember)

## Lead review (the Lead's adversarial pass)

In software engineering: this rewrite closes the six highest-confidence gaps identified by two independent hostile reviews. The evidence threshold (gate must have actually fired + captured output + bounded diagnostics) prevents speculative contradiction claims. The blast-radius triage prevents work avoidance via minor unrelated false positives. The cascade depth limit prevents infinite ticket chains. The fix guardrails prevent enforcement weakening.

**Approach fit:** Correct level of intervention — still a rule, not a hook. The rule explicitly acknowledges it depends on agent judgment and documents what mechanical enforcement (#602) would look like. This is honest about its limitations rather than pretending behavioral guidance is mechanical enforcement.

**Remaining risk:** The rule is still behavioral guidance. Until #602 (meta-hook) is implemented, a determined adversarial agent can still ignore it. The self-review hook and operator oversight are the enforcement mechanisms. This is explicitly acknowledged in the "Mechanical enforcement" section.

**Blast radius:** Minimal. Rule file rewrite, one table row in RESOLVER.md. No hooks modified, no signal files changed, no executable code touched.

## Findings

No findings.

## Quantified claims

- "2 files modified" — `git diff --stat` on this branch
- "7 taxonomy classes" — enumerated in the rule file under "## Contradiction taxonomy"
- "7 tickets addressed" — #597 (evidence packet), #598 (severity routing), #599 (emergency break-glass), #600 (cascade limit), #601 (taxonomy expansion), #602 (mechanical enforcement), #603 (fix guardrails)
- "Two independent reviewers" — Sonnet (call_llm in session 260610-tidy-coyote), GPT-5.5 (spawn_session 260630-ruby-ember on chatgpt-plus connection)

## Rework ledger

No rework occurred.

## Evidence-predates-work

Artifact: plans/self-review-597-603.md
