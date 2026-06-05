---
name: high-performance-django
description: 'Scale Django for high-traffic production: caching tiers, database optimization, load balancing, deployment automation, and performance testing. Use when the user mentions "Django performance", "Django caching", "Django scaling", "Django load balancing", "Django deployment", "Django database optimization", "Django Celery", "Django Redis", "high traffic Django", "Django production", "Django performance testing", "Django connection pooling", "Django read replicas", "Django horizontal scaling", "Django Varnish", "Django uWSGI", "Django load testing", "Russian doll caching", "cache stampede", or "thundering herd". Also trigger when optimizing an existing Django application for throughput, planning infrastructure for a Django deployment, debugging slow Django views, preparing for a site launch, or monitoring Django in production. For best practices see two-scoops-django; for legacy code see django-design-patterns.'
license: 'Free online edition (authors released it freely in 2021)'
metadata:
  source: 'lincolnloop.com/high-performance-django/ -- full text freely available online. Authors: Peter Baumgartner, Yann Malet (Lincoln Loop). Originally published 2014 via Kickstarter; released free online 2021.'
  coverage: 'FULL -- all 7 chapters absorbed via WebFetch 2026-06-02. Code samples from 2014 may reference outdated package versions; architectural patterns remain sound. See references/ for detailed configuration extracts.'
---

# High Performance Django Framework

A scaling blueprint for Django applications in production. Apply when
optimizing Django for higher traffic, planning deployment infrastructure,
implementing caching strategies, load-testing before launch, or
monitoring Django in production.

**Age caveat:** published 2014. Django has since added async views (3.1),
ASGI support, and other features. The book's caching, DB optimization,
and deployment architecture patterns predate these but remain valid as
the synchronous scaling playbook. Supplement with current Django docs
for async patterns. Specific tool versions (Varnish 4.1, Python 2.7
references) should be updated to current equivalents.

## Core Principle

**Performance is an architectural decision, not an optimization pass.**
You cannot bolt performance onto a Django application after the fact.
The choices made at project setup -- how you structure caching, how you
configure the database layer, how you deploy -- determine the performance
ceiling. The book provides a blueprint so you build with that ceiling
in mind from the start.

The guiding philosophy is simplicity, attributed to Dijkstra: "Simplicity
is a prerequisite for reliability." Minimize moving parts. Choose proven
solutions over experimental technology. Route traffic toward fast, simple
components (cache, load balancer) and away from complex ones (Django,
database).

## Scoring

**Goal: 10/10.** When evaluating a Django deployment for performance
readiness, rate 0-10 on the architectural patterns below.

- **9-10:** Multi-tier caching (template fragment, view, reverse proxy).
  Database optimized (connection pooling, read replicas, query analysis).
  Horizontal scaling ready (stateless app servers, shared-nothing).
  Load tested with realistic data. Monitoring and alerting in place.
  Pre-launch checklist passed. Rollback plan documented.
- **7-8:** Caching present but not tiered. Database tuned but no read
  replicas. App servers can scale but session state may block it.
  Some load testing done. Monitoring partial.
- **5-6:** Basic caching (memcached for sessions). Default DB config.
  Single app server. No load testing. Monitoring incomplete.
- **3-4:** No caching. Database on same server as app. No scaling plan.
  "We will optimize later."
- **1-2:** `DEBUG = True` in production. SQLite in production. No
  deployment automation.

## 1. The Big Picture -- Architecture

**Core concept:** Django alone does not scale. No web framework does.
Scaling comes from the infrastructure wrapped around Django -- caching
layers, load balancers, and task queues that keep requests from reaching
the slow parts of the stack.

**The canonical stack (front to back):**

