---
name: rule-eval-loop
description: "How to design Tier-3 rules so they ship well-calibrated. Three independent arcs (negotiation, audit, library-fix) with separate stopping criteria. Cross-pass evidence + ratified wording + fix-exercise validation = three samples per rule before ship. Promoted from LESSON 323a0f5 after recurrence reached 4 across the v2.2.0 + v2.3.0 cycles."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash
---

# Rule-eval-loop discipline

This skill documents the discipline that turns Tier-3 rule proposals into well-calibrated shipped rules. Use it when opening a new rule-set negotiation cycle, when running a hostile-review audit, or when applying a rule retroactively to a codebase. It does not write rules; it names the loop's shape so operators running the loop know which arc they are closing at any moment.

## The three arcs

Three independent arcs run in parallel during any rule-set evolution. They have independent timelines and independent closing criteria. Conflating them causes one arc to wait on another that is on a different schedule, slowing the whole cycle.

### Negotiation arc

**Owns:** Tier-3 rule wording, identifier placement, scanner spec, coverage matrix entry.

**Closes when:** consensus on wordings + tier-placement is reached across the involved sessions, with verbatim sign-off on every drift-watch item.

**Anti-pattern:** continuing to negotiate after consensus on the substance, looking for further refinement when the rule has converged. Counter: if the next round produces no wording change, the arc has closed; ship.

### Audit arc

**Owns:** discovering rule-gap candidates by hostile-reviewing real code across module shapes.

**Closes when:** one full sweep across uncovered module shapes yields zero new rule-gap candidates AND all parked candidates are negotiated/shipped/explicitly deferred.

**Anti-pattern:** stopping after one or two passes because no new candidates surfaced. Counter: the diminishing-returns curve is real but unevenly distributed across module shapes; pre-rule-era code has more findings than rule-aligned code, and security/credential domains hit different patterns than UI/output domains. Confirm the curve has actually flattened across diverse shapes, not converged on a single shape's empty pass.

### Library-fix arc

**Owns:** resolving specific instances surfaced by audit passes — the actual code fixes against shipped rules.

**Closes when:** every Critical/Major finding from any audit pass is shipped or explicitly deferred to a tracked ticket. Minor findings are batch-deferred without per-instance tickets when the volume is high.

**Anti-pattern:** treating every audit finding as blocking the library-fix arc close. Counter: the library-fix arc closes against a triage threshold (Critical/Major), not against the audit arc's complete output. A library can have a "good ruleset and a good library" with deferred Minor findings tracked.

## Two-arcs-decoupling observation

The audit arc and library-fix arc decouple at the diminishing-returns inflection. After enough hostile-review passes (typically 6-8 in a single library), audit finds patterns; library fixes resolve specific instances. Audit closes faster than library-fix because audit converges on rule-gap exhaustion while library-fix scales linearly with finding count.

Operators running the loop should expect this decoupling and not hold the audit arc open waiting for library-fix. The two arcs run independent timelines.

## The three-samples-before-ship discipline

A Tier-3 rule should have three independent samples of evidence before it ships, each from a different observation point in the loop:

1. **Sample 1 — Originating finding.** The first instance that surfaced the rule. Single module shape, single failure case. Insufficient evidence to ship (the rule may over-fit the originating shape).
2. **Sample 2 — Cross-pass transferability.** A second hostile-review pass on a different module shape (HTTP fetcher vs engine abstraction; output generator vs data source; CLI vs library). If the rule does not bite in pass 2, it is over-fit to pass 1's shape and needs broader wording. If it does bite, the wording generalizes.
3. **Sample 3 — Fix-exercise validation.** Ratified wording applied by an operator to fix the originating findings. If the rule bites cleanly without the operator needing to interpret around the wording, the rule is well-calibrated. If the operator routinely chooses around the rule's options, the rule is too directive or too loose; the wording needs refinement.

Three samples is the minimum. Five (RG-7's "no silent processes" had five module-shape evidence points before ship) is better. One is not enough — single-pass evidence systematically over-fits.

## Recurrence ledger

The eval-loop discipline itself has been validated across these instances:

| # | Date | Instance | What was validated |
|---|---|---|---|
| 1 | 2026-05-13 | v2.2.0 ratification | Cross-pass evidence (engines + HTTP fetcher) + four-round wording negotiation produced rules that bit cleanly. |
| 2 | 2026-05-13 | v2.2.0 fix exercise (siege_utilities PR #478) | All four v2.2.0 rules (writing-code:9, writing-code:10, writing-prose:1 extended, writing-releases:3) bit cleanly with zero wording mis-fires. |
| 3 | 2026-05-13 | v2.3.0 negotiation drift discipline | Three-round negotiation with sequencing reversal mid-cycle (RG-7 alone vs ship-all-five) demonstrated the negotiation arc tolerates reversal when reasoning improves; sequencing converged at RG-7 alone after honest cost-benefit re-examination. |
| 4 | 2026-05-13 | v2.3.0 fix exercise (siege_utilities PR #487 + PR #484) | Pre-registered hypothesis confirmed: floor + additive bit cleanly across four module shapes; (a)+(b) was operational default for library entry points; per-process-type advisory landed correctly in 4 of 5 cases. |

Promotion threshold for the eval-loop discipline as a meta-skill: recurrence ≥ 3. Cleared at instance 3; this skill opens at instance 4 with empirical validation across the v2.2.0 and v2.3.0 cycles.

## Application

When opening a new rule-set negotiation cycle:

1. Open audit arc first (one or more hostile-review passes against the originating module shape).
2. After the originating arc surfaces candidates, open negotiation arc on the candidate wordings.
3. Run cross-pass transferability check before sign-off (sample 2).
4. Ship as RC.
5. Run fix-exercise validation against the RC (sample 3).
6. Promote to final.
7. Library-fix arc continues independently as discoveries surface.

Each arc has its own stopping criterion (above). Do not block one on another.

## Skipping the loop

Single-pass-only rules are acceptable when:

- The originating finding is itself cross-cutting (operator-stated principles like writing-code:11 had four-pass evidence at first negotiation; the discipline was already met).
- The rule extends an existing well-validated rule (the writing-tests:1 retroactive-fix corollary was a body extension, not a new rule).
- The failure mode is obvious enough that wording need not be negotiated (typo fixes, scanner pattern updates, character-class extensions).

When in doubt, run the loop. The cost of an over-fit rule is paid by every consumer; the cost of one extra hostile-review pass is paid once.

## Cross-references

- `[`lessons-learned`](../../meta/lessons-learned/SKILL.md)` — Tier-1 ledger; eval-loop instances get filed there as evidence before being promoted into this skill.
- `[`rules-audit`](../../meta/rules-audit/SKILL.md)` — cross-tier hygiene pass; complements this skill at the maintenance level (this skill is about rule design; rules-audit is about rule consistency over time).
- `[`distill-lessons`](../../meta/distill-lessons/SKILL.md)` — Tier-1 to Tier-2 promotion mechanics.

## Attribution

Defers to `[`output`](../../_output-rules.md)`. No AI / agent attribution in this skill or its instances.
