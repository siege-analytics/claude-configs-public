# Spark Reference

Detailed code templates, Delta Lake operations, and performance tuning patterns. Referenced by the main skill.

## Medallion Architecture Templates

### Bronze (Raw)

Raw data, as received from the source. Minimal transformation — just enough to make it queryable.

```python
def bronze_ingest(spark: SparkSession, source_path: str, table: str) -> None:
    """Load raw files into a bronze Delta table."""
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "false")  # always string in bronze
        .csv(source_path)
    )

    # Add ingestion metadata
    df = (
        df
        .withColumn("_source_file", F.input_file_name())
        .withColumn("_ingested_at", F.current_timestamp())
    )

    (
        df.write
        .format("delta")
        .mode("append")          # never overwrite bronze — it's the audit trail
        .saveAsTable(table)
    )
```

**Bronze rules:**
- All columns are strings (no type coercion at this stage)
- Append-only — never delete or overwrite raw data
- Add `_source_file` and `_ingested_at` metadata columns
- Partitioned by ingestion date or source if the table grows large

### Silver (Clean)

Typed, deduplicated, validated data. This is where data quality enforcement happens.

```python
def silver_clean(spark: SparkSession, bronze_table: str, silver_table: str) -> None:
    """Clean bronze data into silver."""
    bronze = spark.table(bronze_table)

    silver = (
        bronze
        # Type casting
        .withColumn("amount", F.col("amount").cast("decimal(12,2)"))
        .withColumn("contribution_date", F.to_date("contribution_date", "yyyy-MM-dd"))
        # Standardization
        .withColumn("state", F.upper(F.trim("state")))
        .withColumn("zip_code", F.substring(F.trim("zip_code"), 1, 5))
        # Deduplication
        .dropDuplicates(["filing_id", "line_number"])
        # Validation: drop rows that fail basic checks
        .filter(F.col("amount").isNotNull())
        .filter(F.col("contribution_date").isNotNull())
        # Audit
        .withColumn("_cleaned_at", F.current_timestamp())
    )

    (
        silver.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(silver_table)
    )
```

**Silver rules:**
- Correct data types (cast from bronze strings)
- Standardized values (trimmed, uppercased, normalized)
- Deduplicated on a natural key
- Invalid rows filtered with clear criteria
- Schema is enforced and documented

### Gold (Enriched)

Business-level aggregations, joins, and derived data. This is what downstream consumers read.

```python
def gold_donor_summary(spark: SparkSession) -> None:
    """Build the donor summary gold table."""
    donations = spark.table("main.silver.donations")
    committees = spark.table("main.silver.committees")

    summary = (
        donations
        .join(committees, "committee_id", "inner")
        .groupBy("contributor_name", "state", "committee_type")
        .agg(
            F.sum("amount").alias("total_given"),
            F.count("*").alias("donation_count"),
            F.min("contribution_date").alias("first_donation"),
            F.max("contribution_date").alias("last_donation"),
            F.countDistinct("committee_id").alias("unique_committees"),
        )
    )

    (
        summary.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable("main.gold.donor_summary")
    )
```

**Gold rules:**
- Named for the business concept, not the source (`donor_summary`, not `donations_aggregated`)
- Joins are resolved — no foreign keys left for consumers to chase
- Aggregation levels are clear from the table name
- Optimized for read patterns (partitioned by common filter columns)

## Delta Lake Operations

### Merge (Upsert)

```python
from delta.tables import DeltaTable

target = DeltaTable.forName(spark, "main.silver.committees")

(
    target.alias("t")
    .merge(
        source_df.alias("s"),
        "t.committee_id = s.committee_id"
    )
    .whenMatchedUpdateAll()
    .whenNotMatchedInsertAll()
    .execute()
)
```

### Schema Evolution