| Tier | Role | Scales by | Response time |
|---|---|---|---|
| Load balancer (nginx, HAProxy) | Distributes requests, TLS termination | Adding instances | < 1ms |
| Web accelerator (Varnish) | Full-page cache, serves cached responses | RAM (in-memory cache) | ~10ms |
| App servers (uWSGI, gunicorn) | Run Django | Adding servers horizontally | 100-300ms (warm cache) |
| Cache layer (Redis, Memcached) | Reduces DB load | Partitioning keyspace | < 2ms |
| Database (PostgreSQL) | Source of truth | Vertically first, then read replicas | 1-500ms |
| Task queue (Celery + broker) | Async work | Adding workers | Background |
| Static/media (CDN, S3) | Offloaded from app servers | CDN edge nodes | Varies |

**Key insight:** each tier scales independently. Understanding which
tier is the bottleneck determines where to invest. Most requests should
end their journey at the web accelerator -- "most requests' journeys end
here."

**Performance benchmarks (from the book):**

| Component | Response time |
|---|---|
| Varnish cache hit | ~10ms |
| Django per-site cache hit | ~35ms |
| Django with warm application cache | 100-300ms |
| Django with cold cache | 500ms-2s |

No single component (database, cache, template rendering) should consume
more than ~30% of total request duration. If one does, that is the
bottleneck.

**Load balancer patterns:**
- Round robin is the recommended default distribution algorithm
- "Least connections" can cause problems when new servers join during
  traffic spikes -- they get overwhelmed before establishing stability
- TLS termination at the load balancer, plain HTTP internally

**Anti-patterns:**
- Serving static files through Django in production
- Running everything on one server with no tier separation
- Scaling app servers when the database is the bottleneck
- Replacing the database with NoSQL (pushes complexity into app code)

## 2. The Build -- Application-Level Performance

**Core concept:** most Django performance problems are in the application
code, not the infrastructure. Measure before optimizing -- use
`django-debug-toolbar` to see every query a view executes.

### Settings organization

Three-module structure:
- `settings.base` -- shared configuration across all environments
- `settings.deploy` -- production-specific (caching, security)
- `settings.local` -- developer-specific, not committed to VCS

Sensitive data via JSON config file rather than environment variables
(avoids type conversion issues):

```python
import json
with open('/srv/project/config.json') as config_file:
    CONFIG = json.load(config_file)
SECRET_KEY = CONFIG['SECRET_KEY']
```

### Query optimization

**select_related and prefetch_related** are the single most impactful
optimization on an un-optimized codebase -- can drop 50%+ of total
queries.

- `select_related('author')` -- follows ForeignKey in a single JOIN
- `prefetch_related('tags')` -- separate query for M2M/reverse FK,
  cached in Python
- Filtering after prefetch defeats the cache:
  `post.tags.filter(is_active=True)` triggers a new query.
  Instead: `[t for t in post.tags.all() if t.is_active]`

**Missing indexes:** use EXPLAIN (via debug toolbar) to find sequential
scans. Add `db_index=True` or `index_together`. Create migrations when
adding indexes.

**Counts are slow:** replace `if qs.count() > 0` with `if qs.exists()`.
For approximate counts, PostgreSQL: `SELECT reltuples FROM pg_class
WHERE relname = 'table_name'` (98% faster, ~1% variance).

**Reduce result size:**
- `defer('body')` -- everything except body
- `only('title')` -- only title
- `values_list('id', flat=True)` -- list of IDs, bypasses model init

**cached_property** for expensive model methods accessed multiple times
per request. Cache lifetime = request/response cycle only.

**Generic foreign keys:** avoid when possible due to performance
penalties and caching complexity.

### Caching tiers (Russian doll caching)

Nest cache blocks with different TTLs. Inner fragments expire
independently; only portions requiring re-render execute per request.

```django
{% cache MIDDLE_TTL "post_list" request.GET.page %}
  {% for post in post_list %}
    {% cache LONG_TTL "post_teaser" post.id post.last_modified %}
      {% include "inc/post/teaser.html" %}
    {% endcache %}
  {% endfor %}
{% endcache %}
```

Recommended TTLs for read-heavy sites:
- Short: 10 minutes
- Middle: 30 minutes
- Long: 1 hour
- Forever: 7 days

**Thundering herd / cache stampede prevention:** when many keys expire
simultaneously, all servers regenerate at once. Apply jitter:

