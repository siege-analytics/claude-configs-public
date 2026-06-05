---
name: django-design-patterns
description: 'Django design patterns, anti-patterns, legacy code rescue, and async architecture with Celery and Channels. Use when the user mentions "Django design patterns", "Django anti-patterns", "Django legacy code", "Django refactoring", "Django code smells", "Django migration from legacy", "strangler fig Django", "Django test harness", "fat models", "fat views", "Django monolith", "dealing with legacy Django", "Django technical debt", "Django code rescue", "Django Celery patterns", "Celery retry", "Celery idempotent", "Django Channels", "Django WebSocket", "Django feature flags", "django-waffle", "inspectdb", "characterization tests", "Django services pattern", "Django MRO", "Django PRG pattern", or "Django MTV". Also trigger when inheriting a Django codebase, refactoring a Django monolith, diagnosing structural problems in Django projects, designing async task pipelines with Celery, implementing real-time features with Channels, or deciding how to incrementally modernize a Django application. For performance infrastructure see high-performance-django; for greenfield best practices see two-scoops-django.'
license: 'Paid book (Packt Publishing)'
metadata:
  source: 'Arun Ravindran -- Django Design Patterns and Best Practices (2nd edition, Packt 2018). Covers Django 2.x; structural patterns, rescue methodology, and async architecture remain relevant across Django versions.'
  coverage: 'FULL -- all 13 chapters absorbed from procured PDF on 2026-06-02.'
---

# Django Design Patterns and Legacy Rescue Framework

A pattern catalog, async architecture guide, and rescue methodology for
Django applications. Apply when inheriting a Django codebase, diagnosing
structural problems in an existing project, designing Celery task
pipelines, implementing real-time features with Django Channels, or
deciding how to incrementally refactor a Django monolith toward best
practices.

**Edition note:** covers Django 2.x. Structural patterns (MTV, services,
mixins, QuerySet chaining), the legacy rescue methodology, and async
architecture (Celery, Channels) are version-stable. Supplement with
current Django docs for post-2.x async features (async views, async ORM).

## Core Principle

**Every Django codebase encodes design decisions, whether the developers
made them consciously or not.** Recognizing the patterns (and
anti-patterns) already present in a codebase is the prerequisite to
improving it. You cannot refactor what you cannot name. This book
provides the vocabulary for naming what you see, the async patterns for
scaling what you build, and the methodology for changing what needs
fixing -- incrementally, safely, under test.

## Scoring

**Goal: 10/10.** When evaluating a Django codebase's structural health,
a refactoring plan, or an async architecture, rate 0-10 on pattern
recognition, async discipline, and rescue methodology.

- **9-10:** Patterns are named and intentional. Anti-patterns identified
  and tracked. GoF/Fowler equivalents understood. Celery tasks are
  idempotent with retry/backoff. Channels used for real-time features.
  Refactoring is incremental with characterization tests at each step.
  Legacy code has test coverage before changes.
- **7-8:** Most patterns recognizable. Celery tasks work but lack
  retry discipline. Some anti-patterns identified but not addressed.
  Refactoring underway with partial test coverage.
- **5-6:** Mixed patterns -- some intentional, some accidental. Celery
  used but tasks share mutable state unsafely. Anti-patterns present
  but undiagnosed. Refactoring attempted without test safety net.
- **3-4:** No pattern awareness. Fat views with 500+ lines. Logic in
  templates. Celery tasks pass model objects. No refactoring plan.
- **1-2:** Codebase is a collection of workarounds. No tests. Async
  tasks fail silently. Changes are high-risk.

## 1. Architecture and Pattern Vocabulary

**Core concept:** Django's MTV (Model-Template-View) architecture maps
to classical design patterns. Knowing the mapping gives you a shared
vocabulary for diagnosing and discussing structural decisions.

### MTV vs MVC

Django's View is the Controller. Django's Template is the View. The
Model is the Model. The naming difference is Django convention, not a
different architecture. Django adds its own patterns: URL dispatcher
(Front Controller), middleware pipeline (Decorator/Chain of
Responsibility), signals (Observer).

