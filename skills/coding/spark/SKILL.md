---
name: spark
description: PySpark job patterns, Delta Lake, and medallion architecture. Covers when to use Spark, job structure, transform design, and performance.
routed-by: coding-standards
---

# Spark Jobs

## Companion shelves

Spark on Databricks is JVM underneath — the cost model and failure modes are JVM. Load these for code-level idioms:
- [`shelves/languages/effective-java/`](../../shelves/languages/effective-java/SKILL.md) — equals/hashCode for Dataset[T], immutability, exception handling in UDFs.
- [`shelves/languages/effective-kotlin/`](../../shelves/languages/effective-kotlin/SKILL.md) — null-safety idioms (≈ Scala Option/Either).
- [`shelves/systems-architecture/data-intensive/`](../../shelves/systems-architecture/data-intensive/SKILL.md) — partitioning, shuffle, replication theory.

Always-on: [`_jvm-rules.md`](../../_jvm-rules.md) is loaded when Spark/JVM code is touched.
For Scala notebooks specifically, see also [`coding/scala-on-spark/`](../scala-on-spark/SKILL.md).

Apply these patterns when writing PySpark jobs, Delta Lake pipelines, or Spark-based ETL. See [reference.md](reference.md) for full code templates, Delta operations, and performance tuning.

## When to Use Spark vs. Alternatives

| Data Size | Complexity | Use |
|-----------|-----------|-----|
| < 1M rows, fits in memory | Simple transforms | Pandas or DuckDB |
| < 10M rows, single machine | SQL-heavy, joins | PostgreSQL or DuckDB |
| 10M+ rows or growing | Multi-step pipeline | Spark |
| Any size, real-time | Stream processing | Spark Structured Streaming |
| Any size, one-off exploration | Ad hoc analysis | Start with DuckDB, graduate to Spark |

Spark has startup overhead. Don't use it for jobs that finish in seconds on a single machine.

## Session Setup

```python
# Spark Connect (remote)
spark = SparkSession.builder.remote("sc://spark-server:15002").appName("my_pipeline").getOrCreate()

# Local development
spark = SparkSession.builder.master("local[*]").appName("my_pipeline_dev").getOrCreate()

# With Unity Catalog
spark = (
    SparkSession.builder
    .remote("sc://spark-server:15002")
    .config("spark.sql.defaultCatalog", "main")
    .appName("my_pipeline")
    .getOrCreate()
)
```

## Job Structure

Every Spark job should follow extract/transform/load:

```python
"""
One-line description of what this job does.

Reads from: catalog.schema.input_table
Writes to:  catalog.schema.output_table
Schedule:   daily / hourly / on-demand
"""

from pyspark.sql import SparkSession, DataFrame
import pyspark.sql.functions as F


def get_spark() -> SparkSession:
    return SparkSession.builder.remote("sc://spark-server:15002").appName("my_job").getOrCreate()


def extract(spark: SparkSession) -> DataFrame:
    """Read source data."""
    return spark.table("main.bronze.raw_filings")


def transform(df: DataFrame) -> DataFrame:
    """Apply business logic."""
    return (
        df
        .filter(F.col("amount") > 0)
        .withColumn("year", F.year("contribution_date"))
    )


def load(df: DataFrame) -> None:
    """Write results."""
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("main.silver.result")


def main():
    spark = get_spark()
    raw = extract(spark)
    result = transform(raw)
    load(result)
    spark.stop()
```

**Why this structure:** `transform` takes and returns a DataFrame (pure, testable). `main` is the composition root.

## Medallion Architecture

Three tiers, each with distinct rules:

| Tier | Purpose | Write Mode | Schema |
|------|---------|-----------|--------|
| **Bronze** | Raw, as received | Append-only (never overwrite) | All strings, add `_source_file` and `_ingested_at` |
| **Silver** | Typed, deduped, validated | Overwrite | Correct types, standardized values, null-filtered |
| **Gold** | Business-level joins and aggregations | Overwrite | Named for the concept, joins resolved |

See [reference.md](reference.md) for full bronze/silver/gold code templates.

## Transform Patterns

### Chained Transforms

Always chain DataFrame operations. Never reassign to the same variable name in sequence.

```python
# Good: one readable chain
result = (
    df
    .filter(F.col("state").isin(target_states))
    .withColumn("fiscal_year", fiscal_year_udf("contribution_date"))
    .groupBy("fiscal_year", "state")
    .agg(F.sum("amount").alias("total"))
    .orderBy("fiscal_year", "state")
)
```

### Named Intermediate DataFrames

When a pipeline has distinct stages, name them so each name tells you what the data represents:

```python
raw_filings = spark.table("main.bronze.filings")
parsed_filings = raw_filings.withColumn("amount", F.col("amount").cast("decimal(12,2)"))
valid_filings = parsed_filings.filter(F.col("amount") > 0)
enriched_filings = valid_filings.join(committees, "committee_id", "left")
```

### Conditional Columns

```python
df.withColumn("is_large", F.col("amount") >= 2000)

df.withColumn(
    "donor_tier",
    F.when(F.col("total_given") >= 100000, "major")
     .when(F.col("total_given") >= 10000, "mid")
     .otherwise("small")
)

df.withColumn("display_name", F.coalesce("preferred_name", "legal_name", F.lit("Unknown")))
```

### UDFs: Last Resort

UDFs break Spark's optimizer. Prefer built-in functions. When unavoidable, use `pandas_udf` (vectorized) over regular UDF.

## Performance Rules

| Rule | Why |
|------|-----|
| Partition by low-cardinality columns (<1000 values) | High-cardinality = millions of tiny files |
| Use `broadcast()` for small dimension tables (<100MB) | Avoids shuffle |
| Cache DataFrames read multiple times, `.unpersist()` after | Avoids recomputation |
| Use `coalesce(N)` to reduce partitions, `repartition(N)` to increase | coalesce avoids shuffle |
| Never `.collect()` large DataFrames | Pulls everything to driver, OOM risk |
| Never count inside a loop | Full scan every call |

See [reference.md](reference.md) for detailed performance patterns with code examples.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Collecting large DataFrames | Use `.limit()`, `.take()`, or write to storage |
| Python UDFs in hot paths | Use built-in functions or `pandas_udf` |
| Not caching reused DataFrames | `.cache()` before reuse |
| Overwriting bronze tables | Bronze is always append-only |
| Too many small partitions | `OPTIMIZE` or `coalesce` before writing |

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