```python
from random import randint
def jitter(num, variance=0.2):
    return randint(int(num * (1 - variance)), int(num * (1 + variance)))
```

**Query caching:** sits between ORM and database, manages invalidation
automatically. Useful for read-heavy sites.

### Async work with Celery

Anything > 200ms that is not required for the HTTP response belongs in
a Celery task: email, image processing, third-party API calls, reports.

**Task design rules:**
- Never pass Django model objects as arguments; pass primary keys and
  refetch inside the task
- Keep tasks small and atomic; one task can trigger others
- Avoid race conditions between DB commits and task execution -- use
  `on_commit()` hooks or task delay
- Separate high-priority user-facing queues from low-priority maintenance

**Celery Beat** for scheduled tasks: better than cron because it has
retry support and finer granularity.

### Front-end optimization

- Minify and bundle CSS/JS. Output must be versioned (unique filenames
  per build) to prevent stale browser caches.
- Compress images: `pngcrush` for static assets, optimization during
  thumbnailing for uploads. "Not uncommon to cut size by 50%+."
- Serve static assets from a CDN.

### File uploads at scale

- Single server: store locally
- Multiple servers: shared storage (S3, GlusterFS, Ceph)
- Pre-generate common thumbnail sizes via Celery on upload; maintain
  on-the-fly fallback from template tags

### Third-party app evaluation

Every dependency consumes RAM. A bare Python interpreter uses a couple
MB; production apps can exceed 200+ MB compounded by multiple WSGI
workers. Evaluate: does the app precisely match requirements? Is the
project healthy (tests, docs, maintainer activity)? Could a few
project-specific lines suffice instead?

## 3. The Deployment -- Infrastructure

**Core concept:** deployment automation is a performance feature. If you
cannot deploy quickly and reliably, you cannot iterate on performance.

### Code shipping (6 steps, automated to one command)

1. Version control checkout
2. Dependency updates
3. Database migration
4. Static file collection, compression, CDN push
5. WSGI server reload (graceful, not hard restart)
6. Background worker restart

Graceful reloads preserve load balancer pool membership. uWSGI's
`--touch-reload` provides convenient graceful reloading.

### Server layout and resource requirements

| Tier | Resource bottleneck | Scaling strategy |
|---|---|---|
| Load balancer | Network throughput | Managed cloud or medium VM |
| Web accelerator (Varnish) | RAM (in-memory cache) | Dedicated or collocated |
| App servers | CPU and/or RAM | Multiple smaller machines preferred |
| Background workers | CPU | Stateless, easily added/removed |
| Cache servers | RAM, network | Monitor eviction rates |
| Database | Disk speed, RAM | "Don't skimp" -- beefiest machine |

**App server worker count:** start with 2x CPU cores, increase until
CPU/RAM saturates.

**Database RAM rule of thumb:** enough to keep entire dataset in memory.
60GB expected DB = minimum 64GB RAM.

### PostgreSQL tuning

| Setting | Value |
|---|---|
| `shared_buffers` | 25% RAM, up to 8GB |
| `work_mem` | (2x RAM) / max_connections |
| `maintenance_work_mem` | RAM / 16 |
| `effective_cache_size` | RAM / 2 |
| `max_connections` | Less than 400 |

### uWSGI tuning

Key parameters:
- `processes`: start with 2x CPU cores, increase until saturated
- `threads`: additional concurrency for thread-safe apps
- `harakiri`: max request time before worker kill (prevents runaways)
- `max-requests`: respawn after X requests (stop-gap for memory leaks)
- `post-buffering`: max HTTP body in memory (prevents upload bloat)
- `thunder-lock`: improves load balancing among workers
- Emperor mode for multi-site hosting on single server

### Django settings for production

**CACHES:** use `pylibmc` for Memcached or `django-redis` for Redis.
For cache stampede prevention: `HerdClient` (django-redis) or `MintCache`
(django-ft-cache).