### GoF patterns in Django

| GoF pattern | Django equivalent |
|---|---|
| Command | HttpRequest/HttpResponse cycle |
| Observer | Signal dispatcher (post_save, pre_delete, etc.) |
| Template Method | CBV hooks (get_queryset, form_valid, get_context_data) |
| Strategy | Swappable backends (cache, email, auth, storage, template engine) |
| Flyweight | QuerySet caching (evaluated querysets are reused) |
| Decorator | Middleware, view decorators (@login_required, @cache_page) |

### Fowler patterns in Django

| Fowler pattern | Django equivalent |
|---|---|
| Active Record | Model (fields + behavior + persistence in one class) |
| Identity Map | QuerySet evaluation cache (same query, same objects) |
| Lazy Loading | Related object access (ForeignKey traversal deferred until accessed) |

### Requirements and app design (Ch2)

**10-step requirements gathering:**
1. Gather business context and domain vocabulary
2. Write user stories
3. Build feature list from stories
4. Identify app candidates (one concern each)
5. Map app dependencies
6. Create wireframes for key flows
7. Identify entities and relationships
8. Plan iteration milestones
9. Prioritize features
10. Define MVP scope

**App division:** a medium Django project typically has 15-20 apps.
Each app is narrowly scoped. When in doubt, split -- merging is easier
than untangling.

## 2. Model Design and Data Patterns

**Core concept:** the model layer is where domain knowledge lives.
Getting the data model right -- normalized, well-named, with behavior
attached -- determines whether the rest of the application can be clean.

### The model hunt

- Start from requirements: identify every noun that needs persistence.
- Each noun is a candidate model. Relationships emerge from the verbs
  ("user creates post", "post belongs to category").
- Validate against user stories: can every story be served by the
  identified models?

### Splitting models.py

When an app has more than 5 models, convert `models.py` into a
`models/` package:

```
myapp/
  models/
    __init__.py   # import all models here
    posts.py
    comments.py
    tags.py
```

The `__init__.py` re-exports all models so external imports do not
change.

### Normalization

- Normalize to 3NF by default. Every non-key attribute depends on the
  key, the whole key, and nothing but the key.
- Denormalize selectively for read performance -- add redundant fields
  only when profiling shows the JOIN is the bottleneck, and maintain
  consistency via signals or save() overrides.

### QuerySet chaining

Custom managers and querysets that compose:

```python
class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status='published', pub_date__lte=now())

    def featured(self):
        return self.filter(is_featured=True)

class Post(models.Model):
    objects = PostQuerySet.as_manager()
```

Callers compose: `Post.objects.published().featured()` -- readable,
testable, DRY. Never scatter raw filter chains across views.

### Model mixins

Extract cross-cutting model behavior into mixins:
- **TimestampedMixin:** `created_at`, `modified_at` auto-fields
- **SoftDeleteMixin:** `is_deleted` flag with custom manager
- **OrderedMixin:** `position` field with reordering methods

**Anti-patterns:**
- God model with 50+ fields and dozens of methods
- Anemic models (field-only, no behavior)
- Raw filter chains duplicated across views
- Premature denormalization without profiling evidence

## 3. Views and URL Design

**Core concept:** views are thin dispatchers. Business logic belongs
in models or a services layer. The view's job is: accept input,
validate it, delegate to the domain layer, return a response.

### FBV vs CBV decision

- **FBVs:** explicit, easy to read, easy to decorate. Preferred for
  one-off logic, custom HTTP method handling, views that do not fit
  standard CRUD patterns.
- **CBVs:** 20+ generic views for standard patterns. Preferred when
  the view fits a known pattern (list, detail, create, update, delete)
  and benefits from mixin composition.

### Generic CBVs

Django provides 20+ built-in generic CBVs. The key ones:

| Pattern | CBV |
|---|---|
| Display one object | DetailView |
| List objects | ListView |
| Create | CreateView |
| Update | UpdateView |
| Delete | DeleteView |
| Date-based archive | ArchiveIndexView, YearArchiveView, etc. |
| Redirect | RedirectView |
| Static page | TemplateView |
| Form processing | FormView |

