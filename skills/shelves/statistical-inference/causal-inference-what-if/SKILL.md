---
name: causal-inference-what-if
description: 'Canonical modern treatment of causal inference using the potential-outcomes / counterfactuals framework. Use when the user mentions "causal inference", "counterfactual", "potential outcomes", "ATE / ATT / CATE", "g-methods", "g-computation", "g-estimation", "marginal structural models", "IPW", "inverse probability weighting", "Hernan", "Robins", "What If book", "exchangeability", "positivity", or "consistency assumption". Also trigger when reasoning about whether an observational study can identify a causal effect, designing a target trial, picking between regression / matching / IPW / g-methods, or distinguishing association from causation. Heavier on theory and identification assumptions than the applied causal-inference-mixtape; pair them. For pure prediction / non-causal modeling see think-stats.'
license: 'Free PDF from authors (non-commercial; attribution required)'
metadata:
  source: 'miguelhernan.org/whatifbook — free PDF at /s/hernanrobins_WhatIf_21nov25.pdf (Hernán & Robins, Harvard / MIT). CRC Press / Chapman & Hall publishes paid print edition.'
  coverage: 'Full book, freely downloadable PDF, current revision dated 21 Nov 2025. Verified 2026-05-17 via WebFetch.'
---

# Causal Inference: What If — Framework

Modern canonical treatment of causal inference from a clinical-epidemiology lineage. The book teaches the disciplines that distinguish "X is correlated with Y" from "X causes Y," and the specific identification assumptions you must check (and the methods that work) when trying to estimate causal effects from observational data.

## Core Principle

**A causal effect is the difference between potential outcomes under different treatments, only one of which is observed for any individual.** Identification — going from observed associations to causal effects — requires explicit assumptions about exchangeability (no unmeasured confounding given measured covariates), positivity (all relevant treatment-covariate combinations have positive probability), and consistency (the observed outcome equals the potential outcome under the actually-taken treatment). If any of these assumptions fails, the standard regression / matching / weighting machinery produces numbers that look like causal estimates but aren't.

**The foundation:** causal claims are claims about what *would* have happened under a different action. The data you have only shows what *did* happen. Bridging that gap requires assumptions that must be named, justified, and checked. The book's central discipline: never make a causal claim without identifying which assumption you're relying on and stating the sensitivity of the conclusion to that assumption.

## Scoring

**Goal: 10/10.** When evaluating a causal-claim analysis, rate 0-10.

- **9-10:** Target trial specified; identification assumptions stated and defended; appropriate g-method or weighting used; sensitivity analysis to unmeasured confounding included; positivity verified; uncertainty propagated honestly.
- **7-8:** Estimand defined; one or two assumptions implicit but defensible; method-choice appropriate; sensitivity-analysis present but light.
- **5-6:** Regression model presented as causal without acknowledging which assumption makes it causal; positivity not checked; no sensitivity analysis.
- **3-4:** Observational data treated as if it were from a randomized trial; "controlling for X" presented as defeating confounding without explicit identification argument.
- **1-2:** Correlation-presented-as-causation in plain text; no causal vocabulary; "the data show that X causes Y" with no design.

## The Three Identification Assumptions

Every causal estimate from observational data depends on these three. Check each.

| Assumption | What it means | How it fails |
|---|---|---|
| **Exchangeability** | Treated and untreated groups are comparable on all confounders (conditional on measured covariates) | Unmeasured confounding — a variable that affects both treatment and outcome was not collected |
| **Positivity** | Every covariate stratum has both treated and untreated individuals | Some patient types are never given the treatment (no overlap); estimates rely on extrapolation, not data |
| **Consistency** | The observed outcome under treatment T equals the potential outcome had treatment been set to T | "Treatment" is not well-defined (e.g., "weight loss" — by what means? surgery vs diet have different effects) |

Without all three holding (or being explicitly relaxed via sensitivity analysis), you do not have causal identification.

## Target Trial Framing

