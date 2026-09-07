---
name: shelves--django
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
| Starting a new Django project, project layout, settings management | [`shelves--two-scoops-django`](../../shelves/django/two-scoops-django/SKILL.md) |
| Django best practices, CBV vs FBV, forms, security checklist | [`shelves--two-scoops-django`](../../shelves/django/two-scoops-django/SKILL.md) |
| Django performance, caching, scaling, load balancing, deployment | [`shelves--high-performance-django`](../../shelves/django/high-performance-django/SKILL.md) |
| High-traffic Django, database optimization, Celery, Redis | [`shelves--high-performance-django`](../../shelves/django/high-performance-django/SKILL.md) |
| Legacy Django code, refactoring Django, design patterns, anti-patterns | [`shelves--django-design-patterns`](../../shelves/django/django-design-patterns/SKILL.md) |
| Inheriting a Django codebase, fat models/views, strangler fig | [`shelves--django-design-patterns`](../../shelves/django/django-design-patterns/SKILL.md) |
| Django REST framework patterns, API design in Django | [`shelves--two-scoops-django`](../../shelves/django/two-scoops-django/SKILL.md) |
| Django GraphQL, Ariadne, schema-first API | [`shelves--two-scoops-django`](../../shelves/django/two-scoops-django/SKILL.md) |
| Django admin customization, user model, AbstractUser | [`shelves--two-scoops-django`](../../shelves/django/two-scoops-django/SKILL.md) |
| Django security checklist, HSTS, CSP, mass assignment | [`shelves--two-scoops-django`](../../shelves/django/two-scoops-django/SKILL.md) |
| Django Celery patterns, task retry, idempotent tasks | [`shelves--django-design-patterns`](../../shelves/django/django-design-patterns/SKILL.md) |
| Django Channels, WebSocket, real-time features | [`shelves--django-design-patterns`](../../shelves/django/django-design-patterns/SKILL.md) |
| Django feature flags, django-waffle, gradual rollout | [`shelves--django-design-patterns`](../../shelves/django/django-design-patterns/SKILL.md) |
| Django deployment checklist, production readiness | [`shelves--high-performance-django`](../../shelves/django/high-performance-django/SKILL.md) |

## Books in this shelf

- [`shelves--two-scoops-django`](../../shelves/django/two-scoops-django/SKILL.md) -- Feldroy. Two Scoops of Django 3.x (5th ed). Best-practices bible covering project layout, settings, models, views, forms, security, testing, deployment. FULL -- all 37 chapters absorbed.
- [`shelves--high-performance-django`](../../shelves/django/high-performance-django/SKILL.md) -- Baumgartner & Malet (Lincoln Loop). High Performance Django. Scaling blueprint: caching tiers, DB optimization, load balancing, deployment automation. Free online. FULL -- all 7 chapters absorbed.
- [`shelves--django-design-patterns`](../../shelves/django/django-design-patterns/SKILL.md) -- Ravindran. Django Design Patterns and Best Practices (2nd ed). Design patterns, anti-patterns, legacy rescue, Celery/Channels async architecture. FULL -- all 13 chapters absorbed.

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

- General Python best practices without Django context -- see [`shelves--languages`](../../shelves/languages/SKILL.md) (Python entries)
- Distributed systems design beyond Django -- see [`shelves--systems-architecture`](../../shelves/systems-architecture/SKILL.md)
- Frontend framework choices (React, Vue, etc.) -- these books focus on Django's server side
- Database design independent of Django ORM -- see [`shelves--data-and-pipelines`](../../shelves/data-and-pipelines/SKILL.md)

## Production case studies (reference context)

These are not books but documented production architectures worth knowing when the shelf's books reference "what large Django sites do":

- **Instagram** -- 30M+ users scaled by 3 engineers on Django. Connection pooling, read replicas, Celery for async work. Documented in Instagram Engineering blog.
- **Disqus** -- one of the highest-traffic Django applications. Documented migration from monolith to service-oriented architecture while keeping Django core.
- **Pinterest** -- early Django, later hybrid architecture. Documents the decision boundary where Django's ORM patterns stop scaling and specialized services take over.

## Source attribution

See individual book entries for per-book attribution and license information.
