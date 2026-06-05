---
name: two-scoops-django
description: 'Django best practices across all layers: project layout, settings, models, queries, views, forms, templates, APIs, security, testing, performance, and deployment. Use when the user mentions "Django best practices", "Django project structure", "Django settings", "cookiecutter-django", "class-based views", "function-based views", "CBV vs FBV", "Django forms", "Django form patterns", "Django security checklist", "Django testing patterns", "Django REST framework", "DRF", "Django deployment", "Django anti-patterns", "Django model design", "fat models", "Django template architecture", "Django GraphQL", "Django async views", "Django admin customization", "Django user model", "AbstractUser", "Django logging", "Django task queues", "Django caching", "django-debug-toolbar", "Django performance", "ATOMIC_REQUESTS", "Django CSRF", "Django Content Security Policy", "Django HSTS", "ModelSerializer", "Django coverage", or "factory_boy". Also trigger when starting a new Django project, reviewing Django code for quality, choosing between Django approaches, designing Django models, implementing Django forms, setting up Django REST APIs, hardening Django security, or writing Django tests. For scaling/performance infrastructure see high-performance-django; for legacy rescue see django-design-patterns.'
license: 'Paid book (Feldroy self-published). No free edition.'
metadata:
  source: 'feldroy.com -- Two Scoops of Django 3.x (5th edition, Daniel and Audrey Feldroy, formerly Greenfeld). Covers Django 3.x; no Django 5 update published as of 2026-06-02.'
  coverage: 'FULL -- all 37 chapters + appendices absorbed from procured PDF on 2026-06-02. Chapters 30-36 are stubs in the book ("Chapter in Progress"); content from Chapters 1-29, 37, and Appendix A is complete.'
---

# Two Scoops of Django Framework

The community-standard best-practices reference for Django development.
Apply when starting a new Django project, reviewing existing Django code
for quality, choosing between competing Django approaches at any layer
(models, views, forms, templates, settings, testing, security, APIs,
deployment), or auditing a Django codebase against established conventions.

**Edition note:** covers Django 3.x. Core patterns (settings split, fat
models, CBV discipline, security checklist) are version-stable. Async
views (Ch11) were new in Django 3.1. No Django 5 edition exists;
supplement with current Django release notes for post-3.x features
(async ORM operations, LoginRequiredMixin default, etc.).

## Core Principle

**Every Django decision has a best practice; know it before you deviate.**
The Feldroy approach is prescriptive: for each layer of a Django project
(settings, models, views, forms, templates, REST APIs, security, testing,
deployment), there is a recommended pattern backed by years of consulting
experience across dozens of projects. Deviation is fine when justified --
but you must know the standard you are deviating from, and you must know
why.

The book's through-line is defense in depth: settings protect secrets,
forms validate input, security middleware hardens transport, tests verify
contracts, and deployment automation prevents human error. Each layer
reinforces the others.

## Scoring

**Goal: 10/10.** When evaluating Django code against Two Scoops practices,
rate 0-10 on adherence to the layered best practices below.

- **9-10:** Project layout follows three-tier cookiecutter-django
  conventions. Settings split into base/local/staging/production/test with
  env vars for secrets. Models are fat with managers, custom querysets,
  and behavior mixins. Views are thin (FBV or CBV chosen by pattern).
  Forms handle all validation with standard patterns. Templates use
  2/3-tier inheritance. DRF APIs versioned with proper permissions.
  Security checklist (30+ items) passes. Tests are comprehensive with
  factory_boy and coverage game enforced. Logging structured with one
  logger per module.
- **7-8:** Most conventions followed. Settings mostly split. Model layer
  reasonable but some logic in views. CBVs used but mixin discipline
  loose. Security basics present but checklist not fully verified.
- **5-6:** Mixed adherence. Settings in one file with some env vars.
  Business logic split inconsistently between models and views. Templates
  contain logic. Testing present but coverage gaps. Security checklist
  not run.
- **3-4:** Significant deviations. Business logic scattered across views
  and templates. Single settings file with secrets. Minimal testing. No
  API versioning.
- **1-2:** No evidence of best-practice awareness. Single settings file
  with hardcoded SECRET_KEY. Logic in templates. No tests. Security holes.
  DEBUG=True in production.

## 1. Foundation -- Coding Style, Environment, Layout, Apps, Settings

