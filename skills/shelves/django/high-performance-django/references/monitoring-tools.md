# Production Monitoring Tools Reference

Extracted from High Performance Django, Chapter 5 (The Launch).

## Per-tier monitoring

### htop (app servers)

Watch for:
- Load average exceeding CPU core count
- Python processes > 300MB RES (memory leak candidate)
- Swap usage (add RAM if swapping)

### uwsgitop (uWSGI workers)

```bash
pip install uwsgitop
uwsgitop 127.0.0.1:1717
```

Displays: requests served, average response time, bytes transferred,
busy/idle status per worker.

Raw data: `uwsgi --connect-and-read 127.0.0.1:1717`

Target: average response time under 1 second. If all workers busy
with CPU/RAM available, add workers. If no resources, add servers.

### Varnish tools

**varnishstat:** cache hit rate and cumulative event counts. Note: the
displayed hit rate can be deceiving because passes are not counted as
misses.

**varnishhist:** response time histograms. `|` = cache hits, `#` = misses.
Logarithmic scale: 1e-3 = 1ms, 1e0 = 1 second.

**varnishtop filters:**

| Command | Shows |
|---|---|
| `varnishtop -b -i "BereqURL"` | Cache misses by URL |
| `varnishtop -c -i "ReqURL"` | Cache hits by URL |
| `varnishtop -i ReqMethod` | Request methods |
| `varnishtop -c -i RespStatus` | Response status codes |
| `varnishtop -I "ReqHeader:User-Agent"` | User agents |

**varnishlog with filtering:**

```bash
varnishlog -b -g request -q "BerespStatus eq 404" \
    -i "BerespStatus,BereqURL"
```

Target: read-heavy sites should achieve 90%+ hit rate. Verify expected
URLs are cached. Identify top URLs bypassing cache for VCL optimization.

### Celery monitoring

- `celery inspect` -- point-in-time activity snapshot
- `celery events` -- real-time activity stream
- **Flower** -- web interface with control and time-series graphs

Watch: all tasks completing, queue growth vs worker capacity.

### memcache-top

```bash
curl -L http://git.io/h85t > memcache-top
chmod +x memcache-top
./memcache-top --instances=10.0.0.1,10.0.0.2,10.0.0.3
```

Target: hit rate in the 90s. Balanced connections across servers.
Operations under 2ms average.

### PostgreSQL monitoring

**pg_top:**

```bash
sudo -u postgres pg_top -d <database>
```

Press R for per-table stats, X for per-index stats, E with PID to
EXPLAIN queries in-place.

**pg_stat_statements:**

Enable in `postgresql.conf`:

```
shared_preload_libraries = 'pg_stat_statements'
```

Then: `psql -c "CREATE EXTENSION pg_stat_statements;"`

Find slowest queries:

```sql
SELECT
    calls,
    round((total_time/1000/60)::numeric, 2) as total_minutes,
    round((total_time/calls)::numeric, 2) as average_ms,
    query
FROM pg_stat_statements
ORDER BY 2 DESC
LIMIT 100;
```

Better psql output: `psql -P border=2 -P format=wrapped -P linestyle=unicode`

**pgBadger:** HTML reports from query logs for offline analysis.

Watch: connection count under max, flag "Idle in transaction" > expected
duration, queries > 1 second, iowait near zero.

### MySQL monitoring

**mytop:** `apt install mytop`. Press `e` to EXPLAIN by query ID.

**pt-query-digest** (Percona Toolkit): MySQL equivalent to
pg_stat_statements.

## Monitoring stack overview

| Layer | What to collect | Tool |
|---|---|---|
| Application metrics | Response time, query count per view | django-statsd + Graphite + Grafana |
| Server resources | CPU, RAM, disk, network | Collectd/Diamond + Graphite |
| Alerting | Thresholds on metrics | Nagios, Cabot, PagerDuty |
| Log aggregation | Request logs, slow queries | ELK (ElasticSearch + Kibana + Logstash) |
| Error tracking | Tracebacks, frequency, trends | Sentry |

## Error reporting

Do NOT use Django's default email-on-traceback:
- High-traffic pages DoS mail servers
- Trigger blacklisting
- No frequency tracking or trending
- Email unsuitable for incident management

Use Sentry: first occurrence triggers email, rest aggregated. Dashboard
tracks errors. Supports JavaScript client-side errors.