**Multiple cache servers increase failure probability.** Use `twemproxy`
with `auto_eject_hosts` -- removes failing servers from pool for 30s
after 3 consecutive failures. Transform catastrophic outage into ~3
failed requests every 30 seconds.

**SESSION_ENGINE:** default (database) touches DB on every request.
Alternatives: `cache` (if Redis persists to disk), `cached_db` (works
with Memcached), `signed_cookies` (zero server state).

**CONN_MAX_AGE:** set to `300` (5 minutes) or `None` (recycle
indefinitely). Default off = new connection per request.

**LOGGING:** log to stderr, let uWSGI or process manager capture output.
Do not log directly to files (permission issues, startup crashes).

**MIDDLEWARE:** custom middleware runs on every request. Avoid DB queries
in middleware. Understand what each middleware does.

### Web accelerator (Varnish) configuration

**Anonymous vs authenticated:** bypass cache for logged-in users (check
for `sessionid` cookie), strip cookies for anonymous requests.

**Hit rate patterns:**
- Anonymous-heavy sites: basic `vcl_recv` provides substantial gains
- Personalized sites: AJAX approach (cache anonymous page, fetch
  personalized bits via second request) or ESI (Edge Side Includes)

**Grace periods:** serve stale cached content when backends are down.
Configure backend health probes (every 5s, 3/5 failures = unhealthy).

**Cache purging:** custom PURGE method with strict ACL. Unrestricted
PURGE access enables DDoS via cache flushing.

See `references/varnish-config.md` for full VCL examples.

### Security

- Disable root SSH login and password authentication
- Use private networks between servers
- Lock down internal services (admin, CI, dashboards) via VPN or
  auth proxy
- Firewall: allow only expected traffic on specific ports
- Run processes as dedicated non-root users
- Secure third-party credentials (2FA, strong passwords)
- Run `manage.py check --deploy` (or `checksecure`) before every deploy

### Backup strategy

- Managed services preferred (RDS, Cloud SQL, S3 with versioning)
- Self-hosted: live replica + daily `pg_dump` + WAL archiving for PITR
- "Off-site" = different provider or region
- Test restores regularly. Script the restoration process.
- "Backups you have not restored from are not backups."

### Monitoring stack

| Need | Proprietary | Open source |
|---|---|---|
| Application metrics | NewRelic | Graphite + Grafana + django-statsd |
| Server resources | NewRelic | Collectd or Diamond + Graphite |
| Alerting | NewRelic | Nagios, Cabot |
| Log aggregation | Splunk, Loggly | ElasticSearch + Kibana + Logstash |
| Error reporting | -- | Sentry |

**Error reporting:** do NOT use Django's default email-on-traceback.
High-traffic errors DoS mail servers and trigger blacklisting. Use
Sentry (aggregation, deduplication, trending).

### Environments and single points of failure

- Maintain staging + production minimum. Stack parity between them.
- Never use production DB replicas in development (security risk +
  notification danger). Generate anonymized snapshots instead.
- No single points of failure. Stateless services are naturally
  resilient; data services need backup strategy.

## 4. The Preparation -- Load Testing and Launch

**Core concept:** load-test before launch, not after the site goes down.

### JMeter load testing

JMeter over simpler tools (ab, Siege) for comprehensive testing. Build
tests in GUI, export XML for headless execution.

**Setup requirements:**
- Cookie manager for Django CSRF handling
- `StringFromFile()` for dynamic URL construction from data files
- Header manager for AJAX simulation (`X-Requested-With: XMLHttpRequest`)
- Headless execution on remote servers to eliminate bandwidth constraints

```bash
jmeter -n -p user.properties -t my_test_plan.jmx -l my_results.jtl
```

Integrate with CI (Jenkins Performance Plugin) for trend analysis.

### Launch strategies

- **Gradual traffic migration:** load balancer traffic split, session
  affinity between old and new
- **Dark launch:** background AJAX requests to new infrastructure
- **Live traffic proxying:** mirror production traffic invisibly (Gor)
- **Feature flags:** release to user subsets progressively
- **Cache warming:** pre-populate caches with popular URLs before launch