**Core concept:** the decisions made before writing the first view --
coding style, environment parity, project layout, app boundaries, and
settings management -- determine maintainability at scale.

### Coding style (Ch1)

- Follow PEP 8 with Django conventions. Use `flake8` or `black`.
- Import order: stdlib, Django, third-party, local. Use `isort`.
- Explicit relative imports within apps (`from .models import`), absolute
  imports between apps (`from profiles.models import`).

### Environment (Ch2)

- **Same database engine everywhere.** PostgreSQL in production means
  PostgreSQL in development. SQLite in dev hides bugs that surface in
  production (different type coercion, missing features, locking).
- pip + virtualenv (or pipenv/poetry). Pin all dependencies. Use
  `requirements/` directory: `base.txt`, `local.txt`, `production.txt`,
  `test.txt`.
- Docker is acceptable but not required -- the principle is parity.

### Project layout (Ch3)

Three-tier layout (repository root, project root, configuration root):

```
<repository_root>/
  <project_root>/
    <configuration_root>/  # settings/, urls.py, wsgi.py
    <app1>/
    <app2>/
  manage.py
  requirements/
  docs/
```

Use `cookiecutter-django` for new projects. The default
`django-admin startproject` is a starting point, not a production layout.

### App design (Ch4)

- Each app does one thing. "Can you describe the app in one sentence
  without using 'and'?"
- Name apps as plural nouns: `flavors`, `animals`, `profiles`.
- Apps should be loosely coupled. If you cannot explain what the app does
  without referencing another app, they may need merging or an explicit
  interface.

### Settings (Ch5)

- Split into `settings/base.py`, `settings/local.py`,
  `settings/staging.py`, `settings/production.py`, `settings/test.py`.
- Never put secrets in settings files or version control.
- Use environment variables (via `django-environ` or `os.environ`).
  django-environ provides typed getters that avoid type conversion issues.
- `DJANGO_SETTINGS_MODULE` selects the active settings file.
- Keep `SECRET_KEY` out of VCS. Generate with
  `secrets.token_urlsafe(50)`.

**Anti-patterns:**
- Single `settings.py` with `if DEBUG` blocks
- Secrets committed to version control
- SQLite in development when PostgreSQL is in production
- Monolithic apps that mix unrelated models

## 2. The Model Layer -- Design, Queries, Transactions

**Core concept:** business logic belongs in the model layer. Models
should be "fat" -- carrying methods, managers, custom querysets, and
behavior mixins that encapsulate domain behavior. The database is the
foundation; get it right.

### Model design (Ch6)

**Inheritance hierarchy:**

| Strategy | Table structure | Use when |
|---|---|---|
| Abstract base class | No table for parent | Sharing fields/methods across models |
| Multi-table inheritance | Separate tables, implicit JOIN | Need independent querysets on both |
| Proxy model | Same table, different Python | Different behavior on same data |

- **Abstract base classes** (`abstract = True`): share fields and methods
  without extra tables. The TimeStampedModel pattern (abstract base with
  `created` and `modified` auto-fields) should underpin every model.
- **Multi-table inheritance:** performance penalty on every query (implicit
  JOIN). Avoid unless you genuinely need independent querysets on both
  parent and child.
- **Proxy models:** different Python behavior on the same table. Use for
  alternative managers, different default ordering, different methods.

**null vs blank guide:**
- `CharField`/`TextField`: never `null=True`. Use `blank=True, default=""`.
  Two possible empty values (NULL and "") creates ambiguity.
- `FileField`/`ImageField`: same rule -- `blank=True`, never `null=True`.
- `BooleanField`: prefer `BooleanField(default=False)`. Use
  `NullBooleanField` only for genuine three-state (yes/no/unknown).
- Numeric fields: `null=True, blank=True` when "not applicable" differs
  from zero.
- ForeignKey/M2M: `null=True, blank=True` when the relationship is
  optional.

**TextChoices/IntegerChoices:** use for enumerated fields instead of
ad-hoc strings or magic numbers. Define on the model class.

**Fat models with behavior mixins:** when a model grows large, extract
behavior into mixin classes. Each mixin adds one coherent behavior
(Publishable, Sluggable, SoftDeletable). The model class becomes a
composition of mixins + field declarations.

### Queries and database (Ch7)

- **`get_object_or_404()`:** use in views only. It raises Http404 --
  a view-layer concern. In model/service code, use `.get()` and handle
  `DoesNotExist` explicitly.