### MRO (Method Resolution Order)

Multiple inheritance in CBV mixins follows Python's C3 linearization.
When diamond conflicts arise, Python raises `TypeError`. Keep mixins
focused on one concern. The mixin order matters: leftmost wins for
methods with the same name.

### Services pattern

When business logic grows beyond what model methods can cleanly hold,
extract to a `services.py` module:

```python
# services.py
def place_order(user, cart):
    order = Order.objects.create(user=user)
    for item in cart:
        OrderItem.objects.create(order=order, product=item.product)
    send_confirmation.delay(order.pk)
    return order
```

Views call services. Services call models. Models handle persistence.
This keeps views thin and business logic testable without HTTP.

### URL design

- Readable and hierarchical: `/articles/2024/django-patterns/`
- Trailing slashes: follow Django convention (APPEND_SLASH = True)
- API URLs versioned: `/api/v1/articles/`
- Use `path()` with typed converters (`<int:pk>`, `<slug:slug>`)

**Anti-patterns:**
- Fat views with 200+ lines
- Business logic in URL patterns
- Deep CBV inheritance (more than 3 levels)
- Missing services layer when model methods grow unwieldy

## 4. Templates, Admin, and Forms

**Core concept:** templates should be as logic-free as possible. The
admin is for operators, not end users. Forms handle the full validation
lifecycle.

### Template philosophy (Ch5)

- The ideal template contains only presentation markup and simple
  iteration/conditionals. Complex logic belongs in the view, a template
  tag, or a model method.
- **Madame Grinch anti-pattern:** templates overloaded with custom tags
  that effectively put Python logic in HTML. If a template tag does more
  than format output, it probably belongs in the view.
- **Jinja2:** faster, supports Python expressions, can coexist with DTL.
  Use DTL for admin integration; Jinja2 for performance-critical pages.
- **Bootstrap integration:** `django-bootstrap5` or `django-crispy-forms`
  with Bootstrap template packs. Do not hardcode Bootstrap classes in
  template markup -- use form rendering helpers.
- **Active link pattern:** a template tag or context processor that marks
  the current navigation item as active based on URL matching.

### Admin customization (Ch6)

- `ModelAdmin`: `list_display`, `list_filter`, `search_fields`,
  `ordering` for useful list views.
- `fieldsets` for organized detail views. `inlines` for related objects.
- Custom admin actions for batch operations.
- `readonly_fields` for computed/derived values.
- **Feature flags:** `django-waffle` for gradual rollout. Three
  mechanisms: switches (global on/off), flags (per-user/group), samples
  (percentage-based). Use for risky deploys, A/B testing, or
  incremental feature releases.

### Form lifecycle (Ch7)

1. **GET:** render blank form (create) or populated form (update).
2. **POST:** bind data to form, validate.
3. **Valid:** save, redirect (PRG pattern).
4. **Invalid:** re-render with errors.

- **CSRF:** middleware + `{% csrf_token %}` in every form. SameSite
  cookie attribute adds defense in depth.
- **django-crispy-forms:** declarative layout control. Separates form
  logic from rendering. Bootstrap, Tailwind, and Foundation packs.
- **PRG (Post-Redirect-Get):** after successful form submission, always
  redirect. Prevents duplicate submissions on browser refresh. Use
  `HttpResponseRedirect` or `redirect()`.

**Anti-patterns:**
- Logic in templates (if-trees deeper than 2 levels)
- Admin exposed to end users
- Form submissions without PRG (duplicate data on refresh)
- Feature toggles via settings instead of feature flags

## 5. Async Patterns -- Celery and Django Channels

**Core concept:** Django's request-response cycle is synchronous. For
background processing (Celery) and real-time bidirectional communication
(Channels), you need async architecture. Each tool solves a different
problem.

### Celery task design (Ch8)

**Task declaration:**

```python
@shared_task
def send_notification(user_pk):
    user = User.objects.get(pk=user_pk)
    # ... send notification
```

