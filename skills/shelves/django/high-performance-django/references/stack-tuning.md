# Stack Tuning Reference

Extracted from High Performance Django, Chapters 3-5.

## PostgreSQL tuning

From Christophe Pettus' recommendations, cited in the book:

| Setting | Value | Notes |
|---|---|---|
| `shared_buffers` | 25% RAM, up to 8GB | PostgreSQL shared memory |
| `work_mem` | (2x RAM) / max_connections | Per-operation sort/hash memory |
| `maintenance_work_mem` | RAM / 16 | VACUUM, CREATE INDEX, etc. |
| `effective_cache_size` | RAM / 2 | Planner hint for OS cache |
| `max_connections` | Less than 400 | Use connection pooling if more needed |

**RAM rule of thumb:** enough to keep entire dataset in memory. 60GB
expected database = minimum 64GB RAM to minimize disk round-trips.

**Disk:** SSDs preferred. Monitor iowait (shown as `X%wa` in `top`).
Should be near zero; high values = disk bottleneck.

## MySQL tuning

- Use Percona configuration wizard for sane defaults
- `innodb-buffer-pool-size`: 80% of RAM
- MySQL `ADD COLUMN` requires full table copy and lock -- test migrations
  against production-sized data

## uWSGI configuration

### Process/thread settings

| Parameter | Purpose | Starting value |
|---|---|---|
| `processes` | Concurrent request capacity | 2x CPU cores |
| `threads` | Per-process concurrency | Start without, add if thread-safe |
| `thunder-lock` | Improved load balancing | Enable |

Increase processes until CPU/RAM saturates. If load average exceeds
core count, you have too many processes.

### Safety settings

| Parameter | Purpose | Recommendation |
|---|---|---|
| `harakiri` | Max request time before worker kill | Set per-app (e.g., 30s) |
| `max-requests` | Respawn after N requests (leak stop-gap) | Set high (e.g., 5000) |
| `post-buffering` | Max HTTP body in memory (bytes) | 4096 (larger to disk) |

### Monitoring settings

| Parameter | Purpose | Example |
|---|---|---|
| `stats` | Publish process stats | `127.0.0.1:1717` |
| `auto-procname` | Human-readable process names | Enable |
| `procname-prefix-spaced` | Prefix for multi-site | Site name |
| `log-x-forwarded-for` | Log real client IP | Enable behind proxy |
| `req-logger` | Access log | `file:/var/log/uwsgi/access.log` |
| `logger` | Error/app log | `file:/var/log/uwsgi/error.log` |

### Emperor mode (multi-site)

Emperor (main process) manages vassals (sites). Adding `.ini` to
`/etc/uwsgi/vassals-enabled` starts the site; deleting kills it;
editing gracefully reloads.

```ini
emperor = /etc/uwsgi/vassals-enabled
```

### Async workers warning

Gevent and similar async workers are not universal performance solutions.
Can cause subtle application issues. Thoroughly test before production.

## Django production settings

### Cache configuration

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.HerdClient',
        }
    }
}
```

HerdClient prevents cache stampede by randomizing expiration within
a window.

### Multi-cache resilience

Multiple cache servers = higher failure probability. Use twemproxy
with `auto_eject_hosts`:

```yaml
server_failure_limit: 3
server_retry_timeout: 30000
auto_eject_hosts: true
```

Removes failing server from pool for 30s after 3 failures. Transforms
catastrophic outage into ~3 failed requests every 30 seconds.

Handle failed cache ops gracefully: treat `get` failures as cache
misses, ignore failed `set` operations.

### Session engine options

| Engine | Tradeoff |
|---|---|
| `db` (default) | Touches DB every request. Worst for performance. |
| `cache` | Fast. Use if Redis persists to disk. |
| `cached_db` | Works with Memcached. DB fallback on cache restart. |
| `signed_cookies` | Zero server state. Review security implications. |

### Connection persistence

```python
DATABASES = {
    'default': {
        # ... other settings ...
        'CONN_MAX_AGE': 300,  # 5 minutes; None = indefinite
    }
}
```

Default (off) = new connection per request.

### Logging configuration

Log to stderr. Let uWSGI/process manager capture output.

```python
import logging.config
import os
from django.utils.log import DEFAULT_LOGGING

LOGGING_CONFIG = None
LOGLEVEL = os.environ.get('LOGLEVEL', 'info').upper()

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        },
        'django.server': DEFAULT_LOGGING['formatters']['django.server'],
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'django.server': DEFAULT_LOGGING['handlers']['django.server'],
    },
    'loggers': {
        '': {
            'level': 'WARNING',
            'handlers': ['console'],
        },
        'myproject': {
            'level': LOGLEVEL,
            'handlers': ['console'],
            'propagate': False,
        },
        'django.server': DEFAULT_LOGGING['loggers']['django.server'],
    },
})
```
