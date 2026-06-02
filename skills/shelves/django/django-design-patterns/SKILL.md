---
name: django-design-patterns
description: 'Django design patterns, anti-patterns, and legacy code rescue. Use when the user mentions "Django design patterns", "Django anti-patterns", "Django legacy code", "Django refactoring", "Django code smells", "Django migration from legacy", "strangler fig Django", "Django test harness", "fat models", "fat views", "Django monolith", "dealing with legacy Django", "Django technical debt", or "Django code rescue". Also trigger when inheriting a Django codebase, refactoring a Django monolith, diagnosing structural problems in Django projects, or deciding how to incrementally modernize a Django application. For performance see high-performance-django; for greenfield best practices see two-scoops-django.'
license: 'Paid book (Packt Publishing)'
metadata:
  source: 'Arun Ravindran -- Django Design Patterns and Best Practices (2nd edition, Packt 2018). Covers Django 2.x; structural patterns and rescue methodology remain relevant across Django versions.'
  coverage: 'PARTIAL -- public table of contents, Chapter 10 ("Dealing with Legacy Code") documented from reviews and community summaries, general pattern catalog from public descriptions. Full book not yet procured. Verified 2026-06-02 via WebSearch.'
---

# Django Design Patterns and Legacy Rescue Framework

A pattern catalog and rescue methodology for Django applications. Apply
when inheriting a Django codebase, diagnosing structural problems in an
existing Django project, or deciding how to incrementally refactor a
Django monolith toward best practices.

**Coverage caveat:** this entry is PARTIAL. The pattern descriptions are
drawn from publicly available chapter listings, reviews, and community
discussions. Chapter 10's legacy rescue methodology is documented from
multiple review sources. Nuanced code examples and detailed pattern
implementations require the full book. Procure and re-absorb for FULL
coverage.

## Core Principle

**Every Django codebase encodes design decisions, whether the developers
made them consciously or not.** Recognizing the patterns (and anti-patterns)
already present in a codebase is the prerequisite to improving it. You
cannot refactor what you cannot name. This book provides the vocabulary
for naming what you see and the methodology for changing it incrementally.

## Scoring

**Goal: 10/10.** When evaluating a Django codebase's structural health or
a refactoring plan, rate 0-10 on pattern recognition and rescue discipline.

- **9-10:** Patterns are named and intentional. Anti-patterns are identified
  and tracked for remediation. Refactoring is incremental with test coverage
  at each step. Legacy code has characterization tests before changes.
- **7-8:** Most patterns are recognizable. Some anti-patterns identified but
  not yet addressed. Refactoring underway with partial test coverage.
- **5-6:** Mixed patterns -- some intentional, some accidental. Anti-patterns
  present but undiagnosed. Refactoring attempted without test safety net.
- **3-4:** No pattern awareness. Fat views with 500+ lines. Business logic
  in templates. No refactoring plan. Changes made ad hoc.
- **1-2:** Codebase is a collection of workarounds with no discernible
  structure. No tests. Changes are high-risk.

## 1. Pattern Catalog -- Django-Specific Patterns

**Core concept:** Django's MTV (Model-Template-View) architecture has its
own pattern vocabulary distinct from generic GoF patterns.

**Key patterns (from public chapter listings):**

- **Service layer:** extract business logic from views into service
  modules. Views become thin dispatchers; services are testable without
  HTTP.
- **QuerySet chaining:** custom managers and querysets that compose.
  `Article.objects.published().featured()` instead of raw filter chains
  repeated across views.
- **Mixin composition for CBVs:** small, focused mixins that compose
  rather than deep inheritance hierarchies.
- **Signal decoupling:** Django signals for cross-cutting concerns
  (audit logging, cache invalidation) where direct calls would create
  circular dependencies. Overuse is an anti-pattern.
- **Template tag encapsulation:** complex presentation logic in custom
  template tags rather than in templates or views.

## 2. Anti-Pattern Recognition

**Core concept:** knowing what NOT to do is as valuable as knowing what
to do. Django anti-patterns have characteristic shapes.

**Common Django anti-patterns:**

- **Fat views:** views with 200+ lines handling validation, business
  logic, formatting, and response construction. Fix: extract to forms,
  services, and serializers.
- **Fat templates:** templates containing business logic (`{% if %}` trees
  that make decisions). Fix: move logic to view or template tags.
- **Anemic models:** models that are just field declarations with no
  methods. All logic lives in views. Fix: move domain behavior to models.
- **God model:** one model that does everything. 50+ fields, dozens of
  methods. Fix: decompose into related models with clear boundaries.
