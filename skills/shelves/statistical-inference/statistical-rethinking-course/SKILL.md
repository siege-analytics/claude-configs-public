---
name: statistical-rethinking-course
description: 'Bayesian statistical-inference course by Richard McElreath -- DAGs, multilevel models, MCMC, regression-as-thinking. Use when the user mentions "Bayesian inference", "MCMC", "Stan", "PyMC", "brms", "rethinking package", "multilevel models", "hierarchical models", "regression-as-thinking", "Garden of Forking Data", "geocentric models", "elemental confounds", or "Statistical Rethinking". Also trigger when designing a model from scratch with explicit priors, debating frequentist-vs-Bayesian for a specific question, handling missing data / measurement error rigorously, or learning Bayesian thinking from first principles. Course materials (lectures + slides + code) are free; the book itself is paid. Heavier on first-principles Bayesian framing than the other shelf entries; pairs with causal-inference-what-if (compatible identification framework) and think-stats (lighter-weight applied complement).'
license: 'GitHub repo MIT; course materials free; book itself paid'
metadata:
  source: 'github.com/rmcelreath/stat_rethinking_2024 -- 10-week course companion with lecture videos (YouTube), slides PDFs, code in R / Stan / Python / Julia. The Statistical Rethinking textbook (CRC Press) is paid.'
  coverage: 'PARTIAL -- course materials (10 weeks, lecture videos, slides, exercises, code) are free. The book itself is paid and absorption from the book waits for procurement.'
---

# Statistical Rethinking Course Framework

McElreath's Bayesian-statistics course covering the foundations of probabilistic modeling, causal reasoning via DAGs, multilevel / hierarchical models, MCMC inference, and the discipline of regression-as-thinking. The free course materials (lectures + slides + code) ground the framework; the paid book extends with deeper text content (absorb when procured).

## Core Principle

**Statistics is a tool for inferring small worlds from data, but the small world is not the large world.** McElreath's recurring metaphor: every statistical model is a "small world" -- a self-consistent miniature reality where the assumptions hold and the inferences are valid. The "large world" -- the actual data-generating process -- is always more complex. The discipline is naming what your small world assumes, what the large world likely contains beyond it, and being honest about where inferences from the small world are likely to fail in the large.

**The foundation:** Bayesian inference isn't a different statistical paradigm -- it's a more honest one. Every analysis already has priors (the choice of model, of variables to include, of functional form); Bayesianism makes them explicit. Every inference is conditional on assumptions; Bayesianism propagates uncertainty through them. The framework also makes multilevel modeling natural (partial pooling falls out of hierarchical priors) and integrates cleanly with causal DAG reasoning.

## Scoring

**Goal: 10/10.** When evaluating a statistical model built on Bayesian / multilevel foundations, rate 0-10.

- **9-10:** Priors specified and defended; posterior visualized with appropriate uncertainty bands; multilevel structure used where group-level variation exists; DAG drawn to justify variable inclusion; posterior predictive checks performed; "small world vs large world" caveat named.
- **7-8:** Priors set with some justification; posterior visualized; multilevel structure considered (used or explicitly skipped with reason).
- **5-6:** Default priors used without justification; point estimates without uncertainty; multilevel structure ignored where it matters.
- **3-4:** Bayesian framing without Bayesian discipline; MCMC results not visualized; priors are vague defaults with strong influence on conclusions.
- **1-2:** Frequentist test re-labeled "Bayesian"; no priors; no posterior; no honesty about model assumptions.

## The 10-Week Curriculum

The course mirrors the book's structure across 10 weeks.

| Week | Theme | Topics |
|---|---|---|
| 1 | Foundations | Science before statistics; Garden of Forking Data (the binomial mechanism that grounds all of Bayes); chapters 1-3 |
| 2 | Introductory modeling | Geocentric models; categories and curves; chapter 4 |
| 3 | Causal analysis | Elemental confounds (fork / chain / collider); good and bad controls; chapters 5-6 |
| 4 | Overfitting + MCMC | Overfitting; information criteria; MCMC computation; chapters 7-9 |
| 5 | Categorical modeling | Modeling events (binomial); counts and confounds (Poisson); chapters 10-11 |
| 6 | Specialized models | Ordered categories; multilevel models; chapters 11-12 |
| 7 | Hierarchical depth | Multilevel adventures; correlated features; chapter 13 |
| 8 | Advanced | Social networks; Gaussian processes; chapter 14 |
| 9 | Data quality | Measurement; missing data; chapter 15 |
| 10 | Concluding | Generalized linear madness; horoscopes; chapters 16-17 |

## Garden of Forking Data (the central mechanism)