```python
# Allow new columns to be added automatically
(
    df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")    # full schema replacement
    .saveAsTable(table)
)

# Or for merge operations:
(
    df.write
    .format("delta")
    .mode("append")
    .option("mergeSchema", "true")        # add new columns, keep existing
    .saveAsTable(table)
)
```

### Maintenance

```python
from delta.tables import DeltaTable

table = DeltaTable.forName(spark, "main.silver.donations")

# Compact small files
table.optimize().executeCompaction()

# Z-order for query performance on specific columns
table.optimize().executeZOrderBy(["state", "contribution_date"])

# Remove old versions (default retention: 7 days)
table.vacuum(168)  # hours
```

## Performance Patterns

### Partitioning

```python
# Partition by low-cardinality columns you filter on frequently
(
    df.write
    .format("delta")
    .partitionBy("state")                  # 50 partitions, good
    .saveAsTable("main.silver.donations")
)

# DON'T partition by high-cardinality columns
# .partitionBy("contributor_name")         # millions of tiny files, bad
# .partitionBy("contribution_date")        # 365+ partitions per year, usually too many
```

**Partitioning rules:**
- Fewer than 1000 distinct values
- Queries almost always filter on this column
- Each partition has at least 100MB of data
- If in doubt, don't partition — use Z-ORDER instead

### Broadcast Joins

```python
from pyspark.sql.functions import broadcast

# Small table (< 100MB) joined to large table
enriched = donations.join(broadcast(committees), "committee_id", "left")
```

### Caching

```python
# Cache when a DataFrame is read multiple times
committees = spark.table("main.silver.committees").cache()

# Use it multiple times
result_a = donations.join(committees, ...)
result_b = expenditures.join(committees, ...)

# Unpersist when done
committees.unpersist()
```

### Repartitioning

```python
# Before a write: control output file count
df.repartition(10).write.format("delta").saveAsTable(table)

# Before a join: co-partition on the join key
left = left.repartition(200, "committee_id")
right = right.repartition(200, "committee_id")
joined = left.join(right, "committee_id")

# coalesce (not repartition) to reduce partitions without a full shuffle
df.coalesce(4).write.format("delta").saveAsTable(table)
```

## Testing Spark Jobs

### Test Transform Functions Independently

```python
def test_silver_clean_casts_amount():
    """Silver transform should cast amount to decimal."""
    spark = SparkSession.builder.master("local[1]").getOrCreate()
    input_df = spark.createDataFrame([("100.50",)], ["amount"])

    result = silver_transform(input_df)

    row = result.collect()[0]
    assert row["amount"] == Decimal("100.50")


def test_silver_clean_drops_null_amount():
    """Silver transform should filter out null amounts."""
    spark = SparkSession.builder.master("local[1]").getOrCreate()
    input_df = spark.createDataFrame([(None,), ("50",)], ["amount"])

    result = silver_transform(input_df)

    assert result.count() == 1
```

### Validate Data Quality After Writes

```python
def validate_table(spark: SparkSession, table: str, checks: dict) -> list[str]:
    """Run data quality checks. Returns list of failures."""
    df = spark.table(table)
    failures = []

    if "min_rows" in checks:
        count = df.count()
        if count < checks["min_rows"]:
            failures.append(f"Row count {count} < minimum {checks['min_rows']}")

    if "no_nulls" in checks:
        for col in checks["no_nulls"]:
            null_count = df.filter(F.col(col).isNull()).count()
            if null_count > 0:
                failures.append(f"{col} has {null_count} nulls")

    if "unique" in checks:
        for col in checks["unique"]:
            total = df.count()
            distinct = df.select(col).distinct().count()
            if total != distinct:
                failures.append(f"{col} has {total - distinct} duplicates")

    return failures
```

## SparkSQL Reference

### Session and Catalog

