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

**Owns:** resolving specific instances surfaced by audit passes; the actual code fixes against shipped rules.

**Closes when:** every Critical/Major finding from any audit pass is shipped or explicitly deferred to a tracked ticket. Minor findings are batch-deferred without per-instance tickets when the volume is high.

**Anti-pattern:** treating every audit finding as blocking the library-fix arc close. Counter: the library-fix arc closes against a triage threshold (Critical/Major), not against the audit arc's complete output. A library can have a "good ruleset and a good library" with deferred Minor findings tracked.

## Two-arcs-decoupling observation

The audit arc and library-fix arc decouple at the diminishing-returns inflection. After enough hostile-review passes (typically 6-8 in a single library), audit finds patterns; library fixes resolve specific instances. Audit closes faster than library-fix because audit converges on rule-gap exhaustion while library-fix scales linearly with finding count.

Operators running the loop should expect this decoupling and not hold the audit arc open waiting for library-fix. The two arcs run independent timelines.

## The three-samples-before-ship discipline

A Tier-3 rule should have three independent samples of evidence before it ships, each from a different observation point in the loop:

1. **Sample 1, originating finding.** The first instance that surfaced the rule. Single module shape, single failure case. Insufficient evidence to ship (the rule may over-fit the originating shape).
2. **Sample 2, cross-pass transferability.** A second hostile-review pass on a different module shape (HTTP fetcher vs engine abstraction; output generator vs data source; CLI vs library). If the rule does not bite in pass 2, it is over-fit to pass 1's shape and needs broader wording. If it does bite, the wording generalizes.
3. **Sample 3, fix-exercise validation.** Ratified wording applied by an operator to fix the originating findings. If the rule bites cleanly without the operator needing to interpret around the wording, the rule is well-calibrated. If the operator routinely chooses around the rule's options, the rule is too directive or too loose; the wording needs refinement.