- **Copy-paste views:** multiple views with near-identical logic differing
  in small ways. Fix: CBV with mixins, or shared service functions.
- **Hardcoded queries:** raw SQL or complex ORM queries duplicated across
  the codebase. Fix: custom managers and querysets.
- **Settings spaghetti:** `if DEBUG` / `if ENVIRONMENT == 'production'`
  scattered through application code. Fix: proper settings split and
  configuration injection.

## 3. Chapter 10 -- Dealing with Legacy Code

**Core concept:** legacy Django code requires a specific rescue
methodology. You cannot rewrite safely; you must refactor incrementally.

**The rescue methodology (from reviews and community documentation):**

### Step 1: Understand before changing

- Read the code with the goal of understanding what it does, not how
  to fix it. Map the actual data flow, not the intended data flow.
- Identify the "load-bearing" code -- the parts that, if broken, bring
  down the application. These get characterization tests first.

### Step 2: Add characterization tests

- Before changing ANY legacy code, write tests that capture its current
  behavior -- even if that behavior is wrong.
- Use Django's test client to write integration tests against views.
  These are coarse but fast to write and catch regressions.
- Use `factory_boy` to create test data instead of fixtures. Fixtures
  rot; factories evolve with the schema.

### Step 3: Identify seams

- A "seam" is a place where you can change behavior without changing
  the code around it. In Django: URL routing, middleware, view
  dispatch, signal handlers.
- The strangler fig pattern: wrap legacy views with new implementations.
  Route traffic incrementally (by URL, by feature flag, by percentage).
  Retire old code when new path is proven.

### Step 4: Refactor incrementally

- One pattern at a time. Extract a service layer from the fattest view.
  Add a custom manager to the most-queried model. Split the god model.
- Each refactoring step must: (a) have test coverage before starting,
  (b) not change behavior, (c) be deployable independently.

### Step 5: Modernize settings and configuration

- Most legacy Django projects have a single `settings.py` with
  hardcoded values, debug toggles, and production secrets.
- Split into base/local/production/test. Extract secrets to environment
  variables. This is usually safe to do early because it does not change
  application behavior.

## 4. Domain-Driven Design Applied to Django

**Core concept:** DDD provides a vocabulary for decomposing a Django
monolith into bounded contexts.

**Key application patterns:**

- Identify bounded contexts in the monolith. Each context becomes a
  Django app (or a cluster of apps) with explicit interfaces.
- The Django app boundary IS the bounded context boundary. If two apps
  need to share models, they are either one context or they need an
  explicit interface (API, event, shared abstraction).
- Aggregate roots map to Django models with custom managers that enforce
  invariants.

## 5. Incremental Modernization Strategy

**Core concept:** a legacy Django codebase cannot be rewritten in one pass.
The strategy is progressive improvement with continuous deployment.

**Key principles:**

- **Test harness first.** No refactoring without tests. The first week of
  rescue work produces tests, not features and not refactoring.
- **Strangler fig, not big bang.** New code wraps old code. Old code is
  retired when the new path is proven. Never "rewrite weekend."
- **Track technical debt explicitly.** Every anti-pattern identified gets
  a ticket. Tickets get prioritized alongside features. Debt is work,
  not background noise.
- **Celebrate incremental wins.** A 500-line view reduced to 200 lines
  with a service layer is progress worth deploying and measuring.

## When this skill does NOT apply

- Greenfield Django projects following best practices from the start --
  see [skill:two-scoops-django]
- Performance optimization of structurally sound code -- see
  [skill:high-performance-django] (fix correctness before speed)
- General refactoring patterns outside Django -- see
  [skill:refactoring-patterns] or [skill:clean-code]
- Non-Django legacy codebases -- the Django-specific patterns (MTV,
  ORM managers, URL routing as seams) are central to this framework

## Companions

- [skill:two-scoops-django] -- the target state. Refactoring legacy code
  means moving it toward Two Scoops conventions.
- [skill:high-performance-django] -- after structural rescue, optimize
  for performance
- [skill:clean-code] -- general code quality principles
- [skill:refactoring-patterns] -- broader refactoring catalog beyond
  Django-specific patterns

## Source and license

- **Title:** Django Design Patterns and Best Practices
- **Author:** Arun Ravindran
- **Publisher:** Packt Publishing
- **Edition:** 2nd (2018, covers Django 2.x)
- **License:** Paid. No free edition available.
- **Coverage:** PARTIAL -- public chapter listings, Chapter 10 legacy
  rescue methodology from reviews, general pattern catalog. Full book
  not yet procured.
- **Verified:** 2026-06-02 via WebSearch (confirmed 2nd edition is
  latest; no 3rd edition covering Django 4/5 published)