The pedagogical innovation: introduce Bayesian inference NOT via Bayes' theorem but via a concrete counting exercise. Given a small bag with marbles of unknown composition, observed draws update relative plausibility across the possible compositions. The arithmetic IS Bayesian inference. Once the mechanism is internalized concretely, the formalism (priors, likelihoods, posteriors) is just notation for the counting.

## Elemental Confounds (Week 3)

McElreath's framing of DAG vocabulary:

| Pattern | Structure | Treatment |
|---|---|---|
| **The Fork** | Z → X, Z → Y (Z is common cause of X and Y) | Condition on Z to block spurious path. |
| **The Pipe** | X → Z → Y (Z is mediator) | Conditioning on Z blocks the indirect effect; leaves the direct effect. |
| **The Collider** | X → Z ← Y (Z is common effect) | Do NOT condition on Z -- opens spurious path. |
| **The Descendant** | X → Z ← Y, with Z → A (A is descendant of collider) | Conditioning on A also opens the collider; treat as collider. |

"Good and bad controls" -- the framework's treatment of when a variable should / should NOT enter your regression. Adding a "control variable" without checking whether it's a collider is the most common applied-statistics failure.

## Multilevel Models (Weeks 6-7)

When data has hierarchical structure (students in classrooms in schools; observations within subjects over time; counties within states), pooling decisions matter:

- **No pooling:** treat each group separately. High variance estimates for small groups; ignores between-group similarity.
- **Complete pooling:** treat all groups as one. Misses real between-group variation.
- **Partial pooling (multilevel):** estimate group-level parameters with a hyperprior that shrinks small-group estimates toward the population mean. The Bayesian default.

Civic / electoral / longitudinal data is full of hierarchical structure; multilevel models are the appropriate machinery.

## MCMC Computation (Week 4)

Modern Bayesian inference relies on Markov Chain Monte Carlo to approximate posteriors that don't have closed-form solutions. The course covers:

- **Why MCMC:** posteriors for non-conjugate models can't be computed analytically; sample from them instead.
- **Hamiltonian Monte Carlo (HMC):** the modern default. More efficient than Metropolis-Hastings for high-dimensional posteriors.
- **NUTS (No-U-Turn Sampler):** HMC variant that auto-tunes the step size + trajectory length. The default in Stan / PyMC.
- **Diagnostics:** R-hat (chain convergence), ESS (effective sample size), divergence (sampler problems), trace plots.

When NUTS warns of divergences, you have a model-specification problem (often non-identifiable parameters or pathological priors), not a sampler problem.

## Tooling -- Multiple Language Support

The course provides code in:
- **R + `rethinking` package** (McElreath's own; pedagogical wrapper around Stan)
- **R + Tidyverse + `brms`** (more polished applied stack)
- **R + Tidyverse + `ggplot2` + Stan directly**
- **Python + PyMC** (PyMC3 / PyMC v4+)
- **Julia + Turing.jl**

Pick the language stack that matches your existing workflow.

## When this skill does NOT apply

- **Pure frequentist questions** with no Bayesian framing needed -- see think-stats for lighter applied stats.
- **Quasi-experimental designs** (RD / IV / DiD) -- see causal-inference-mixtape, though the DAG framework here transfers.
- **Theoretical causal-inference foundations** -- see causal-inference-what-if (more rigorous identification framework; mostly frequentist but compatible).
- **Pure ML / prediction** -- Bayesian is overkill; standard ML tooling is faster.

## Companions

- `causal-inference-what-if` -- shelf-mate; theoretical causal-inference foundation. DAG framing is compatible across both.
- `causal-inference-mixtape` -- applied causal designs; DAG vocabulary the same.
- `think-stats` -- applied / EDA / simulation-based stats; lighter-weight entry point.

## Source + license + coverage

- **Source:** github.com/rmcelreath/stat_rethinking_2024 -- Richard McElreath, Max Planck Institute for Evolutionary Anthropology.
- **License:** repository MIT-licensed. Lecture videos free on YouTube (2023 playlist; 2024/2022 also available). Slides PDFs free in the repo. Code (R / Python / Julia / Stan) free.
- **Coverage:** PARTIAL. The course materials (lectures + slides + code + exercises) are absorbable from the public materials. The Statistical Rethinking textbook itself (CRC Press, 2nd edition) is paid; that book extends the course with substantially deeper text content. Absorb the book when procured.
- **Verified:** WebFetch 2026-05-17 confirmed the GitHub repo has the 10-week schedule, lecture playlists, slides, multi-language code, and exercises.

## See also

- McElreath's lectures on YouTube (Statistical Rethinking 2023 playlist linked from the repo) -- auto-transcripts plus slides PDFs are the best free study path until the book is procured.
- Session 260502-pure-vista's `plans/shelf-recommendations-for-su-roles.md` -- operator wanted "all three" statistical flavors; this entry covers the Bayesian flavor at course-materials depth, with the book queued for procurement.