### Pre-launch checklist

**Django config:**
- `DEBUG = False`, `TEMPLATE_DEBUG = False`
- Large random `SECRET_KEY` kept confidential
- `ALLOWED_HOSTS` configured
- Cached template loader enabled
- Fast session engine (not database default)
- Memcached or Redis configured
- Media uploads working

**Infrastructure:**
- Servers secured and locked down
- Single-command deployment working
- Horizontal scaling documented
- DNS TTL reduced to 5 minutes for quick changes
- Monitoring and alerting operational
- Error reporting active
- Custom error pages at all levels (Varnish, Django)
- Valid SSL certificates
- `manage.py check --deploy` passes clean
- Admin interface not at `/admin/`

**Timing:**
- Not end-of-day or Friday
- Full team available during and after
- Low-traffic period if patterns exist
- Team rested

## 5. The Launch -- Monitoring in Production

**Core concept:** production behavior differs dramatically from
development. Stack layers compete for scarce resources. Monitoring
enables performance optimization and incident response.

### What to watch per tier

**App servers (htop / uwsgitop):**
- Load average must not exceed CPU core count
- Flag Python processes > 300MB RES
- Average response time should be under 1 second
- If all workers busy with CPU/RAM available, add workers

**Varnish (varnishstat / varnishlog / varnishtop):**
- Hit rate for read-heavy sites should be 90%+
- Verify expected URLs are cached
- Identify top URLs bypassing cache for VCL optimization
- Catch common 404s or redirects in Varnish, not Django

Useful varnishtop filters:
- `varnishtop -b -i "BereqURL"` -- cache misses by URL
- `varnishtop -c -i "ReqURL"` -- cache hits
- `varnishtop -c -i RespStatus` -- response codes

**Celery (Flower / inspect / events):**
- All tasks completing successfully
- Queue growth rate vs worker processing capacity
- Add workers if resources available; add servers if not

**Memcached (memcache-top):**
- Hit rate should be in the 90s
- Balanced connections across servers
- Operations under 2ms average

**Database (pg_top / pg_stat_statements):**
- Connection count well under configured maximum
- Flag "Idle in transaction" connections lasting too long
- Queries > 1 second may need optimization or lock investigation
- Monitor iowait (should be near zero; high = disk bottleneck)

Find slowest queries with pg_stat_statements:

```sql
SELECT calls,
       round((total_time/1000/60)::numeric, 2) as total_minutes,
       round((total_time/calls)::numeric, 2) as average_ms,
       query
FROM pg_stat_statements
ORDER BY 2 DESC
LIMIT 100;
```

## 6. Disaster Response

**App server overload, DB fine:** scale app servers horizontally. This
is the simplest fix. Case study: one launch went from 4 to 8 servers
due to poor web accelerator config. After fixing Varnish and caching
legacy redirects, the site ran on 3 servers at 20% CPU.

**DB overload:** harder to scale horizontally. For read-heavy sites,
adding a read replica buys time. Case study: missing index from
incorrectly applied migration caused pathological performance on a
simple FK lookup. One SQL command to add the index "immediately dropped
database load to almost zero."

**Both overloaded:** either optimize from DB up, or tune web accelerator
to reduce downstream load. Case study: external application running
against the same database triggered long-running queries. Solution:
point read-only external app to a replica.

## 7. Post-Launch -- The Road Ahead

**Resource utilization rule:** never regularly exceed 70% (CPU, RAM,
disk) during normal operation. Maintain buffer for surges.

### Common post-launch failures

**Cache flush under load:** restarting caches during high traffic causes
stampede. Use Varnish reload (not restart) to preserve in-memory cache.
Use `KEY_PREFIX` and `VERSION` for selective invalidation. Schedule
restarts during low-traffic periods. Rolling restarts across servers.

**Database locking:** schema migrations on tables with millions of rows
create extended locks. MySQL `ADD COLUMN` requires full table copy and
lock. PostgreSQL handles this better. Always test migrations against
production-sized data before deploying.