- **F() expressions:** avoid race conditions in updates.
  `Entry.objects.filter(pk=pk).update(num_views=F('num_views') + 1)` is
  atomic; `entry.num_views += 1; entry.save()` is not.
- **Database functions:** use `Length`, `Lower`, `Coalesce`, `Greatest`,
  etc. for database-side computation. Avoids pulling data into Python.
- **Raw SQL as last resort:** `.raw()` and `cursor.execute()` bypass
  ORM protections. Always use parameterized queries. Document why the
  ORM was insufficient.
- **Indexes:** add `db_index=True` or `Meta.indexes` for fields used
  in `filter()`, `exclude()`, `order_by()`. Target: 10-25% of queries
  should benefit from custom indexes beyond Django's automatic ones.
- **ATOMIC_REQUESTS:** set `True` in DATABASES config. Wraps every view
  in a transaction. Override with `@transaction.non_atomic_requests` for
  views that should not be transactional. Separate from
  `@transaction.atomic()` which wraps specific blocks.

**Anti-patterns:**
- Anemic models (field declarations with no methods)
- Business logic in views instead of models/managers
- Raw SQL without parameterization
- Missing indexes on frequently-filtered fields

## 3. The View Layer -- FBVs, CBVs, Async Views

**Core concept:** choose the view type that fits the pattern. Neither
FBVs nor CBVs are universally superior. The decision depends on the
use case.

### When to use which (Ch8-9)

**FBVs when:** custom HTTP method handling that does not fit standard
CRUD; one-off views; the view is simpler as a decorated function than
a class with overrides. Use `functools.wraps` on decorators to preserve
function metadata.

**CBVs when:** the view follows a standard CRUD pattern (list, detail,
create, update, delete); you benefit from mixin composition; you need
the same pattern across multiple models.

### URL design (Ch8)

- Use URL namespaces: `app_name = 'flavors'` in app `urls.py`, reference
  as `{% url 'flavors:detail' flavor.pk %}`.
- Keep `urls.py` thin. No logic in URL patterns.
- Loose coupling: views should not know their own URL. Use `reverse()`.

### CBV discipline (Ch10)

**Mixin MRO -- three rules:**
1. Django's base view classes always go on the far right.
2. Mixins go to the left of the base class.
3. Mixins should inherit from `object` (or a mixin base), never from
   a view class.

**GCBV usage table:**

| Task | View class | Form? |
|---|---|---|
| Display one object | DetailView | No |
| List objects | ListView | No |
| Create object | CreateView | Yes |
| Update object | UpdateView | Yes |
| Delete object | DeleteView | Confirm |
| Simple static page | TemplateView | No |
| Redirect | RedirectView | No |
| Date-based list | ArchiveIndexView et al. | No |
| Form without model | FormView | Yes |

**LoginRequiredMixin:** always the far-left mixin. If not far left, MRO
may skip the login check.

**form_valid / form_invalid:** override `form_valid()` to add behavior
after successful validation (send email, create related objects).
Always call `super().form_valid(form)`.

### Async views (Ch11)

- `async def` view functions or `AsyncViewMixin` for I/O-bound work.
- Django ORM is synchronous. Use `sync_to_async()` to call ORM code
  from async views.
- Requires ASGI deployment (Daphne, Uvicorn, Hypercorn).

**Anti-patterns:**
- Views with 200+ lines of business logic
- Deep CBV inheritance (more than 3 levels)
- CBVs where every method is overridden (FBV would be clearer)
- LoginRequiredMixin not in far-left position

## 4. Forms, Templates, and Frontend Integration

**Core concept:** forms are Django's data-validation layer. Templates
are the presentation layer. Keep business logic out of both.

### Five form patterns (Ch12)

1. **Simple ModelForm:** `ModelForm` with explicit `fields` list.
2. **ModelForm with custom validators:** `validators=[...]` on fields
   or `validate_<field>()` methods.
3. **ModelForm with clean overrides:** `clean_<field>()` for field-level,
   `clean()` for cross-field validation.
4. **Hacking fields in __init__:** modify fields dynamically based on
   user, permissions, or context via `self.fields['name']` in
   `__init__()`.
5. **Reusable search/filter mixin:** a Form mixin that applies
   `.filter()` chains to a queryset from cleaned data.

### Form fundamentals (Ch13)

- **Validate ALL user input with forms** (or DRF serializers). Never
  trust `request.POST` or `request.GET` directly.
