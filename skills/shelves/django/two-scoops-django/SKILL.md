---
name: two-scoops-django
description: 'Django best practices across project layout, settings, models, forms, views, templates, security, testing, and deployment. Use when the user mentions "Django best practices", "Django project structure", "Django settings", "cookiecutter-django", "class-based views", "function-based views", "CBV vs FBV", "Django forms", "Django security checklist", "Django testing patterns", "Django REST framework patterns", "Django deployment", or "Django anti-patterns". Also trigger when starting a new Django project, reviewing Django code for quality, or choosing between Django approaches. For scaling/performance see high-performance-django; for legacy rescue see django-design-patterns.'
license: 'Paid book (Feldroy self-published). No free edition.'
metadata:
  source: 'feldroy.com -- Two Scoops of Django 3.x (5th edition, Daniel and Audrey Feldroy, formerly Greenfeld). Covers Django 3.x; no Django 5 update published as of 2026-06-02.'
  coverage: 'PARTIAL -- public chapter listings, community-documented patterns, and widely-cited recommendations. Full book not yet procured. Verified 2026-06-02 via WebSearch.'
---

# Two Scoops of Django Framework

The community-standard best-practices reference for Django development.
Apply when starting a new Django project, reviewing existing Django code
for quality, or choosing between competing Django approaches at any layer
(models, views, forms, templates, settings, testing, deployment).

**Coverage caveat:** this entry is PARTIAL. It distills the publicly known
chapter structure, widely-cited recommendations, and community-documented
patterns. Nuanced arguments, code examples, and edge-case guidance require
the full book. Procure and re-absorb for FULL coverage.

## Core Principle

**Every Django decision has a best practice; know it before you deviate.**
The Feldroy approach is prescriptive: for each layer of a Django project
(settings, models, views, forms, templates, REST APIs, security, testing,
deployment), there is a recommended pattern backed by years of consulting
experience. Deviation is fine when justified -- but you must know the
standard you are deviating from, and you must know why.

## Scoring

**Goal: 10/10.** When evaluating Django code against Two Scoops practices,
rate 0-10 on adherence to the layered best practices below.

- **9-10:** Project layout follows cookiecutter-django conventions. Settings
  split correctly. Models are fat with managers and querysets. Views are thin.
  Forms handle validation. Security checklist passes. Tests are comprehensive.
- **7-8:** Most conventions followed, minor deviations justified. Settings
  mostly split. Model layer reasonable. Some views doing too much.
- **5-6:** Mixed adherence. Settings in one file. Some logic in views that
  belongs in models. Security basics present but checklist incomplete.
- **3-4:** Significant deviations. Business logic scattered across views
  and templates. No settings split. Minimal testing.
- **1-2:** No evidence of best-practice awareness. Single settings file with
  secrets. Logic in templates. No tests. Security holes.

## 1. Project Layout and Settings

**Core concept:** a Django project's directory structure and settings
management determine how maintainable it will be at scale.

**Key practices (widely cited):**

- Use cookiecutter-django or a similar opinionated template for new projects.
  The default `django-admin startproject` layout is a starting point, not a
  production layout.
- Split settings into multiple files: `base.py`, `local.py`, `production.py`,
  `test.py`. Never put secrets in settings files checked into version control.
- Use environment variables (via `django-environ` or `os.environ`) for
  secrets and environment-specific configuration.
- Keep the root `urls.py` thin -- delegate to app-level `urls.py` files.
- One app per concern. Apps should be reusable and loosely coupled.

**Anti-patterns:**
- Single `settings.py` with `if DEBUG` blocks
- Secrets committed to version control
- Monolithic apps that mix unrelated models

## 2. Models -- Fat Models, Thin Views

**Core concept:** business logic belongs in the model layer, not in views
or templates. Models should be "fat" -- carrying methods, managers, and
custom querysets that encapsulate domain behavior.

**Key practices:**

- Use model managers and custom querysets for complex queries. Chain
  querysets rather than writing raw SQL in views.
- Use `select_related()` and `prefetch_related()` to avoid N+1 query
  problems. Know which one to use (foreign keys vs reverse/M2M relations).
