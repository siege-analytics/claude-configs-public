---
name: shelf-django
description: 'Router for Django book skills. Dispatches to two-scoops-django, high-performance-django, or django-design-patterns based on task signals. Read this when building Django applications, scaling Django for production traffic, refactoring legacy Django codebases, or applying Django best practices to project layout, settings, models, views, and deployment.'
---

# Django -- Shelf

Books for building, scaling, and rescuing Django applications. Covers
three concerns: best-practices discipline (project structure, security,
testing), high-traffic production architecture (caching, DB optimization,
horizontal scaling), and legacy codebase rescue (pattern recognition,
incremental refactoring, test harness bootstrapping).

## Trigger table

| Task signal | Book to read |
|---|---|
| Starting a new Django project, project layout, settings management | [skill:two-scoops-django] |
| Django best practices, CBV vs FBV, forms, security checklist | [skill:two-scoops-django] |
| Django performance, caching, scaling, load balancing, deployment | [skill:high-performance-django] |
| High-traffic Django, database optimization, Celery, Redis | [skill:high-performance-django] |
| Legacy Django code, refactoring Django, design patterns, anti-patterns | [skill:django-design-patterns] |
| Inheriting a Django codebase, fat models/views, strangler fig | [skill:django-design-patterns] |
| Django REST framework patterns, API design in Django | [skill:two-scoops-django] |
| Django deployment checklist, production readiness | [skill:high-performance-django] |

## Books in this shelf

- [skill:two-scoops-django] -- Feldroy. Two Scoops of Django 3.x (5th ed). Best-practices bible covering project layout, settings, models, views, forms, security, testing, deployment. PARTIAL -- not yet procured.
- [skill:high-performance-django] -- Baumgartner & Malet (Lincoln Loop). High Performance Django. Scaling blueprint: caching tiers, DB optimization, load balancing, deployment automation. Free online. PARTIAL.
- [skill:django-design-patterns] -- Ravindran. Django Design Patterns and Best Practices (2nd ed). Design patterns, anti-patterns, and Chapter 10 on legacy code rescue. PARTIAL -- not yet procured.

## Disambiguation

- **two-scoops-django vs high-performance-django:** Two Scoops is about writing correct Django code (the right patterns at every layer). HPD is about making correct code fast at scale (infrastructure, caching, deployment). Two Scoops answers "how should I structure this?"; HPD answers "how do I serve this to 10M users?"
- **two-scoops-django vs django-design-patterns:** Two Scoops is prescriptive best practices for greenfield work. Django Design Patterns includes rescue patterns for codebases that did not follow best practices -- how to recognize structural problems and refactor incrementally.
- **high-performance-django vs django-design-patterns:** HPD optimizes working code for throughput. Django Design Patterns fixes broken code for correctness. If the codebase is structurally sound but slow, start with HPD. If it is structurally broken, start with Django Design Patterns.

## When to use this shelf

- Building a new Django application of any size
- Scaling an existing Django application for higher traffic
- Inheriting or rescuing a legacy Django codebase
- Reviewing Django code for quality, security, or performance
- Making architectural decisions in Django (monolith vs services, sync vs async, ORM patterns)

## When NOT to use this shelf

- General Python best practices without Django context -- see [skill:shelf-languages] (Python entries)
- Distributed systems design beyond Django -- see [skill:shelf-systems-architecture]
- Frontend framework choices (React, Vue, etc.) -- these books focus on Django's server side
- Database design independent of Django ORM -- see [skill:shelf-data-and-pipelines]

## Production case studies (reference context)

These are not books but documented production architectures worth knowing when the shelf's books reference "what large Django sites do":

- **Instagram** -- 30M+ users scaled by 3 engineers on Django. Connection pooling, read replicas, Celery for async work. Documented in Instagram Engineering blog.
- **Disqus** -- one of the highest-traffic Django applications. Documented migration from monolith to service-oriented architecture while keeping Django core.
- **Pinterest** -- early Django, later hybrid architecture. Documents the decision boundary where Django's ORM patterns stop scaling and specialized services take over.

## Source attribution

See individual book entries for per-book attribution and license information.