- **CSRF always on.** Never disable. For AJAX: include the token from
  the cookie in the `X-CSRFToken` header.
- **Validation internals:** `is_valid()` calls `full_clean()` which
  runs: `_clean_fields()` (per-field), `_clean_form()` (cross-field
  `clean()`), `_post_clean()` (ModelForm-specific).
- **Form.add_error(field, error):** add errors programmatically in
  `clean()` rather than raising immediately.
- **Widget customization:** override in `Meta.widgets` or in
  `__init__()` via `self.fields['x'].widget.attrs`.
- **Never `Meta.exclude`** or `fields = "__all__"` on ModelForms.
  Explicit `fields = [...]` always -- prevents mass assignment.

### Template architecture (Ch14)

**2-tier or 3-tier inheritance:**
- 2-tier: `base.html` -> page template. Simple sites.
- 3-tier: `base.html` -> `section_base.html` -> page template. Sites
  with distinct sections (dashboard, public, admin).

**Five template gotchas:**
1. N+1 queries in template loops -- fix with `select_related`/
   `prefetch_related` in the view.
2. Hidden CPU in custom template tags that do heavy computation on
   every render -- cache the output.
3. Hidden REST calls from template tags that call external APIs -- move
   to the view or an async task.
4. Overly complex template logic -- `{% if %}` trees deeper than 2
   levels belong in the view or a template tag.
5. Missing error pages -- 404.html and 500.html must be static HTML
   (no template tags) because they render when Django itself is broken.

### Template tags, filters, and engines (Ch15-16)

- Filters are testable pure functions. Prefer filters over tags when
  the operation takes a value and returns a transformed value.
- Tags are harder to debug (access template context). Use sparingly.
- **DTL vs Jinja2:** Django supports both simultaneously. Jinja2 is
  faster and more flexible. Use DTL for admin/forms integration, Jinja2
  for performance-critical rendering. CSRF in Jinja2: `{{ csrf_input }}`
  not `{% csrf_token %}`.

### JavaScript integration (Ch19)

- **SPA vs template enhancement:** prefer Django templates with
  progressive enhancement (HTMX, Alpine.js) unless a full SPA is
  required. SPAs add complexity (auth, state, two deployments).
- **json_script filter:** `{{ data|json_script:"my-data" }}` safely
  embeds JSON without XSS risk. Never use
  `<script>var data = {{ data }};</script>`.
- **AJAX + CSRF:** include the CSRF token from the cookie in
  `X-CSRFToken` header for POST/PUT/DELETE.

**Anti-patterns:**
- Business logic in templates
- `fields = "__all__"` or `Meta.exclude` on ModelForms
- Disabling CSRF
- Inline JSON without `json_script`

## 5. APIs -- Django REST Framework and GraphQL

**Core concept:** DRF is the standard for Django REST APIs. Apply the
same layered discipline as views and forms.

### DRF patterns (Ch17)

- **HTTP semantics:** GET is safe and idempotent. POST creates. PUT
  replaces. PATCH updates partially. DELETE removes. Return correct
  status codes (201 Created, 204 No Content, 400, 404, 410 Gone).
- **Permissions:** default to `IsAdminUser` or `IsAuthenticated`, not
  `AllowAny`. Permission classes compose with AND; use custom classes
  for OR logic.
- **Public identifiers:** never expose sequential database PKs in URLs.
  Use UUIDs or slugs. Sequential PKs leak count and enable enumeration.
- **ModelSerializer:** explicit `fields` list (never `"__all__"`). Use
  `read_only_fields` for computed/auto fields.
- **Generic API views:** `ListCreateAPIView`,
  `RetrieveUpdateDestroyAPIView`, etc. Same pattern as CBVs.

**API package layout:**

```
flavors/
  api/
    __init__.py
    serializers.py
    views.py
    urls.py
  models.py
  views.py
```

- **Versioning:** from day one. URL path versioning (`/api/v1/`) is
  the most explicit. When deprecating: return HTTP 410 Gone, not a
  silent redirect.
- **Rate limiting:** DRF throttling or django-ratelimit. Aggressive
  limits on unauthenticated endpoints.
- **Atomicity:** wrap API views in `@transaction.atomic()` or use
  `ATOMIC_REQUESTS`.

### GraphQL (Ch18)

- **Ariadne preferred** over Graphene. Schema-first (write `.graphql`
  files), async/ASGI native, Apollo Federation compatible.