**Mass cache invalidation:** changing cache key prefixes or bulk DB
edits generate thousands of cache misses simultaneously.

**Expensive admin views:** unoptimized admin can generate thousands of
queries. Apply standard view optimization.

**Gradual degradation:** silent performance decay when monitoring lapses
during feature development. Incorporate performance metrics review into
release process.

**Complexity creep:** the "not invented here" risk of replacing Varnish
with custom caching, etc. Custom infrastructure costs: developer
onboarding, maintenance, testing, documentation.

## Common Mistakes

| Mistake | Why it fails | Fix |
|---|---|---|
| Optimize without measuring | You fix the wrong thing | Use django-debug-toolbar, measure first |
| Cache at one tier only | Misses cascade to DB | Russian doll: fragment + view + proxy |
| Send email in request cycle | 200ms+ per request | Celery task |
| `count()` for existence checks | Full table scan | `exists()` |
| Filter after prefetch | New query, defeats cache | Filter in Python on prefetched set |
| SQLite in production | No concurrency | PostgreSQL always |
| Same server for everything | No isolation, no scaling | Tier separation from day one |
| Restart cache during peak | Stampede | Reload (not restart), rolling, low-traffic window |
| Skip load testing | "It works on my machine" | JMeter with realistic data volumes |
| Log to files from Django | Permission issues, crashes | Log to stderr, let process manager capture |

## Quick Diagnostic

| Question | If No | Action |
|---|---|---|
| Is DEBUG False in production? | Stop everything | Fix immediately |
| Are you measuring query count per view? | You are guessing | Install django-debug-toolbar |
| Is caching multi-tiered? | Single tier saturates | Add fragment + view + proxy tiers |
| Are sessions in external storage? | Cannot scale horizontally | Move to Redis or signed cookies |
| Is there a load balancer? | Single point of failure | Add one before launch |
| Have you load-tested with production data volumes? | You do not know your ceiling | Run JMeter against staging |
| Is monitoring in place? | You cannot see problems | Set up Grafana/Sentry before launch |
| Can you deploy in one command? | Human error on every deploy | Automate the 6-step process |
| Have you tested backup restores? | Backups may not work | Test restore now |
| Is resource utilization under 70%? | No headroom for spikes | Scale up or optimize |

## When this skill does NOT apply

- Writing correct Django code (project layout, model design, form
  validation) -- see [skill:shelves--two-scoops-django]
- Rescuing a structurally broken codebase -- fix correctness before
  optimizing performance; see [skill:shelves--django-design-patterns]
- Distributed system design beyond Django (microservices, event sourcing,
  CQRS) -- see [skill:shelves--systems-architecture]
- Frontend performance (bundle size, rendering, CDN for SPAs) -- this
  book focuses on the Django server side
- Async Django (ASGI, async views) -- this book predates Django 3.1;
  supplement with current Django docs

## Companions

- [skill:shelves--two-scoops-django] -- build correctly first, then scale
- [skill:shelves--django-design-patterns] -- if the codebase needs structural
  fixes before performance work is meaningful
- [skill:shelves--data-intensive] -- for deeper treatment of database internals,
  replication, and partitioning beyond Django's ORM
- [skill:shelves--release-it] -- production resilience patterns (circuit breakers,
  bulkheads) that complement Django scaling

## Source and license

- **Title:** High Performance Django
- **Authors:** Peter Baumgartner, Yann Malet
- **Publisher:** Lincoln Loop (originally Kickstarter-funded, 2014)
- **License:** Free online edition released 2021. No explicit Creative
  Commons declaration on the site; content is freely readable.
- **URL:** lincolnloop.com/high-performance-django/
- **Coverage:** FULL -- all 7 chapters absorbed via WebFetch on 2026-06-02.
  Code samples from 2014 may reference outdated package versions;
  architectural patterns remain sound.
- **Verified:** 2026-06-02 via WebFetch (all chapters confirmed readable:
  preface, intro, build, deployment, preparation, launch, road-ahead,
  final-thoughts)
