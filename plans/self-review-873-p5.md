---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
---

# Self-review: #873 P5 -- KB consultation advisory-until-opt-in

## What changed
- `hooks/resolver/think-gate-guard.sh`: the Level-3 KB check emits the
  `BLOCKED:` prefix (which ca-enforcement-gate converts to a halt) ONLY when a
  PROJECT.md declares `kb_enforcement: blocking`. Otherwise it prints an
  advisory reminder that ca-enforcement does not catch.
- `hooks/_test/kb_consultation_advisory.test.sh` (new): 3 scenarios.

## Why
D2: the KB check hard-halted any turn whose think-gate lacked a `kb` section
when a PROJECT.md declared `knowledge_base:` -- including unrelated work
(observed 2026-09-12 on this epic's own task). Blocking should be a declared
project escalation, not the default. Advisory still narrates the reminder.

## Assumptions
- `kb_enforcement: blocking` is matched by an anchored line regex in the
  PROJECT.md, consistent with the frontmatter reader style. Absent -> advisory.
- The advisory path still prints the same reminder body, so no information is
  lost; only the BLOCKED: prefix (the ca-enforcement trigger) is withheld.

## Peer review (mechanics, correctness, craft floor)
- Syntax: `bash -n hooks/resolver/think-gate-guard.sh` ok.
- Resolver suite still 18/0 (the guard is exercised there), so no regression to
  the other think-gate-guard levels.
- The opt-in scan reuses the same project_files list already gathered for the
  knowledge_base: detection; one extra regex, no new file walk.

## Lead review (adversarial: did this actually solve it?)
- Does an unrelated task still get hard-blocked by KB? No -- default is advisory
  (tested: reminder shown, no BLOCKED: prefix).
- Can a project that wants hard enforcement still get it? Yes -- kb_enforcement:
  blocking restores BLOCKED: (tested).
- Did any other gate level change? No -- only the KB (Level 3) block prefix is
  conditional now; the warning content and the other levels are untouched.

## Quantified claims
- "3/0" -- `bash hooks/_test/kb_consultation_advisory.test.sh` -> `Results: 3 passed, 0 failed`
- "resolver suite still 18/0" -- `bash hooks/_test/session_signal_resolution.test.sh` -> `Results: 18 passed, 0 failed`

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| (none) | - | - | - | - |

## Trivial-investigation declaration
Not trivial -- #873 investigation and pre-mortem exist.