```sql
-- Use fully qualified names: catalog.schema.table
SELECT * FROM main.silver.donations LIMIT 10;

-- Set the default catalog/schema for the session
USE CATALOG main;
USE SCHEMA silver;

-- Show what's available
SHOW CATALOGS;
SHOW SCHEMAS IN main;
SHOW TABLES IN main.silver;

-- Table metadata
DESCRIBE EXTENDED main.silver.donations;
SHOW CREATE TABLE main.silver.donations;
```

### Delta Lake SQL Operations

```sql
-- Time travel: query a table as of a previous version
SELECT * FROM main.silver.donations VERSION AS OF 5;
SELECT * FROM main.silver.donations TIMESTAMP AS OF '2024-03-15 00:00:00';

-- Merge (upsert): insert new, update existing
MERGE INTO main.gold.committees AS target
USING staging.new_committees AS source
    ON target.committee_id = source.committee_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

-- Optimize: compact small files and co-locate related data
OPTIMIZE main.silver.donations ZORDER BY (committee_id, contribution_date);

-- Vacuum: remove old files no longer referenced by any version
VACUUM main.silver.donations RETAIN 168 HOURS;

-- History
DESCRIBE HISTORY main.silver.donations;
```


# Addendum to coding/spark/reference.md — High-Performance Spark

Append this section after the existing Delta / medallion content.

Draws from:
- **Holden Karau et al. — *High Performance Spark*** — the tuning canon
- **Jacek Laskowski — "Mastering Apache Spark SQL" gitbook** (jaceklaskowski.gitbooks.io) — deepest public internals walkthrough
- **Sandy Ryza et al. — *Advanced Analytics with Spark* 2nd ed** — pattern catalog

---

## The two bottlenecks you actually hit

Every Spark performance problem is eventually one of these:

1. **Shuffle** — data crossing executors (join, groupBy, distinct, repartition). Disk I/O + network.
2. **Skew** — one partition has 10x the data of others; one task stalls while others finish.

Everything else (CPU, JVM GC, spill) is downstream of these two.

## Inspect before tuning

| Tool | Use |
|---|---|
| Spark UI — Stages tab | Per-stage duration, shuffle read/write, skew |
| Spark UI — SQL tab | Physical plan with row counts and timings |
| `df.explain(mode="formatted")` | Plan from code |
| `df.explain(mode="cost")` | CBO estimates (3.2+) |
| `spark.sql.adaptive.enabled=true` | Let AQE handle skew automatically |

Never "optimize" without a before-number. Most changes that "feel faster" don't move the total wall-clock.

## Adaptive Query Execution (AQE)

Enable by default in modern Spark (3.0+):

```python
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
```

AQE at runtime:
- Coalesces too-small post-shuffle partitions (reduces task overhead)
- Detects skewed partitions and splits them
- Switches join strategy based on actual row counts

Before AQE, these required manual hints. AQE handles 80% of cases correctly; the rest need targeted intervention.

## Skew — the most common silent killer

Symptoms:
- Spark UI shows one task taking 10x the median
- Stage doesn't finish because it's waiting on one straggler
- OOM in one executor while others are idle

Diagnose:
```python
df.groupBy("join_key").count().orderBy(F.desc("count")).show()
# If one key has 100x the rows of the median, that's skew
```

Fixes, in order of cost:

### 1. Let AQE handle it

```python
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
```

Often sufficient. Try this first.

### 2. Salt the hot keys

```python
from pyspark.sql import functions as F

# Before join, add a random salt to hot keys
left_salted = left.withColumn(
    "salted_key",
    F.concat(F.col("key"), F.lit("_"), (F.rand() * 10).cast("int"))
)
# Explode the right side so each salt variant matches
right_exploded = right.withColumn(
    "salt", F.explode(F.array(*[F.lit(i) for i in range(10)]))
).withColumn(
    "salted_key",
    F.concat(F.col("key"), F.lit("_"), F.col("salt"))
)
result = left_salted.join(right_exploded, "salted_key")
```

Trade-off: 10x data on the small side, but the skew is broken.

### 3. Broadcast the small side

If one side of a join is <10 GB:

```python
from pyspark.sql.functions import broadcast

result = large_df.join(broadcast(small_df), "key")
```

Small table ships to every executor; no shuffle. Broadcasting eliminates skew entirely because the "small" side is fully available to every partition.

### 4. Partition-by-key explicitly

If the same skewed join runs repeatedly, write the small side partitioned:

```python
small_df.write.mode("overwrite").partitionBy("key").saveAsTable("staging.small_partitioned")
```

Subsequent reads of a single key are O(1) file lookups.

## Shuffle — reduce it

Shuffles happen at:
- `join` (unless one side is broadcast)
- `groupBy` (unless the data is already keyed correctly)
- `distinct` / `dropDuplicates`
- `repartition` (obviously)
- Window functions with PARTITION BY

### Tricks

**Bucket tables on the join key.** Co-located data skips the shuffle:

```python
df.write.bucketBy(200, "user_id").sortBy("user_id").saveAsTable("users_bucketed")
# Joins on user_id between two tables bucketed the same way: no shuffle
```

Constraint: both sides must be bucketed identically. Works for Hive-style tables; less relevant for Delta (which uses liquid clustering).

**Pre-aggregate before shuffle.** `groupBy + sum` vs. `aggregate inside partition, then groupBy the local sums`:

```python
# Naive
df.groupBy("region").agg(F.sum("amount"))

# With pre-aggregation (manual — usually Catalyst does this automatically)
# Only relevant if you're using RDD or custom aggregations
```

Catalyst usually does this for built-in aggregates. Custom UDAFs miss out; prefer built-ins.

**Use `reduceByKey` over `groupByKey`.** `reduceByKey` combines per-partition before shuffle; `groupByKey` ships all values. RDD-era advice — in the DataFrame world this maps to preferring built-in aggregates over `collect_list + post-process`.

## Caching and persistence

Cache is NOT free:
- Occupies memory (pressures other operations)
- Costs time to compute the first read
- Becomes stale if the source changes

Use cache only when:
- The same DataFrame is used >2 times in the job
- The computation is expensive (heavy joins, large filters)
- You've verified the plan (check Spark UI's Storage tab to confirm caching actually happened)

```python
df = heavy_computation()
df.cache()
df.count()  # materialize the cache
# subsequent uses of df now hit cache
```

Levels (from `StorageLevel`):
- `MEMORY_ONLY` — fastest; OOM if it doesn't fit
- `MEMORY_AND_DISK` — default; spills to disk. Use this.
- `MEMORY_AND_DISK_SER` — serialized; smaller but slower to deserialize. Rarely worth it with modern Spark.
- `DISK_ONLY` — not faster than recomputing unless the computation is very expensive

Always `unpersist()` when done to reclaim memory.

## File layout — Parquet/Delta tuning

| Setting | Why | Target |
|---|---|---|
| Parquet row group size | Larger = better compression, more scan overhead | 128 MB – 1 GB |
| File size | Too small = metadata overhead; too big = can't parallelize | 100 MB – 1 GB per file |
| Column encoding | Dictionary encoding for low-cardinality strings | Default is usually right |

For Delta tables: run `OPTIMIZE` (or enable predictive optimization) to compact small files. The magic threshold is `spark.databricks.delta.optimize.maxFileSize` — default 1 GB, often fine.

## Columnar projection and predicate pushdown

Spark's Catalyst optimizer pushes projection (column selection) and predicates (WHERE clauses) into the file reader. This means:

```python
# BAD — reads all columns, then drops
df = spark.table("wide_table").drop("huge_unused_col1", "huge_unused_col2")
df.filter(F.col("date") > "2024-01-01")

# GOOD — Catalyst pushes the select and filter into Parquet
df = spark.table("wide_table").select("date", "id", "amount").filter(F.col("date") > "2024-01-01")
```

Parquet reads only the columns and row groups that survive. On a 200-column wide table this is a 10-50x I/O reduction.

