---
name: causal-inference-mixtape
description: 'Applied causal-inference handbook covering DAGs, RD, IV, DiD, synthetic control, and panel methods — the methods econometricians actually use. Use when the user mentions "regression discontinuity", "RDD", "instrumental variables", "IV", "difference-in-differences", "DiD", "synthetic control", "panel data", "natural experiment", "quasi-experiment", "Cunningham", or "Mixtape". Also trigger when looking for an empirical strategy to identify a causal effect from observational data, debating which natural-experiment design fits the data shape, or learning the practical mechanics of a specific identification strategy. More applied / hands-on than causal-inference-what-if (which is the theoretical foundation); pair them. For pure Bayesian framing see statistical-rethinking-course; for applied non-causal stats see think-stats.'
license: 'Free online; commercial print via Yale University Press'
metadata:
  source: 'mixtape.scunning.com — full free online edition of Causal Inference: The Mixtape (Scott Cunningham, Baylor). Yale University Press publishes paid print edition.'
  coverage: 'Full book (11 chapters) freely readable inline. Verified 2026-05-17 via WebFetch (intro + Chapter 3 DAGs).'
---

# Causal Inference: The Mixtape — Framework

A hands-on, code-heavy handbook of identification strategies for causal inference from observational data. Where What If grounds the theoretical foundations, Mixtape walks through the specific quasi-experimental designs — regression discontinuity, instrumental variables, difference-in-differences, synthetic control — that practitioners actually deploy on real research questions.

## Core Principle

**Most causal questions can't be answered by randomized trials; the methodological challenge is finding (or creating) variation that approximates randomization.** Each identification strategy — RD, IV, DiD, synthetic control — exploits a different kind of as-good-as-random variation: a sharp cutoff, an instrument that affects treatment but not outcome directly, a policy change affecting one group and not another, a counterfactual constructed from untreated units. The discipline is matching the strategy to the data structure and being explicit about which "as-good-as-random" assumption you're relying on.

**The foundation:** every design has a *fundamental assumption* without which it doesn't identify a causal effect. For RD, it's continuity at the cutoff. For IV, it's the exclusion restriction. For DiD, it's parallel trends. For synthetic control, it's that the synthetic counterfactual is a good match in the pre-period. State the assumption, defend it, test it (when possible), report sensitivity.

## Scoring

**Goal: 10/10.** When evaluating an applied causal analysis using a quasi-experimental design, rate 0-10.

- **9-10:** Design fits the data structure; fundamental assumption stated + defended + tested where possible; placebo / falsification tests run; standard errors clustered appropriately; sensitivity analysis reported.
- **7-8:** Design choice defensible; assumption stated; one robustness check missing.
- **5-6:** Design applied without articulating the fundamental assumption; placebo tests skipped; standard errors not clustered.
- **3-4:** Design mismatched to data structure (e.g., RD without a sharp cutoff); fundamental assumption violated and unaddressed.
- **1-2:** "Natural experiment" framing without actually using a quasi-experimental method; correlation results dressed as causal.

## The Five Core Identification Strategies

### 1. DAGs (Directed Acyclic Graphs) — chapter 3

DAGs encode causal structure as nodes (variables) and arrows (causal effects). Three critical structural patterns:

- **Fork (confounder):** common cause of treatment and outcome. *Condition on* to close the spurious path.
- **Chain (mediator):** on the causal path from treatment to outcome. Conditioning blocks the indirect effect.
- **Collider:** common effect of treatment and outcome. *Do NOT condition on* — conditioning OPENS a spurious path.

**Backdoor criterion:** a set of covariates Z closes all non-causal paths between treatment T and outcome Y iff Z blocks every "backdoor" path (one ending in an arrow into T) and Z contains no descendants of T.

**Collider bias is the most counterintuitive failure mode.** Worked examples in the book: gender discrimination, occupational sorting, police use of force, movie-star selection. Conditioning on "intermediate outcomes" that are actually colliders can flip the sign of an apparent effect.

### 2. Regression Discontinuity (RD) — chapter 6

When treatment is assigned by a sharp cutoff on a running variable (e.g., test score ≥ 70 → admitted), units just above and just below the cutoff are locally comparable. Compare outcomes for units in a narrow window around the cutoff.

**Fundamental assumption:** continuity of potential outcomes at the cutoff. The conditional expectation E[Y|X=x] would have been smooth at the cutoff in the absence of treatment.