- GraphQL complements REST; it does not replace it. Use GraphQL when
  clients need flexible queries across related objects. Use REST when
  endpoints are well-defined and cacheable.

**Anti-patterns:**
- `AllowAny` as default permission
- Sequential PKs in API URLs
- `fields = "__all__"` on serializers
- No API versioning
- No rate limiting on public endpoints

## 6. Architecture, Admin, Users, and Django Internals

**Core concept:** Django provides powerful built-in components. Understanding
their intended use and boundaries prevents FrankenDjango -- a project that
replaces Django's core with poorly-integrated alternatives.

### Core components (Ch20)

- **Do not replace Django's core.** Swapping the template engine for
  Mako, the ORM for SQLAlchemy, and forms for WTForms produces a project
  that gets none of Django's ecosystem benefits. If you need a different
  stack, use a different framework.
- **NoSQL:** only for caches, queues, and denormalized search indexes.
  PostgreSQL JSON fields cover most "document storage" needs without
  adding a second data store.

### Admin (Ch21)

- **Not for end users.** The admin is a developer/operator tool. Build
  a proper UI for end-user functionality.
- `__str__()` on every model. `list_display` for useful columns.
- **`format_html()` for XSS safety:** never `mark_safe()` with user
  data in admin.
- **Security:** `django-admin-honeypot` for brute-force detection.
  Change URL from `/admin/`. Restrict by IP. Require HTTPS.

### User model (Ch22)

- **`get_user_model()`** in code (dynamic lookup).
  **`AUTH_USER_MODEL`** in ForeignKey definitions (string reference).

**Three approaches:**

| Approach | When to use |
|---|---|
| AbstractUser subclass | Default. Add fields. Set AUTH_USER_MODEL before first migration. |
| AbstractBaseUser | Full control over fields and auth. Rarely needed. |
| Related model (Profile) | Cannot change AUTH_USER_MODEL (third-party dependency). |

- **Multiple user types:** proxy models on one User table, not separate
  tables. Or a `role` field with permission-based access control.

### Third-party packages (Ch23)

- Pin versions. Use `pip-tools` or Poetry.
- 12-criteria checklist: tests, docs, maintainer activity, compatibility,
  issue tracker, downloads, code quality, release cadence, license,
  Django version support, Python version support, security record.

### Async task queues (Ch27)

**Use for:** bulk email, file processing, large API fetches, bulk
inserts, time-intensive calculations, webhook delivery.

**Do not use for:** profile updates, blog/CMS saves -- user expects
immediate feedback in the request cycle.

### Logging (Ch29)

- **Levels:** CRITICAL (system-breaking), ERROR (uncaught exceptions,
  emails ADMINS), WARNING (CSRF failures, honeypot), INFO (startup,
  permissions, performance), DEBUG (replaces print statements).
- **No f-strings in logger calls:**
  `logger.info("User %s logged in", user)` -- deferred formatting skips
  string construction when the level is disabled.
- **`logger.exception()`** in except blocks for automatic traceback
  capture. Or `logger.error("msg", exc_info=True)`.
- **One logger per module:** `logger = logging.getLogger(__name__)`.
- **Rotating files:** `WatchedFileHandler` + `logrotate`, not
  `RotatingFileHandler` (race conditions under multiprocess).
- Sentry for error aggregation. Loggly for log management.

### Documentation (Ch25)

- GFM as default format. MkDocs or Sphinx with MyST for larger projects.
- Minimum set: README.md, docs/, deployment.md, installation.md,
  architecture.md.
- Build weekly via CI. Interrogate for docstring enforcement.

### Utilities (Ch31)

**Core app pattern:** a `core` or `common` app for project-wide
abstractions (TimeStampedModel, shared managers, view mixins).

**django.utils gems:** `humanize` (intcomma, naturaltime, ordinal),
`method_decorator` (apply function decorators to CBV methods),
`cached_property`, `format_html` (XSS-safe interpolation),
`slugify` (with `allow_unicode=True`), `timezone`.

**Useful exceptions:** `ImproperlyConfigured` (missing settings),
`ObjectDoesNotExist` (base for all DoesNotExist), `PermissionDenied`
(returns 403).

**Serializers:** `DjangoJSONEncoder` for dates/decimals/UUIDs.
`yaml.safe_load()` only. `defusedxml` for XML. DRF serializers when
built-in JSON is insufficient.