Three samples is the minimum. Five (RG-7's "no silent processes" had five module-shape evidence points before ship) is better. One is not enough; single-pass evidence systematically over-fits.

## Composition-conflict-resolution

When designing a new Tier-3 rule, check whether complying with the new rule could force violating an existing ratified rule. The fix exercise often surfaces this: an operator applies the new rule and discovers that a fix satisfying its wording would simultaneously violate another rule's wording.

**Three-part discipline:**

- **Detection:** the fix exercise reveals that complying with rule A forces violating rule B in some non-trivial fraction of cases.
- **Resolution:** the rule whose wording is being violated to comply with the other gets a body extension (or carve-out) naming the composition + override. The override clause makes the precedence explicit so future operators do not re-discover and re-litigate the conflict.
- **Anti-pattern:** silently choosing one rule over the other without documenting the precedence. Future operators encounter the same conflict, derive different precedence, and produce inconsistent fixes across the codebase.

Originating evidence (recurrence 1): v2.3.1 surfaced this during the v2.3.0 fix exercise (siege_utilities PR #487). The writing-code:11 floor menu (a)/(b)/(c)/(d) would have forced changing `_ensure_sedona`'s pre-existing `None`-return contract to satisfy the menu, which would have violated writing-releases:1 (BREAKING-when-public-surface-changes-incompatibly) for a 5%-of-cases scenario (1 of 5 functions in the fix exercise). The contract-preservation override carve-out added to writing-code:11's body in v2.3.1 names the composition explicitly: writing-code:11 yields to writing-releases:1 when the floor change would break an established contract.

Empirical signal worth banking: the conflict appeared in 1 of 5 cases (20%), not as a one-off edge case. Any time a new rule's mechanical or judgment-driven application appears in a non-trivial fraction of fix-exercise cases to force a violation of another ratified rule, the override clause is required, not optional.

This principle is itself a recurring discipline: when promoted by recurrence ≥ 2 across multiple rule cycles, it becomes a Tier-3 rule about rule design rather than a meta-skill body extension. For now, recurrence 1; ship as documented principle. Second instance promotes to validated discipline.

## Recurrence ledger

The eval-loop discipline itself has been validated across these instances:

| # | Date | Instance | What was validated |
|---|---|---|---|
| 1 | 2026-05-13 | v2.2.0 ratification | Cross-pass evidence (engines + HTTP fetcher) + four-round wording negotiation produced rules that bit cleanly. |
| 2 | 2026-05-13 | v2.2.0 fix exercise (siege_utilities PR #478) | All four v2.2.0 rules (writing-code:9, writing-code:10, writing-prose:1 extended, writing-releases:3) bit cleanly with zero wording mis-fires. |
| 3 | 2026-05-13 | v2.3.0 negotiation drift discipline | Three-round negotiation with sequencing reversal mid-cycle (RG-7 alone vs ship-all-five) demonstrated the negotiation arc tolerates reversal when reasoning improves; sequencing converged at RG-7 alone after honest cost-benefit re-examination. |
| 4 | 2026-05-13 | v2.3.0 fix exercise (siege_utilities PR #487 + PR #484) | Pre-registered hypothesis confirmed: floor + additive bit cleanly across four module shapes; (a)+(b) was operational default for library entry points; per-process-type advisory landed correctly in 4 of 5 cases. |
| 5 | 2026-05-13 | v2.3.1 fix exercise (siege_utilities PR #489) | All five v2.3.1 rules bit cleanly with zero wording mis-fires. Eight rules across the v2.2.0 + v2.3.0 + v2.3.1 cohorts have originating + cross-pass + fix-exercise evidence with zero shipped rule needing a patch. Three v2.3.x wording observations banked for follow-up (per-rule-commit composes naturally one-site-one-commit when fix satisfies two composing rules in same file; writing-code:13 rename-over-converge option zero-of-five frequency; writing-tests:1 self-validation held empirically at recurrence 2). |
| 6 | 2026-05-14 | v2.4.0 fix exercise (siege_utilities PR #491) | **Reverse self-validation.** Two of the three writing-code:14 originating cases (DuckDBEngine `_parse_geom` in PR #478, logging.py `_create_rotating_file_handler` in PR #480) were already fixed by an operator who did not know writing-code:14 existed yet. Independent fix-shape matched the rule's prescribed shapes. Reverse self-validation is sharper than ordinary fix-exercise validation: the rule is capturing pre-existing operator discipline rather than imposing new constraints. Recurrence 3 of "discipline produces well-calibrated rules at consistent cadence" reached: nine rules across four cohorts (v2.2.0/v2.3.0/v2.3.1/v2.4.0) bitten cleanly with zero wording mis-fires. Skipping-the-loop carve-outs candidate for tightening in v2.5.0 from "acceptable when X" to "mandatory unless X." |
| 7 | 2026-05-14 | v2.6.0 negotiation + fix exercise (siege_utilities PR #492) | **Discipline-defense recurrence-2 + writing-code:3 self-application during rule drafting.** Two distinct framework signals at a single release. (1) Discipline-defense recurrence-2: v2.4.0 RG-8 deferral (recurrence 1) + v2.6.0 candidate-2 deferral. Per the composition-conflict-resolution body extension's "second instance promotes from documented principle to validated discipline" clause, the discipline-defense pattern is empirically validated. (2) writing-code:3 self-application during rule drafting (recurrence 1, distinct shape from reverse-self-validation): round-1 wording included DB-client call surfaces (psycopg2/asyncpg/pymongo/redis/kafka) with no empirical evidence; sibling caught the writing-code:3 (no speculative abstractions) violation in the rule's own design process. Final list shipped empirical-evidence-only. The discipline self-applied at draft time, before fix-exercise. Fix-exercise validation: zero violations on touched branch, zero scanner porting drift between sibling-local script and v2.6.0-rc1-tagged scanner; both known scanner gaps stayed parked as predicted. Hypothesis confirmed end-to-end. |

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

**Process-discipline addition (v2.5.x).** When running wording-review on a skill-file or rule-file PR, run `bash skills/meta/detect-ai-fingerprints/scan.sh --pr <n>` against the diff before signing off. This catches new typographic Unicode characters in added lines per writing-prose:1; pre-existing characters are out of scope (forward-only). The character-class scan is part of wording review, not separate from it: a clean wording-review pass requires both the wording substance to match negotiation AND the diff to be character-class-clean. The PR #65 / PR #70 sequence demonstrates the gap: PR #65 (RD-1 v1) shipped with eight em-dashes in added lines that neither side ran the scanner against; PR #70's self-dogfood caught them retroactively as out-of-scope finding. Even after RD-1's three-arc framing is internalized, process-level steps can drift; this addition closes the wording-review-without-scanner gap.

## Skipping the loop (tightened v2.5.0)

**Three-samples-before-ship is mandatory. Single-pass-only is acceptable only when the candidate rule meets at least one of these carve-outs:**

- (a) The originating finding is itself cross-cutting (operator-stated principles like writing-code:11 had four-pass evidence at first negotiation; the discipline was already met).
- (b) The rule extends an existing well-validated rule via body extension (the writing-tests:1 retroactive-fix corollary was a body extension, not a new rule).
- (c) The failure mode is obvious enough that wording need not be negotiated (typo fixes, scanner pattern updates, character-class extensions).

**Anti-pattern: bundling-convenience justification.** "We're shipping a cohort, and this candidate doesn't quite have three samples but it would be nice to bundle" is not a carve-out. The v2.4.0 RG-8 case demonstrates the discipline being defended: proposed for v2.4.0 with one module shape of evidence, deferred to v2.5.0+ pending cross-pass evidence after the originating side audited their own carve-out claim and found none applied. Future cohorts should pre-empt the request rather than wait for the defense; if cross-pass evidence is not yet in hand and none of (a)/(b)/(c) applies, the candidate stays parked.

**Reverse self-validation as the strongest signal.** The v2.4.0 fix exercise (siege_utilities PR #491) demonstrated reverse self-validation: two of the three writing-code:14 originating cases were already fixed by an operator who did not know the rule existed yet, with fix-shapes matching the rule's prescribed shapes independently. When candidate-rule wording matches independently-arrived-at operator decisions, the rule is capturing pre-existing operator discipline rather than imposing new constraints; this is sharper than ordinary fix-exercise validation. Watch for it: if the originating fix-exercise produces "I already did this naturally," promote that observation into the originating-arc citation; it is the cleanest possible evidence for ratification.

**Tightening rationale (recurrence-3 evidence, v2.5.0).** This section was loosened-shape ("acceptable when X/Y/Z") in RD-1 v1 because the discipline was unproven at promotion time. After three cohorts shipped clean (v2.2.0/v2.3.0/v2.3.1/v2.4.0 = nine rules across four cohorts with zero wording mis-fires), the discipline is empirically validated. The carve-outs stay (the three cases are real), but the default flips: three-samples is the load-bearing rule; carve-outs are exceptions that must be claimed and defended.

When in doubt, run the loop. The cost of an over-fit rule is paid by every consumer; the cost of one extra hostile-review pass is paid once.

## Cross-references

- `[`lessons-learned`](../../meta/lessons-learned/SKILL.md)`: Tier-1 ledger; eval-loop instances get filed there as evidence before being promoted into this skill.
- `[`rules-audit`](../../meta/rules-audit/SKILL.md)`: cross-tier hygiene pass; complements this skill at the maintenance level (this skill is about rule design; rules-audit is about rule consistency over time).
- `[`distill-lessons`](../../meta/distill-lessons/SKILL.md)`: Tier-1 to Tier-2 promotion mechanics.

## Attribution

Defers to `[`output`](../../_output-rules.md)`. No AI / agent attribution in this skill or its instances.