**Sharp vs fuzzy RD:**
- Sharp: cutoff perfectly predicts treatment (admitted iff score ≥ 70).
- Fuzzy: cutoff strongly predicts but doesn't determine (treatment compliance < 100% at cutoff). Estimate via IV.

**Threats:** running-variable manipulation (people gaming the score), discontinuous covariates at the cutoff, bandwidth-choice sensitivity. Standard practice includes density tests at the cutoff (McCrary test) and placebo cutoffs at non-policy values.

### 3. Instrumental Variables (IV) — chapter 7

An instrument Z affects treatment T but does not affect outcome Y except through T. Use variation in T induced by Z to estimate the causal effect of T on Y.

**Fundamental assumptions:**
- **Relevance:** Z actually predicts T (test via first-stage F-statistic; weak instruments produce biased estimates).
- **Exclusion restriction:** Z affects Y only through T, not directly.
- **Monotonicity (for LATE):** Z doesn't push some units toward T while pulling others away.

**LATE interpretation:** IV identifies the Local Average Treatment Effect — the effect on *compliers* (units whose treatment status changed because of Z), not on the population. Different IVs identify different LATEs; pooling them requires care.

**Weak-instrument warning:** if first-stage F < ~10, the IV estimate is biased even in large samples. Multiple weak instruments combined are worse, not better.

### 4. Difference-in-Differences (DiD) — chapter 9

Compare the change in outcomes in a treated group to the change in a control group. The double-difference cancels group-specific time-invariant confounders.

**Fundamental assumption:** parallel trends. In the absence of treatment, the treated and control groups would have followed the same trajectory.

**Tests:**
- Pre-trend visualization (groups should track in pre-period)
- Placebo DiD on pre-period only
- Event-study plots (coefficients should be flat pre-treatment)

**Modern caveats (the "two-way fixed effects" critique):** with staggered treatment timing and heterogeneous effects, the standard two-way fixed-effects regression can produce biased estimates with weights including negative values for already-treated units. Recent literature (de Chaisemartin & D'Haultfœuille, Goodman-Bacon, Sun & Abraham, Callaway & Sant'Anna) provides better estimators. The book covers the staggered-treatment problem and the modern fixes.

### 5. Synthetic Control — chapter 10

When you have one treated unit and many candidate control units, construct a "synthetic" control as a weighted combination of donor units that matches the treated unit's pre-treatment outcomes. Compare post-treatment to the synthetic.

**Fundamental assumption:** the synthetic counterfactual is a good match (low pre-period RMSPE relative to placebo synthetics on untreated donors).

**Inference:** standard errors are unconventional. Common approach: placebo tests on every donor unit, then assess whether the treated unit's post-treatment gap is extreme relative to the placebo distribution.

**Use cases:** policy interventions in a single jurisdiction (Abadie's California Prop 99 / tobacco), one-state policy changes, single-event studies.

## Panel Data and Two-Way Fixed Effects — chapter 8

For repeated observations of the same units over time, panel-data methods control for unit-specific and time-specific confounders via fixed effects. Standard for any longitudinal observational study.

**Two-way fixed effects** (unit + time FE) is the workhorse; the modern critique (covered in DiD section) applies when treatment timing varies across units.

## When this skill does NOT apply

- **Pure theoretical questions** about identifiability — see causal-inference-what-if (the rigorous foundation).
- **Bayesian inference** — see statistical-rethinking-course.
- **Non-causal applied stats** — see think-stats.
- **Randomized trials** — design-based; standard methods work.

## Companions

- `causal-inference-what-if` — shelf-mate; theoretical foundation that grounds the assumptions Mixtape exploits.
- `think-stats` — for non-causal applied work.
- `statistical-rethinking-course` — for Bayesian alternative framing.
- `engineering-principles/` — code-craft for the analysis pipeline.

## Source + license

- **Source:** mixtape.scunning.com — *Causal Inference: The Mixtape* (Scott Cunningham, Baylor University).
- **License:** free online; Yale University Press publishes the paid print edition.
- **Verified:** WebFetch 2026-05-17 on `mixtape.scunning.com` (TOC, 11 chapters) and `/03-directed_acyclical_graphs` (substantive chapter content with DAG framework, backdoor criterion, collider-bias examples).

## See also

- Session 260502-pure-vista's `plans/shelf-recommendations-for-su-roles.md` — context on why Mixtape was the applied-causal complement to What If on the statistical-inference shelf. Operator wanted "all three" statistical flavors; Mixtape + What If together cover the causal flavor at both applied and theoretical depth.
