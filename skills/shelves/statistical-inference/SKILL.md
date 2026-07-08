---
name: shelves--statistical-inference
description: Router for statistical-inference book skills covering causal inference (theory + applied), Bayesian inference, and applied exploratory / computational statistics. Dispatches to causal-inference-what-if (rigorous causal foundations), causal-inference-mixtape (applied causal designs), statistical-rethinking-course (Bayesian + multilevel), or think-stats (applied EDA + simulation). Read this when the task involves any causal claim from observational data, Bayesian modeling, multilevel structure, hypothesis testing, or "is this analysis methodologically sound." Pairs with spatial-data-science for spatial-statistics edge cases.
---

# Statistical Inference -- Shelf

Books grounding analytical rigor -- the methodologies that make statistical claims defensible and that distinguish prediction from causal inference. Operator's framing: "I wind up doing all three kinds of work" (Bayesian + causal + applied), so this shelf carries all three flavors.

## Trigger table

| Task signal | Book to read |
|---|---|
| Causal inference theory; potential outcomes; g-methods; exchangeability / positivity / consistency; target trial; "is this confounded?" | [`shelves--causal-inference-what-if`](../../shelves/statistical-inference/causal-inference-what-if/SKILL.md) |
| Applied causal designs; regression discontinuity (RD); instrumental variables (IV); difference-in-differences (DiD); synthetic control; natural experiment | [`shelves--causal-inference-mixtape`](../../shelves/statistical-inference/causal-inference-mixtape/SKILL.md) |
| Bayesian inference; multilevel / hierarchical models; MCMC / Stan / PyMC; "what priors should I use"; regression-as-thinking | [`shelves--statistical-rethinking-course`](../../shelves/statistical-inference/statistical-rethinking-course/SKILL.md) |
| Applied EDA; distributions (PMF / CDF / PDF); hypothesis testing; permutation tests / bootstrap; effect sizes; time series; survival analysis | [`shelves--think-stats`](../../shelves/statistical-inference/think-stats/SKILL.md) |

## Books in this shelf

- [`shelves--causal-inference-what-if`](../../shelves/statistical-inference/causal-inference-what-if/SKILL.md) -- Hernán & Robins. *Causal Inference: What If*. Theoretical foundation of modern causal inference; potential outcomes + g-methods for time-varying confounding. Free PDF at miguelhernan.org/whatifbook.
- [`shelves--causal-inference-mixtape`](../../shelves/statistical-inference/causal-inference-mixtape/SKILL.md) -- Cunningham. *Causal Inference: The Mixtape*. Applied identification strategies (DAGs, RD, IV, DiD, synthetic control). Full free online at mixtape.scunning.com.
- [`shelves--statistical-rethinking-course`](../../shelves/statistical-inference/statistical-rethinking-course/SKILL.md) -- McElreath. Bayesian course companion (lectures + slides + multi-language code). Free at github.com/rmcelreath/stat_rethinking_2024; book itself paid.
- [`shelves--think-stats`](../../shelves/statistical-inference/think-stats/SKILL.md) -- Downey. *Think Stats 3e*. Computational / Python-first applied statistics. Free Jupyter notebooks at allendowney.github.io/ThinkStats.

## Disambiguation

- **what-if vs mixtape:** What If is the theoretical foundation (assumptions, identification, g-methods). Mixtape is the applied designs you'd actually run on real data (RD, IV, DiD). Load What If when reasoning about whether a study CAN identify causality; load Mixtape when picking which natural-experiment design fits your data structure. They compose: load both for serious causal work.
- **what-if + mixtape vs statistical-rethinking-course:** What If / Mixtape are largely frequentist-oriented though the framework is paradigm-agnostic. Rethinking is Bayesian-first and integrates DAG-based causal reasoning with priors + multilevel models. Use Rethinking when the analysis benefits from explicit uncertainty propagation, hierarchical structure, or small-sample regularization.
- **anything-causal vs think-stats:** Think Stats is the applied / EDA / prediction baseline. Use it when the question is "what's in this data?" or "what predicts what?" -- NOT when the question is causal. For causal questions, escalate to What If / Mixtape.
- **think-stats vs statistical-rethinking-course on Bayesian:** Think Stats touches Bayes briefly (chapter 8). Rethinking IS Bayesian from chapter 1. For full Bayesian framing use Rethinking; for quick applied Bayesian see Downey's separate *Think Bayes* (not in this shelf).

## When to use this shelf

- Estimating a causal effect from observational data.
- Designing a quasi-experimental study (RD / IV / DiD).
- Building a multilevel / hierarchical model.
- Justifying a prior in a Bayesian analysis.
- Reasoning about whether to "control for" a variable in a regression.
- Picking the right hypothesis test for a question.

## When NOT to use this shelf

- **Pure ML / prediction** -- overkill; standard ML tooling is appropriate.
- **Visualization craft** -- see `storytelling/storytelling-with-data`.
- **Pure descriptive reporting** -- Think Stats's EDA chapters are the lightest entry.
- **Spatial autocorrelation specifically** -- see `geospatial/spatial-data-science` which handles spatial regression / kriging / etc. Compose with this shelf as needed.

## Always-on companions

- `_writing-claims-rules.md` -- claim-grounding discipline applies doubly to statistical claims (countable claims need grounded grep; unquantified completeness claims need grounded checks).
- `_data-trust-rules.md` -- statistical analysis on untrusted data is doubly broken.

## Coverage state and procurement queue

| Book | Coverage state |
|---|---|
| causal-inference-what-if | FULL -- free PDF freely maintained by authors |
| causal-inference-mixtape | FULL -- free online edition |
| statistical-rethinking-course | PARTIAL -- course materials free; textbook paid (procurement pending) |
| think-stats | FULL -- free Jupyter notebooks |

When operator procures the Statistical Rethinking book, expand the statistical-rethinking-course entry into a fuller statistical-rethinking-book entry. Other procurement targets (Gelman/Hill/Vehtari *Regression and Other Stories*, Angrist & Pischke *Mostly Harmless Econometrics*) overlap with the existing entries and can be added later if they fill gaps the operator identifies.

## Origin

Statistical-inference gap surfaced in the shelf-coverage joint design (sessions 260502-pure-vista + 260502-vital-channel, 2026-05-17). Operator wanted "all three" kinds of statistical work covered (Bayesian + causal + applied), which translated to four entries on this shelf rather than one. The doc's original priority list included Gelman/Hill/Vehtari + Angrist & Pischke + McElreath as the "stretch" entries; URL verification surfaced the free Hernán & Robins + Cunningham + Downey alternatives that cover the same gaps for free.
