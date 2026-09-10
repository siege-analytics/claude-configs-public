# Self-review - #870 strategic agency doctrine

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: GitHub issue #870 and operator guidance in session 260905-clever-quasar.
Goal source verification: PASS - issue #870 asks configs to explain strategic agency, tactical goal advancement, proactive hub/worker behavior, and valid guidance-seeking.
Plan reference: TRIVIAL - small rule documentation update.
Pre-author-inventory: inspected RULES index, session-coordination, tandem-agent, work-item-ownership, and coverage matrix before editing.
Investigate-artifact: TRIVIAL - focused source inspection in session transcript.
Pre-mortem-artifact: TRIVIAL - main risk is turning autonomy into unsafe guessing; mitigation is rule 4 and cross-links to authorization, review, and operator-control rules.
Hostile-review-artifact: WAIVED (doctrine/prose-only change with scanner and build validation).
Project-contribution: makes the always-on configs explain why hub and worker rules exist: mission progress through bounded initiative, not compliance or passivity.

## Peer review
- Scope is limited to one new meta-rule file plus index, tandem, work-item, and coverage wiring.
- The rule file states that hubs and workers should choose safe tactical ordering and continue when order is non-critical.
- The rule file also states that asking for guidance is correct when the choice affects strategy, authorization, risk, public behavior, or operator control.
- Coverage rows make both failure modes auditable: tactical passivity and guidance avoidance.

## Lead review
- Correctness: the doctrine captures strategic goal, tactical goals, bounded initiative, and appropriate advice-seeking.
- Safety: the change preserves authorization, review, reversibility, and operator steering boundaries.
- Verification: focused assertions, build, whitespace check, and staged scanner passed.
- Merge plan: PR targets develop first, then a linear promotion PR moves develop to main.

## Quantified claims
- The new strategic-agency file has four numbered rules: verified by regex assertion.
- The coverage matrix has 29 judgment rows after adding two rows: verified by status-count script and summary update.