`@shared_task` makes tasks app-independent (no need to import the
Celery app instance). Dispatch with `.delay()` for simple calls or
`.apply_async()` for options (countdown, eta, queue).

**Error handling and retry:**

```python
@shared_task(
    autoretry_for=(HTTPError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5
)
def fetch_external_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
```

- `autoretry_for`: exception classes that trigger automatic retry.
- `retry_backoff=True`: exponential backoff between retries.
- `retry_jitter=True`: randomize backoff to prevent thundering herd.

**Idempotent task design:**
- Tasks may execute more than once (broker redelivery, worker crash).
  Design so re-execution produces the same result.
- Use `F()` expressions for shared state updates:
  `Counter.objects.filter(pk=pk).update(count=F('count') + 1)` is
  safe under concurrent execution.
- **Pass PKs, not model objects.** Model objects serialize stale data.
  Refetch inside the task for current state.

### Django Channels (Ch8)

- **ASGI:** async server gateway interface. Deploy with Daphne (official)
  or Uvicorn.
- **Channel layers:** Redis-backed message passing between consumers.
- **WebSocket consumers:** handle connect, receive, disconnect lifecycle.

```python
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("chat", self.channel_name)
        await self.accept()

    async def receive(self, text_data=None):
        await self.channel_layer.group_send(
            "chat", {"type": "chat.message", "message": text_data}
        )

    async def chat_message(self, event):
        await self.send(text_data=event["message"])
```

### Channels vs Celery

| Need | Use |
|---|---|
| Background processing (email, reports, ETL) | Celery |
| Real-time bidirectional (chat, notifications, live updates) | Channels |
| Scheduled tasks (cron-like) | Celery Beat |
| Long-running computation | Celery |
| Push updates to connected clients | Channels |

They complement, not compete. A common pattern: Celery task completes
work, then sends result to connected clients via Channels.

**Anti-patterns:**
- Passing model objects to Celery tasks (stale data)
- Non-idempotent tasks (unsafe under redelivery)
- Missing retry/backoff (silent failures on transient errors)
- Using Celery for real-time features (wrong tool)
- Using Channels for batch processing (wrong tool)

## 6. REST APIs, Testing, and Debugging

**Core concept:** APIs extend Django to external consumers. Testing and
debugging ensure correctness. The discipline is the same: validate at
boundaries, test contracts, debug systematically.

### REST API patterns (Ch9)

**REST constraints:** client-server separation, statelessness,
cacheability, layered system, uniform interface, optional code-on-demand.

**DRF architecture:**
- **Serializers:** validate and transform data. `ModelSerializer` for
  CRUD; `Serializer` for custom shapes.
- **APIView:** function-based-view equivalent for DRF. Method handlers
  for GET, POST, PUT, PATCH, DELETE.
- **Browsable API:** DRF's HTML interface for interactive exploration.
  Valuable during development; consider restricting in production.

**Five API rules:**
1. Version from day one (`/api/v1/`).
2. Serialize with explicit field lists, never `"__all__"`.
3. Permission classes on every view.
4. Pagination on every list endpoint.
5. Throttling on unauthenticated endpoints.

### Testing patterns (Ch11)

**TDD cycle:** Red (write failing test) -> Green (minimal code to pass)
-> Refactor (clean up without changing behavior).

**FIRST principles:** Fast, Independent, Repeatable, Self-validating,
Timely.

- **factory_boy:** generate test data programmatically. Factories evolve
  with the schema; fixtures rot.
- Structure tests by layer: `test_models.py`, `test_views.py`,
  `test_forms.py`, `test_serializers.py`.
- Test one thing per test. Name describes the scenario.
- Integration tests for critical paths. Unit tests for model logic.

### Debugging tools (Ch11)

- **Werkzeug debugger:** interactive in-browser debugger. More powerful
  than Django's default error page. Do not enable in production.
- **django-debug-toolbar:** query count, template rendering, cache hits,
  signal firing. The first tool to install on any Django project.
- **pdb / pudb:** breakpoint debugging. `import pdb; pdb.set_trace()`
  (or `breakpoint()` in Python 3.7+). pudb provides a curses UI.

