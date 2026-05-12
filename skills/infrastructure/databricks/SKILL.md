---
name: databricks
description: "Databricks platform conventions — Unity Catalog, Delta, job orchestration, and cost. TRIGGER: Databricks notebook, job config, DLT pipeline, Unity Catalog permissioning, cluster sizing, or workspace setup."
user-invocable: false
paths: "**/notebooks/**/*.py,**/*.ipynb,**/bundle.yml,**/databricks.yml,**/jobs/**,**/pipelines/**"
---

# Databricks

Apply when working with the Databricks platform — notebooks, jobs, DLT pipelines, Unity Catalog, clusters. See [reference.md](reference.md) for DAB (Databricks Asset Bundle) templates, DLT patterns, and cost recipes.

Draws from:
- **Databricks Well-Architected Framework** (databricks.com/blog — 2024/25 refresh) — current canonical guide
- **Jaiswal & Haelen — *Delta Lake: Up and Running* (O'Reilly, 2023)** — Delta 3.x features
- **Jules Damji (Databricks) blog posts** — medallion architecture originator
- **Matei Zaharia's original papers** — for understanding Spark / Delta internals

> *Learning Spark 2nd ed* (2020) is dated (pre-Photon GA, pre-liquid clustering). Don't treat as current.

## The five pillars (Well-Architected Framework)

1. **Data governance** — Unity Catalog is the answer; Hive metastore is legacy
2. **Reliability** — Delta + DLT + jobs with retries; not notebooks-in-cron
3. **Performance** — Photon, liquid clustering, adaptive query execution
4. **Cost** — job compute over all-purpose compute; auto-terminate; spot for non-critical
5. **Operational excellence** — DABs for IaC; no clicking through the UI for prod

Each section below applies one of these.

## Unity Catalog discipline

Three-level namespace is non-negotiable in new workspaces:

```
<catalog>.<schema>.<table>
main.bronze.raw_filings
main.silver.cleaned_filings
prod.gold.donor_aggregates
```

| Catalog | Purpose |
|---|---|
| `main` | Dev / scratch |
| `prod` | Production tables — RBAC locked down |
| `sandbox_<user>` | Personal scratch spaces |

Managed vs external tables:
- **Managed** (default): Databricks owns the files. `DROP TABLE` deletes data. Use for silver/gold.
- **External**: Files live at a known `LOCATION`. `DROP TABLE` leaves files. Use for bronze (audit trail) and anything you need raw access to.

**Always use managed** unless you have a specific reason for external. External tables in Unity Catalog also require storage credentials and external locations configured up front.

## Medallion architecture (Jules Damji's canonical pattern)

```
BRONZE — raw ingest, append-only, never overwrite
  ↓
SILVER — cleaned, validated, schemafied; the "source of truth"
  ↓
GOLD — business-aggregated, reporting-ready, optimized for query
```

Rules:
- Bronze = raw + ingest metadata (timestamp, source file); never transform in-place
- Silver = deduplicated, null-handled, typed; the layer where quality checks live
- Gold = read-optimized (liquid clustered or Z-ordered on query filters); can be partitioned by date for time-series

## Delta Lake — modern feature set

Use all of these when available (DBR 14+):

| Feature | Benefit | Use when |
|---|---|---|
| **Liquid clustering** | Replaces partitioning + Z-ORDER | Any table with evolving query patterns |
| **Deletion vectors** | Soft deletes without rewriting data | High-cardinality updates |
| **Column mapping** | Rename/drop columns without file rewrite | Schema evolution |
| **Change data feed (CDF)** | Track row-level changes | Downstream CDC to silver/gold |
| **Predictive optimization** | Auto-OPTIMIZE and VACUUM | Always on for managed tables |

```sql
-- Modern table creation (DBR 15+)
CREATE TABLE main.silver.donations (
    id BIGINT,
    contributor_id STRING,
    amount DECIMAL(10, 2),
    contribution_date DATE,
    cycle INT
)
CLUSTER BY (contribution_date, cycle)
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.feature.allowColumnDefaults' = 'supported'
);
```

## Partitioning — prefer liquid clustering

- **Partition by date** only if: (a) you're on an older runtime, (b) you need explicit partition isolation for compliance, or (c) you always query by date.
- **Liquid clustering** otherwise: `CLUSTER BY (col1, col2)`. Adapts to query patterns.
- **Never partition on high-cardinality columns.** Classic mistake: partitioning by `user_id`.

## Jobs over notebooks-in-cron

Production workloads are **jobs**, not notebooks on a schedule.

```yaml
# databricks.yml — Databricks Asset Bundle
resources:
  jobs:
    donor_ingest:
      name: donor-ingest-daily
      tasks:
        - task_key: extract
          python_wheel_task:
            package_name: myproject
            entry_point: donor_ingest
          job_cluster_key: small_job_cluster
      job_clusters:
        - job_cluster_key: small_job_cluster
          new_cluster:
            spark_version: 15.4.x-scala2.12
            node_type_id: i3.xlarge
            num_workers: 2
            data_security_mode: SINGLE_USER
      schedule:
        quartz_cron_expression: "0 0 6 * * ?"
        timezone_id: America/Chicago
```

- **Python wheel tasks** over notebook tasks — tested, versioned, re-runnable
- **Job clusters** over all-purpose clusters — auto-terminate, cheaper
- **DBR versions** pinned (`15.4.x-scala2.12`) — don't float the runtime
- **Deploy via `databricks bundle deploy`** — no clicking in the UI

## DLT (Delta Live Tables) — when declarative helps

Use DLT when:
- You have a multi-step pipeline with clear bronze → silver → gold stages
- Data quality expectations are explicit (column must be non-null, value must be in range)
- You want automatic retry, backfill, and lineage

Don't use DLT when:
- The pipeline is a single query (a job is simpler)
- You need fine-grained control over the physical layout (DLT abstracts this)

Example:
```python
import dlt
from pyspark.sql.functions import col

@dlt.table(name="bronze_donations")
def bronze_donations():
    return spark.read.format("cloudFiles").option("cloudFiles.format", "json").load(INPUT_PATH)

@dlt.table(name="silver_donations")
@dlt.expect_or_drop("positive_amount", "amount > 0")
@dlt.expect_or_fail("has_contributor", "contributor_id IS NOT NULL")
def silver_donations():
    return (
        dlt.read("bronze_donations")
        .filter(col("amount") > 0)
        .withColumn("year", col("contribution_date").cast("int"))
    )
```

`expect_or_drop` drops bad rows (logged). `expect_or_fail` crashes the pipeline. Pick deliberately.

## Cost discipline

Single biggest lever: **job compute vs. all-purpose compute**. All-purpose clusters are 2-3x more expensive per DBU and don't auto-terminate. For any workload that doesn't need interactive access:

```yaml
# good
new_cluster:
  spark_version: 15.4.x-scala2.12
  node_type_id: i3.xlarge
  num_workers: 2
```

Other levers:
- **Photon** — enable for SQL-heavy workloads (`runtime_engine: PHOTON`). Usually pays for itself in runtime reduction.
- **Spot instances** for non-critical workloads: `first_on_demand: 1` + the rest spot.
- **Auto-terminate** on all-purpose clusters: `autotermination_minutes: 30`.
- **Right-size nodes.** Start small; scale up only after OOM. The default "cluster for your convenience" is usually 3-4x too large.
- **Serverless SQL warehouses** for ad-hoc BI queries — cheaper than a dedicated cluster sitting idle.

## Security & governance

- **Single-user access mode** for job clusters running under a service principal
- **Shared access mode** only for interactive clusters where multiple users need RBAC enforcement
- **Secrets** in Databricks Secret Scopes, never in notebooks; reference as `dbutils.secrets.get(scope, key)`
- **Service principals** for all automated workloads — no PAT tokens in production code
- **Table ACLs** via Unity Catalog: `GRANT SELECT ON main.prod.donors TO 'data-analysts'`

## Photon — when to enable

Rule of thumb: enable Photon for any workload that's >50% SQL or DataFrame operations. Skip Photon for:
- Heavy Python UDF workloads (Photon doesn't accelerate Python code)
- Small workloads (<1 min — overhead doesn't amortize)
- Streaming workloads with very low throughput

Photon adds ~15-20% to DBU cost but typically cuts runtime 2-3x on warehouse-pattern queries.

## Common mistakes

| Mistake | Impact | Fix |
|---|---|---|
| Hive metastore in new workspace | No governance, no lineage | Migrate to Unity Catalog |
| All-purpose cluster in cron | 2-3x cost, no termination | Job cluster |
| `.write.mode("overwrite")` on bronze | Loses audit trail | Append to bronze; overwrite in silver |
| Partitioning on user_id | Thousands of tiny partitions | Liquid clustering |
| Notebooks scheduled directly | No version control | Python wheel task |
| `display()` in scheduled notebook | No output surface, wastes compute | Remove; use logging |
| `.collect()` on large DataFrame | Driver OOM | `.write` to storage instead |
| `cache()` without a plan | Memory pressure | Explicit `persist(StorageLevel.MEMORY_AND_DISK)` with rationale |
| Not running OPTIMIZE | File fragmentation kills reads | Predictive optimization or scheduled `OPTIMIZE` |
| One runtime across all jobs | Breaks on DBR upgrade | Pin per-job; rotate gradually |

## References

- **Databricks Well-Architected Framework** — databricks.com/blog (2024/25 posts)
- **Jaiswal & Haelen** — *Delta Lake: Up and Running* (O'Reilly, 2023)
- **Jules Damji's posts** — databricks.com/blog/author/jules-damji
- **Zaharia et al. — Spark, Delta Lake papers** — for first-principles understanding
- **Databricks docs** — docs.databricks.com (primary current reference)

## Attribution Policy

See [`output`](../../_output-rules.md). NEVER include AI or agent attribution.