- Keep models focused. When a model grows beyond ~500 lines, consider
  whether it should be split.
- Use model validation (`clean()`, validators) rather than form-only
  validation for constraints that must always hold.

**Anti-patterns:**
- Business logic in views ("fat views")
- Raw SQL scattered across view functions
- Models with no custom methods (anemic models)

## 3. Views -- Class-Based vs Function-Based

**Core concept:** choose the view type that fits the pattern.

**Key practices:**

- Function-based views (FBVs) for simple, one-off logic.
- Class-based views (CBVs) when the view fits a standard pattern (list,
  detail, create, update, delete) and benefits from inheritance/mixins.
- Do not use CBVs just because they exist. If you are overriding every
  method, an FBV would be clearer.
- Keep views thin: validate input, call model/service methods, return
  response.
- Use `django.views.decorators` and CBV mixins for cross-cutting concerns
  (login_required, permission checks).

**Anti-patterns:**
- Views with 200+ lines of business logic
- Deep CBV inheritance hierarchies that are hard to trace
- Mixing presentation logic with business logic in views

## 4. Forms and Validation

**Core concept:** forms are Django's data-validation layer for user input.

**Key practices:**

- Use Django forms for ALL user input, even for API endpoints (or use
  serializers in DRF).
- ModelForms for standard CRUD. Regular Forms for non-model input.
- Put validation logic in form `clean()` and `clean_<field>()` methods,
  not in the view.
- Use formsets for collections of related forms.

## 5. Security

**Core concept:** Django provides strong security defaults, but you must
enable and maintain them.

**Key practices (the checklist):**

- Keep `DEBUG = False` in production. Always.
- Set `ALLOWED_HOSTS` explicitly.
- Use HTTPS everywhere. Set `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
  `CSRF_COOKIE_SECURE`.
- Keep `SECRET_KEY` out of version control.
- Run `python manage.py check --deploy` before every deployment.
- Use Django's CSRF protection. Do not disable it.
- Escape user input in templates (Django auto-escapes, but `mark_safe` and
  `|safe` bypass this -- use them only when you control the content).
- Use parameterized queries (Django ORM does this; raw SQL must use params).

## 6. Testing

**Core concept:** test the contracts, not the implementation.

**Key practices:**

- Use `pytest-django` or Django's built-in test framework.
- Test models (business logic), views (HTTP contracts), and forms
  (validation rules) as separate layers.
- Use factories (`factory_boy`) instead of fixtures for test data.
- Integration tests for critical paths. Unit tests for model logic.
- Test that security constraints hold (authentication required, permissions
  enforced).

## 7. Django REST Framework Patterns

**Core concept:** DRF is the standard for Django APIs. Apply the same
layered discipline.

**Key practices:**

- Serializers handle validation (like forms for APIs).
- ViewSets for standard CRUD; APIView for custom endpoints.
- Use permissions classes, not ad-hoc checks in views.
- Version your API from day one.
- Use pagination for list endpoints. Always.

## When this skill does NOT apply

- Pure performance optimization (caching, scaling) -- see
  [skill:high-performance-django]
- Rescuing a legacy codebase that did not follow any of these practices --
  see [skill:django-design-patterns] for the rescue methodology
- Non-Django Python projects -- see [skill:shelf-languages]
- Frontend framework decisions -- Two Scoops focuses on server-side Django

## Companions

- [skill:high-performance-django] -- after building correctly, scale it
- [skill:django-design-patterns] -- legacy rescue when best practices
  were not followed
- [skill:clean-code] -- general code quality principles that complement
  Django-specific practices
- [skill:pragmatic-programmer] -- broader engineering discipline

## Source and license

- **Title:** Two Scoops of Django 3.x
- **Authors:** Daniel Feldroy, Audrey Feldroy
- **Publisher:** Feldroy (self-published)
- **Edition:** 5th (covers Django 3.x)
- **License:** Paid. No free edition available.
- **URL:** feldroy.com
- **Coverage:** PARTIAL -- public chapter structure and widely-cited
  recommendations. Full book not yet procured.
- **Verified:** 2026-06-02 via WebSearch (confirmed no Django 5 edition
  exists; 5th edition covering Django 3.x is the latest)