## 7. Security, Testing, and Production Readiness

**Core concept:** security is not a feature -- it is a property
requiring discipline across every layer. Testing verifies that
discipline holds. Performance ensures it works under load.

### Security hardening (Ch28)

**Django's built-in protections:**
- **XSS:** auto-escaping in templates. Never `|safe` or `mark_safe()`
  on user content. Use `format_html()`. Use `json_script` for data
  embedding.
- **CSRF:** enabled by default. Token in all POST forms. AJAX: read
  from cookie, send in `X-CSRFToken` header.
- **SQL injection:** ORM parameterizes queries. For `.raw()` and
  `cursor.execute()`, always use parameter substitution.
- **Clickjacking:** `X-Frame-Options: DENY` via XFrameOptionsMiddleware.
- **Password hashing:** PBKDF2 default. Upgrade: put
  `Argon2PasswordHasher` first in `PASSWORD_HASHERS`.
- **XML bombs:** Django's parser is hardened. External XML: use
  `defusedxml`.

**Application-layer hardening:**
- `DEBUG = False` in production. Always. `ALLOWED_HOSTS` explicit (not
  `['*']`).
- `SECRET_KEY` out of VCS. Unique per environment.
- HTTPS everywhere: `SESSION_COOKIE_SECURE = True`,
  `CSRF_COOKIE_SECURE = True`.
- `SECURE_SSL_REDIRECT = True`. Set `SECURE_PROXY_SSL_HEADER` behind
  reverse proxy.
- **HSTS progression:** `SECURE_HSTS_SECONDS`: start 300 (5 min),
  increment to 3600, then 86400, then 31536000 (1 year), then submit
  to hstspreload.org.
- **CSP:** `django-csp` for Content Security Policy headers. Prevents
  inline scripts, mitigates XSS even if escaping fails.
- No `eval()`, `exec()`, `execfile()` on any user-reachable path.
- `yaml.safe_load()` only. `yaml.load()` with untrusted input is RCE.
- No pickle deserialization of untrusted data. JSON cookie serializer:
  `SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'`.
- Validate everything with forms or DRF serializers.
- Disable autocomplete on payment fields.
- User uploads via CDN with `Content-Disposition: attachment`. Validate
  with `python-magic` (content, not extension). Never serve from app
  domain.
- Never `Meta.exclude` or `fields = "__all__"` -- mass assignment.
- Do not store credit cards, PII, or PHI unless legally required with
  proper encryption and compliance.
- Monitor deps: pyup.io, Dependabot, or Safety.
- 2FA: TOTP preferred over SMS.
- Passwords: length over complexity. Allow paste.
- Never display sequential PKs publicly -- use slugs or UUIDs.
- SRI (Subresource Integrity) for external CSS/JS.
- `manage.py check --deploy` before every deployment.

### Testing (Ch24)

- **`tests/` directory per app** (not a single `tests.py`). Mirror
  module structure: `test_models.py`, `test_views.py`, `test_forms.py`.
- **Each test tests one thing.** Name describes the scenario.
- **RequestFactory** for unit-testing views without full HTTP stack.
  **Client** for integration tests.
- **DRY does not apply to tests.** Duplicate setup for clarity. Each
  test readable in isolation.
- **factory_boy over fixtures.** Fixtures are static JSON that rots.
  Factories generate data and evolve with the schema.
  `SubFactory` for relations. `LazyAttribute` for computed fields.
  `Sequence` for unique values.
- **Mock external APIs:** `@mock.patch.object(Service, 'call')`. Mock
  only at system boundaries (external APIs, filesystems, email). Do
  not mock the database.
- **Assertions:** `assertRaises`, `assertContains(response, text)`,
  `assertHTMLEqual(html1, html2)`, `assertInHTML(needle, haystack)`,
  `assertJSONEqual(raw, expected)`.
- **Integration tests:** Selenium for browser tests. httpbin.org for
  HTTP client testing.
- **CI:** run tests on every push. `pytest-django` is a valid
  alternative to Django's test runner.
- **Coverage game:** no commit may lower the project's overall test
  coverage. Enforce with `coverage.py` and CI gates.

### Performance (Ch26)

- **django-debug-toolbar:** starting point. SQL panel shows every query
  per view. Identify N+1 before optimizing.
- **Profiling:** `silk` or `RunProfileServer` for function-level timing.
- **select_related / prefetch_related:** highest-impact optimization
  for un-optimized codebases.