**Anti-patterns:**
- APIs without versioning
- `fields = "__all__"` on serializers
- Testing implementation instead of contracts
- Debugging by adding print statements (use logging or debugger)

## 7. Legacy Code Rescue and Production Readiness

**Core concept:** legacy Django code requires a specific rescue
methodology. You cannot safely rewrite; you must refactor incrementally,
under test, toward a production-ready state.

### Legacy rescue methodology (Ch10)

**Step 1: Reverse-engineer the existing state.**
- `manage.py inspectdb` generates model definitions from an existing
  database. The output is a starting point, not final code -- review
  field types, add relationships, fix naming.
- Read code to understand actual data flow, not intended data flow.
- Map "load-bearing" code -- the parts that, if broken, bring down the
  application.

**Step 2: Add characterization tests.**
- Before changing ANY legacy code, write tests that capture current
  behavior -- even if that behavior is wrong.
- Use the Django test client for coarse integration tests against views.
  These are fast to write and catch regressions.
- factory_boy for test data. Fixtures rot; factories evolve.

**Step 3: Identify seams.**
- A seam is where you can change behavior without changing surrounding
  code. In Django: URL routing, middleware, view dispatch, signal
  handlers, template tags.
- The strangler fig pattern: wrap legacy views with new implementations.
  Route traffic incrementally (by URL, by feature flag, by percentage).
  Retire old code when the new path is proven.

**Step 4: Refactor incrementally.**
- One pattern at a time. Extract a service layer from the fattest view.
  Add a custom manager to the most-queried model. Split the god model.
- Each step must: (a) have test coverage, (b) not change behavior,
  (c) be deployable independently.

**Step 5: Modernize configuration.**
- Most legacy projects have a single `settings.py` with hardcoded
  values and secrets. Split into base/local/production/test. Extract
  secrets to environment variables. This is safe to do early because
  it does not change application behavior.

### Incremental vs big-bang rewrite

- **Big-bang rewrite almost always fails.** The new system must reach
  feature parity while the old system continues accumulating requirements.
  The two diverge. The rewrite is never finished.
- **Incremental refactoring** with strangler fig: new code wraps old,
  traffic migrates gradually, old code is retired piece by piece. Each
  step is deployable and reversible.
- Track technical debt explicitly. Every anti-pattern identified gets a
  ticket. Debt is work, not background noise.

### Security checklist (Ch12)

- **XSS:** Django auto-escapes templates. Never bypass on user content.
  Mark user-generated HTML with bleach or similar sanitizer.
- **CSRF:** middleware + token in every form. SameSite cookies.
- **SQL injection:** ORM parameterizes. For raw SQL, always use params.
- **Clickjacking:** X-Frame-Options middleware.
- **Shell injection:** never pass user input to `os.system()`,
  `subprocess.call()` with `shell=True`, or `eval()`.
- 15+ item checklist covering: DEBUG=False, ALLOWED_HOSTS, SECRET_KEY
  rotation, HTTPS, HSTS, secure cookies, password validation,
  dependency scanning, input validation, file upload restrictions,
  admin access control, logging, rate limiting, 2FA, CSP headers.

### Production readiness (Ch13)

**Web stack:** Nginx (reverse proxy, static files) -> Gunicorn/uWSGI
(WSGI) -> Django. For async: Nginx -> Daphne/Uvicorn (ASGI) -> Django.

**Hosting options:** PaaS (Heroku, Render), IaaS (AWS, GCP, Azure),
containers (Docker + Kubernetes for microservices).

**Deployment automation:** Fabric or Ansible for repeatable deploys.
One-command deployment is the goal. Blue-green or rolling deploys for
zero downtime.

**Monitoring:** application metrics (response times, error rates),
server resources (CPU, memory, disk), log aggregation (ELK stack),
error tracking (Sentry).

**Performance optimization layers:**
- Frontend: minify CSS/JS, optimize images, use CDN, enable compression
- Backend: select_related/prefetch_related, database indexes, query
  optimization