The book's recurring discipline: specify the *target trial* you wish you had run, then ask what observational data can approximate it.

**Target trial spec:**
- Eligibility criteria (who's in the trial?)
- Treatment strategies (what are you comparing?)
- Assignment procedure (how are subjects assigned to strategies?)
- Follow-up period (what time horizon?)
- Outcomes (what are you measuring?)
- Causal contrast (intention-to-treat? per-protocol?)
- Analysis plan (what method, what subgroups?)

Then for the observational analysis:
- Which eligibility / treatment / outcome correspond to the target trial?
- Which differences from the target trial are confounders?
- Which assumption (exchangeability / positivity / consistency) is most fragile?

Target-trial framing prevents the most common error: estimating *some* effect without being clear which causal question you've answered.

## The Method Hierarchy

When confounding is **time-invariant** (a single decision point):
- Stratification / standardization
- Regression-based adjustment
- Matching / propensity-score methods
- Inverse-probability weighting (IPW)
- Doubly-robust estimators (combine outcome model + IPW)

When confounding is **time-varying** (sequential decisions, treatment-confounder feedback):
- Standard regression with time-varying covariates is BIASED (treatment-confounder feedback creates collider bias when conditioning on post-treatment covariates).
- **g-methods** are the appropriate machinery:
  - g-formula (parametric standardization across time)
  - IPW with marginal structural models
  - g-estimation of structural nested models

The book is THE canonical reference for g-methods. Time-varying confounding is the case where standard regression is most wrong; civic / health / longitudinal data is full of it.

## DAGs and Confounding Patterns

While Hernán & Robins use less DAG-focused notation than Pearl-school sources, the DAG vocabulary is interoperable:

- **Confounder (fork):** common cause of treatment and outcome. Must condition on (or otherwise adjust for).
- **Collider:** common effect of treatment and outcome. Must NOT condition on (creates spurious association when adjusted for).
- **Mediator (chain):** on the causal path. Conditioning blocks the indirect effect; the direct effect remains. Decision depends on whether you want total or direct effect.

The collider-bias intuition is the most counterintuitive: "controlling for X" can *introduce* bias when X is a collider. The book provides multiple worked examples.

## When this skill does NOT apply

- **Prediction questions** (will Y happen?) — causal inference is overkill; standard ML / regression is the right tool. See think-stats for applied prediction work.
- **Pure description / exploration** — causal framing is premature.
- **Randomized trial analysis** — the assumptions are guaranteed by randomization; standard methods are unbiased. Causal-inference machinery is most needed for observational data.
- **Applied econometrics / RD / IV / DiD** — see causal-inference-mixtape (Cunningham) which covers these designs in more applied detail. What If is the theoretical-foundations book; Mixtape is the applied-methods book. They compose.

## Companions

- `causal-inference-mixtape` — applied complement (DAGs, RD, IV, DiD, synthetic control). Same shelf.
- `think-stats` — for non-causal applied statistics (description, prediction, hypothesis testing). Same shelf.
- `statistical-rethinking-course` — for Bayesian framing; What If is largely frequentist but the framework is compatible.
- `spatial-data-science` — for spatial-statistics edge cases where causal inference meets autocorrelation.

## Source + license

- **Source:** miguelhernan.org/whatifbook → free PDF at `/s/hernanrobins_WhatIf_21nov25.pdf` (Miguel Hernán + James Robins, Harvard School of Public Health).
- **License:** free download for personal / educational use; attribution required. The paid CRC Press print edition is the same content.
- **Verified:** WebFetch 2026-05-17 confirmed the PDF download link on miguelhernan.org/whatifbook; current version dated 21 Nov 2025 (the book is actively maintained — the authors update revisions periodically and post the latest PDF freely).

## See also

- Session 260502-pure-vista's `plans/shelf-recommendations-for-su-roles.md` — context on why causal-inference-what-if is the canonical-causal-rigor entry on the statistical-inference shelf. Operator wanted "all three" statistical flavors; this is the rigorous-foundation flavor.