- **cached_property:** for expensive model methods accessed multiple
  times per request.
- **Caching:** Memcached or Redis. Template fragment caching. Per-view
  caching. django-cacheops or django-cachalot for automatic query
  caching (cachalot has invalidation edge cases -- understand before
  using).
- **EXPLAIN ANALYZE:** for slow queries. Run against production-sized
  data, not dev fixtures.
- **Do not store in DB:** logs, ephemeral data, binary files. Use log
  aggregators, caches, object storage.
- **Compression:** prefer Nginx-level gzip over `GZipMiddleware`.

## Common Mistakes

| Mistake | Why it fails | Fix |
|---|---|---|
| Single settings file | Secrets in VCS, no env parity | Split base/local/production/test |
| SQLite in dev | Hides PostgreSQL-specific bugs | Same DB engine everywhere |
| Anemic models | Logic scatters to views | Fat models with methods/managers |
| Fat views | Untestable business logic | Extract to models and services |
| `fields = "__all__"` | Mass assignment vulnerability | Explicit field lists always |
| `mark_safe()` on user data | XSS vulnerability | `format_html()` or `json_script` |
| No CSRF in AJAX | CSRF bypass | Token in `X-CSRFToken` header |
| Sequential PKs in URLs | Enumeration attack | UUIDs or slugs |
| Mocking the database | Tests diverge from production | Mock only system boundaries |
| No coverage tracking | Silent quality regression | coverage.py + CI gate |
| f-strings in loggers | Wasted string construction | `logger.info("msg %s", val)` |
| `yaml.load()` | Remote code execution | `yaml.safe_load()` only |

## Quick Diagnostic

| Question | If No | Action |
|---|---|---|
| Settings split into multiple files? | Secrets at risk | Split now, env-var secrets |
| Same DB in dev and production? | Hidden bugs | Switch dev to PostgreSQL |
| Models carry business logic? | Fat views | Move logic to model methods |
| Forms validate all user input? | Trust boundary violated | Add form/serializer validation |
| CSRF enabled on all forms? | Bypass possible | Enable, add AJAX token |
| `check --deploy` passing? | Security gaps | Fix all warnings |
| Using factory_boy for test data? | Fixture rot | Switch to factories |
| API versioned from day one? | Breaking changes | Add URL versioning |
| Admin URL changed from /admin/? | Brute force target | Change URL, add honeypot |
| Coverage monitored in CI? | Silent regression | Add coverage.py gate |
| HSTS enabled and progressing? | Downgrade attacks | Start at 300s, increment |
| One logger per module? | Untraceable errors | `getLogger(__name__)` everywhere |

## When this skill does NOT apply

- Pure performance infrastructure (caching tiers, load balancing, Varnish,
  horizontal scaling) -- see [skill:shelves--high-performance-django]
- Rescuing a legacy codebase that did not follow these practices -- see
  [skill:shelves--django-design-patterns] for the rescue methodology
- Non-Django Python projects -- see [skill:shelves--languages]
- Frontend framework architecture (React, Vue) -- Two Scoops focuses on
  server-side Django; see Section 4 for the enhancement-vs-SPA decision
- Distributed system design beyond Django (microservices, event sourcing,
  CQRS) -- see [skill:shelves--systems-architecture]

## Companions

- [skill:shelves--high-performance-django] -- after building correctly, scale it
- [skill:shelves--django-design-patterns] -- legacy rescue and pattern vocabulary
- [skill:shelves--clean-code] -- general code quality principles
- [skill:shelves--pragmatic-programmer] -- broader engineering discipline
- [skill:shelves--data-intensive] -- database internals beyond Django's ORM

## Source and license

- **Title:** Two Scoops of Django 3.x
- **Authors:** Daniel Feldroy, Audrey Feldroy
- **Publisher:** Feldroy (self-published)
- **Edition:** 5th (covers Django 3.x)
- **License:** Paid. No free edition available.
- **URL:** feldroy.com
- **Coverage:** FULL -- all 37 chapters + appendices absorbed from
  procured PDF on 2026-06-02. Chapters 30-36 are stubs ("Chapter in
  Progress") in the book; content from Chapters 1-29, 37, and
  Appendix A is complete.
- **Verified:** 2026-06-02 (confirmed no Django 5 edition exists;
  5th edition covering Django 3.x is the latest)