- Caching: template fragment cache, per-view cache, full-page cache
  (Varnish), object cache (Redis/Memcached)

## Common Mistakes

| Mistake | Why it fails | Fix |
|---|---|---|
| Big-bang rewrite | Never reaches parity | Strangler fig, incremental |
| Refactoring without tests | Silent regressions | Characterization tests first |
| Non-idempotent Celery tasks | Data corruption on retry | F() updates, refetch state |
| Model objects in task args | Stale data, serialization | Pass PKs, refetch inside task |
| Celery for real-time | Wrong tool, high latency | Django Channels for push |
| God model (50+ fields) | Untestable, unmaintainable | Split into related models |
| Fat views | Logic untestable without HTTP | Services layer |
| Logic in templates | Invisible, untestable | Move to view or template tag |
| inspectdb output used as-is | Wrong types, missing relations | Review and correct every field |
| Admin exposed to end users | Security and UX problems | Build proper UI |

## Quick Diagnostic

| Question | If No | Action |
|---|---|---|
| Can you name the patterns in your codebase? | Accidental architecture | Map patterns using this vocabulary |
| Do characterization tests exist for legacy code? | Refactoring is unsafe | Write tests before any changes |
| Are Celery tasks idempotent? | Data corruption risk | Redesign with F(), refetch state |
| Do tasks pass PKs (not objects)? | Stale data risk | Refactor task signatures |
| Is there a services layer? | Fat views | Extract business logic |
| Are feature flags used for risky deploys? | All-or-nothing releases | Add django-waffle |
| Is deployment automated? | Human error on every deploy | Fabric/Ansible, one-command goal |
| Is technical debt tracked explicitly? | Invisible rot | Ticket every anti-pattern |
| Are models split when >5 per app? | models.py is unnavigable | Convert to models/ package |
| Is monitoring in place? | Blind to production issues | Sentry + metrics + log aggregation |

## When this skill does NOT apply

- Greenfield Django projects following best practices from the start --
  see [`shelves--two-scoops-django`](../../../shelves/django/two-scoops-django/SKILL.md)
- Performance optimization of structurally sound code -- see
  [`shelves--high-performance-django`](../../../shelves/django/high-performance-django/SKILL.md) (fix correctness before speed)
- General refactoring patterns outside Django -- see
  [`shelves--refactoring-patterns`](../../../shelves/engineering-principles/refactoring-patterns/SKILL.md) or [`shelves--clean-code`](../../../shelves/engineering-principles/clean-code/SKILL.md)
- Non-Django legacy codebases -- the Django-specific patterns (MTV,
  ORM managers, URL routing as seams) are central to this framework

## Companions

- [`shelves--two-scoops-django`](../../../shelves/django/two-scoops-django/SKILL.md) -- the target state for legacy rescue.
  Refactoring means moving toward Two Scoops conventions.
- [`shelves--high-performance-django`](../../../shelves/django/high-performance-django/SKILL.md) -- after structural rescue, optimize
  for performance
- [`shelves--clean-code`](../../../shelves/engineering-principles/clean-code/SKILL.md) -- general code quality principles
- [`shelves--refactoring-patterns`](../../../shelves/engineering-principles/refactoring-patterns/SKILL.md) -- broader refactoring catalog beyond
  Django-specific patterns
- [`shelves--release-it`](../../../shelves/systems-architecture/release-it/SKILL.md) -- production resilience patterns (circuit breakers,
  bulkheads) that complement deployment readiness

## Source and license

- **Title:** Django Design Patterns and Best Practices
- **Author:** Arun Ravindran
- **Publisher:** Packt Publishing
- **Edition:** 2nd (2018, covers Django 2.x)
- **License:** Paid. No free edition available.
- **Coverage:** FULL -- all 13 chapters absorbed from procured PDF on
  2026-06-02. Structural patterns and rescue methodology are
  version-stable. Supplement with current Django docs for post-2.x
  async features.
- **Verified:** 2026-06-02 (confirmed 2nd edition is latest; no 3rd
  edition covering Django 4/5 published)
