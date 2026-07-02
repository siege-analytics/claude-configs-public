---
name: think-stats
description: 'Computational, Python-first applied statistics for working analysts -- descriptive stats, distributions, hypothesis testing, regression, time series, survival analysis. Use when the user mentions "exploratory data analysis", "EDA", "distributions", "PMF / CDF / PDF", "hypothesis test", "permutation test", "Bayes simple", "regression diagnostics", "time series", "survival analysis", "Allen Downey", or "Think Stats". Also trigger when looking for the right statistical test for a question, doing exploratory analysis on a new dataset, validating assumptions of a regression, or running simulation-based inference. Applied / hands-on / Python-Jupyter; pairs with causal-inference-what-if (when the question becomes causal) and statistical-rethinking-course (Bayesian formalism). Lowest barrier-to-entry entry on the statistical-inference shelf.'
license: 'Creative Commons (non-commercial); ORM print edition paid'
metadata:
  source: 'allendowney.github.io/ThinkStats -- Jupyter notebooks for Think Stats 3e (Allen B. Downey, Olin College). OReilly publishes paid print edition.'
  coverage: 'Full book (14 chapters) freely accessible as runnable Jupyter notebooks. Verified 2026-05-17 via WebFetch.'
---

# Think Stats Framework

A practical, computational approach to applied statistics built for programmers. The book teaches statistical reasoning via short Python programs running on real datasets (NIH, NSFG, BRFSS), with each chapter available as an executable Jupyter notebook combining text + code + exercises.

## Core Principle

**Statistical questions are best learned by running experiments, not memorizing formulas.** Downey's framing: most introductory statistics courses front-load mathematical formalism that obscures the underlying logic. By the time you've worked through what a t-statistic means, you've forgotten what question you were asking. Think Stats inverts this: pose the question, write a short simulation that answers it, then connect the answer to the relevant formal statistic. The computational approach makes the statistic *implementations* (not just the theory) load-bearing for understanding.

**The foundation:** every applied statistical question reduces to: (1) what are you trying to estimate? (2) what's the sampling distribution of that estimate? (3) how would you simulate the null hypothesis? Once the question is in this shape, the formal test follows naturally. The discipline is staying in question-shape, not test-shape.

## Scoring

**Goal: 10/10.** When evaluating an applied statistical analysis, rate 0-10 on rigor + clarity.

- **9-10:** Question stated before method chosen; estimator + sampling distribution explicit; assumptions tested visually (Q-Q plot, residual plot); simulation-based check supplements parametric test; effect size reported (not just p-value); sample size justified.
- **7-8:** Method appropriate; some assumptions checked; effect size present.
- **5-6:** Method-first analysis ("we ran a t-test") without stating the underlying question; only p-value reported.
- **3-4:** Test misapplied (e.g., t-test on highly non-normal data without checking); assumptions unverified; p-hacking risk present.
- **1-2:** "Statistical significance" reported as the conclusion; effect size missing; correlation framed as causation.

## The 14-Chapter Arc

The book builds from EDA → distributions → inference → modeling. Each chapter is an executable notebook.

### Foundations (chapters 1-2)

- **Exploratory data analysis (EDA):** plot first, summarize second. Histograms, scatter plots, distribution shapes.
- **Distributions:** PMF (probability mass function for discrete), CDF (cumulative distribution function), KDE (kernel density estimate for continuous).

**Discipline:** if you can't draw it, you don't understand it. The CDF is the most underrated visualization for comparing distributions.

### Distribution Mechanics (chapters 3-5)

- **PMF, CDF, PDF** in detail with mixture distributions.
- **Modeling continuous distributions** (normal, exponential, log-normal, Pareto, Weibull) and when each is the right model.
- **Skewness, kurtosis, tail behavior.**

**Discipline:** the histogram is a low-resolution visualization. The CDF lets you compare distributions overlaid; the histogram doesn't.

### Relationships and Modeling (chapters 6-7, 11)

- **Probability density, conditional distributions.**
- **Correlation and dependence** (Pearson, Spearman, mutual information).
- **Regression** (simple, multiple, logistic) with diagnostic plots.

**Discipline:** correlation is not causation; residual plots are the test of whether the model fits the data shape.

### Inference Methods (chapters 8-10)

- **Estimation:** sampling distributions, confidence intervals, the bootstrap.
- **Hypothesis testing:** permutation tests as the cleanest formalization. Simulate the null, count how often the observed test statistic appears, that's your p-value.
- **Significance vs effect size:** the discipline of reporting BOTH.

**Discipline:** when in doubt, simulate. A permutation test that you can write in 20 lines of code is more trustworthy than a canned test you can't verify the assumptions of.

### Specialized Applications (chapters 12-14)

- **Time series:** detrending, seasonality, autocorrelation, basic forecasting.
- **Survival analysis:** Kaplan-Meier estimator, hazard functions, censoring.
- **Analytic methods:** when closed-form solutions help (and when simulation is faster).

## The Bootstrap and Permutation Tests

These are the workhorse tools of computational statistics and Think Stats treats them as primary, not as backup methods.

**Bootstrap (for confidence intervals):**
1. Sample with replacement from your data, same size, B times.
2. Compute the estimator on each bootstrap sample.
3. The 2.5th and 97.5th percentiles of the bootstrap distribution are the 95% CI.

**Permutation test (for hypothesis tests):**
1. State the null hypothesis (e.g., "no difference between groups").
2. Pool the data, shuffle the group labels, recompute the test statistic, B times.
3. The fraction of shuffled samples with a test statistic at least as extreme as the observed is the p-value.

These two tools subsume most of an introductory statistics course. When parametric tests apply, they're faster; when assumptions fail, bootstrap / permutation are more honest.

## When this skill does NOT apply

- **Causal inference** -- Think Stats is descriptive / predictive. For causal questions see causal-inference-what-if (theory) or causal-inference-mixtape (applied designs).
- **Bayesian formalism** -- Think Stats touches Bayes lightly (chapter 8); for full Bayesian framing see statistical-rethinking-course or Downey's own *Think Bayes* (different book, same author).
- **Machine learning** -- the book is intentionally statistics-focused, not ML-focused. Regression coverage is the bridge but the book doesn't go into trees / boosting / neural nets.
- **Spatial statistics** -- see spatial-data-science (geospatial shelf).

## Companions

- `causal-inference-what-if` -- when the question becomes causal.
- `causal-inference-mixtape` -- for quasi-experimental designs.
- `statistical-rethinking-course` -- for full Bayesian framing.
- `engineering-principles/` -- the analysis pipeline is code; standard craft applies.

## Source + license

- **Source:** allendowney.github.io/ThinkStats -- *Think Stats: Exploratory Data Analysis in Python* (Allen B. Downey, Olin College of Engineering).
- **License:** Creative Commons (non-commercial). O'Reilly publishes the paid print edition of the 3rd edition.
- **Format:** Jupyter notebooks. Each chapter is an executable notebook with text + code + exercises. Runnable on Google Colab without setup.
- **Verified:** WebFetch 2026-05-17 confirmed the free Jupyter-notebook edition at allendowney.github.io/ThinkStats with 14 chapters spanning EDA through survival analysis.

## See also

- *Think Bayes* (same author, free at greenteapress.com) -- Bayesian counterpart to Think Stats; not absorbed in this shelf because statistical-rethinking-course covers Bayesian more completely.
- Session 260502-pure-vista's `plans/shelf-recommendations-for-su-roles.md` -- context on Think Stats as the applied-statistical-rigor entry. Operator wanted "all three" statistical flavors; this is the practical / EDA / simulation-based flavor.