Gotchas:
- Predicates on derived columns (UDF outputs) can't be pushed down
- Predicates on partition columns are pushed at partition-pruning time (before file open) — always partition-or-cluster on common filter columns

## UDFs — last resort

Python UDFs crash Catalyst optimization (black-box function). Order of preference:

1. **Built-in functions** (`pyspark.sql.functions.*`)
2. **SQL expressions via `F.expr("...")`**
3. **Pandas UDF (vectorized, `@pandas_udf`)** — 10-100x faster than scalar UDF
4. **Scalar Python UDF** — last resort

```python
# Pandas UDF — vectorized
from pyspark.sql.functions import pandas_udf

@pandas_udf("double")
def adjust_amount(s: pd.Series) -> pd.Series:
    return s * 1.1
```

If you must use a scalar UDF, at least register it so Catalyst can eliminate duplicate calls:

```python
spark.udf.register("adjust_amount", adjust_amount)
```

## Cluster sizing heuristics (Karau)

| Workload | Executor memory | Cores | Count |
|---|---|---|---|
| Interactive queries | 16-32 GB | 4-8 | "enough to fit the hot data" |
| ETL (shuffle-heavy) | 32-64 GB | 4-8 | partition_count / 4 |
| Heavy-iteration ML | 64 GB+ | 16 | a few large beats many small |
| Streaming | 16 GB | 4-8 | one per ingest partition + headroom |

Rules of thumb:
- More than 5 cores per executor causes HDFS throughput to collapse (per Cloudera benchmarks, 5 cores/executor is the knee)
- Leave ~10% of node memory for OS and YARN / Kubernetes overhead
- Start small, scale on OOM. "Big enough to be safe" costs ~4x too much.

## Common performance mistakes

| Pattern | Impact | Fix |
|---|---|---|
| `collect()` on large DataFrame | Driver OOM | `write` to storage or `foreachPartition` |
| `cache()` without `.count()` | Cache never materializes | Trigger an action |
| `cache()` on transient DataFrame | Memory pressure | `unpersist()` explicitly |
| `toPandas()` on big DataFrame | Driver OOM | Filter first; `mapInPandas` / `applyInPandas` for grouped |
| UDF for what a built-in does | Catalyst opaque, slow | Use `F.*` functions |
| Repartitioning unnecessarily | Unneeded shuffle | Let AQE coalesce; or `coalesce()` instead of `repartition()` for reducing partitions |
| Wide table without predicate pushdown | Full scan | Partition / cluster on filter columns |
| Shuffle partition count stuck at 200 | Under-parallelized on large data | `spark.sql.shuffle.partitions=1000+` for big shuffles |
| Small files (< 10 MB each) | Metadata overhead kills reads | `OPTIMIZE` (Delta) or `coalesce(N)` before write |
| `checkpoint()` when `cache()` would do | Disk overhead | `cache()` unless you need lineage truncation |

## Streaming considerations

If you're writing Structured Streaming:

- Enable state store cleanup: set a reasonable watermark and don't retain unbounded state
- Use `maxFilesPerTrigger` (file source) or `maxOffsetsPerTrigger` (Kafka) to bound per-batch size
- Checkpoint to durable storage (S3 / ADLS with HDFS-compatible guarantees), not local disk
- The UI's "Input Rate" and "Processing Rate" tell you when you're falling behind

## References

- **Holden Karau, Rachel Warren — *High Performance Spark*** (tuning canon)
- **Jacek Laskowski** — jaceklaskowski.gitbooks.io/mastering-spark-sql (deepest public internals)
- **Sandy Ryza, Uri Laserson, Sean Owen, Josh Wills** — *Advanced Analytics with Spark* 2nd ed
- **Databricks engineering blog** — databricks.com/blog (AQE, Photon, Delta performance posts)
- **Spark UI's SQL and Stages tabs** — the only reliable source of truth
