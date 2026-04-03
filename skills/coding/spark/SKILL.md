---
name: spark
description: PySpark job patterns, Delta Lake conventions, and medallion architecture. Covers session setup, transform design, testing, and performance tuning.
---

# Spark Jobs

## When to Use This Skill

When writing PySpark jobs, Delta Lake pipelines, or Spark-based ETL. This skill covers job structure, transform patterns, and the medallion architecture (bronze/silver/gold).

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

### Spark Connect (Remote)

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .remote("sc://spark-server:15002")
    .appName("my_pipeline")
    .getOrCreate()
)
```

### Local Development

```python
spark = (
    SparkSession.builder
    .master("local[*]")
    .appName("my_pipeline_dev")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .getOrCreate()
)
```

### With Unity Catalog

```python
spark = (
    SparkSession.builder
    .remote("sc://spark-server:15002")
    .config("spark.sql.defaultCatalog", "main")
    .appName("my_pipeline")
    .getOrCreate()
)

# Use fully qualified table names
df = spark.table("main.silver.donations")
```

## Job Structure

Every Spark job should follow this pattern:

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
    """Get or create the Spark session."""
    return (
        SparkSession.builder
        .remote("sc://spark-server:15002")
        .appName("my_job")
        .getOrCreate()
    )


def extract(spark: SparkSession) -> DataFrame:
    """Read source data."""
    return spark.table("main.bronze.raw_filings")


def transform(df: DataFrame) -> DataFrame:
    """Apply business logic."""
    return (
        df
        .filter(F.col("amount") > 0)
        .withColumn("year", F.year("contribution_date"))
        .withColumn("amount_bucket", F.when(F.col("amount") < 200, "small")
                                      .when(F.col("amount") < 2000, "medium")
                                      .otherwise("large"))
    )


def load(df: DataFrame) -> None:
    """Write results."""
    (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable("main.silver.donations_classified")
    )


def main():
    spark = get_spark()
    raw = extract(spark)
    result = transform(raw)
    load(result)
    spark.stop()


if __name__ == "__main__":
    main()
```

**Why this structure:**
- `extract` / `transform` / `load` are independently testable
- `transform` takes and returns a DataFrame — pure function, no side effects
- `main` is the composition root — the only function that knows about Spark sessions and storage

## Medallion Architecture

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

# Bad: mutable reassignment obscures what happened
df = df.filter(...)
df = df.withColumn(...)
df = df.groupBy(...)
df = df.orderBy(...)
```

### Named Intermediate DataFrames

When a pipeline has distinct stages, name them.

```python
# Each name tells you what the data represents at that stage
raw_filings = spark.table("main.bronze.filings")

parsed_filings = (
    raw_filings
    .withColumn("amount", F.col("amount").cast("decimal(12,2)"))
    .withColumn("date", F.to_date("date_str", "MM/dd/yyyy"))
)

valid_filings = (
    parsed_filings
    .filter(F.col("amount") > 0)
    .filter(F.col("date").isNotNull())
)

enriched_filings = (
    valid_filings
    .join(committees, "committee_id", "left")
    .join(zip_to_district, "zip_code", "left")
)
```

### Conditional Columns

```python
# Simple binary
df.withColumn("is_large", F.col("amount") >= 2000)

# Multi-way classification
df.withColumn(
    "donor_tier",
    F.when(F.col("total_given") >= 100000, "major")
     .when(F.col("total_given") >= 10000, "mid")
     .when(F.col("total_given") >= 1000, "grassroots")
     .otherwise("small")
)

# Coalesce for fallback values
df.withColumn("display_name", F.coalesce("preferred_name", "legal_name", F.lit("Unknown")))
```

### UDFs: Last Resort

User-defined functions (UDFs) break Spark's optimizer. Avoid them when possible.

```python
# Bad: Python UDF — serializes every row to Python and back
@F.udf("string")
def clean_name(name):
    return name.strip().upper() if name else None

# Good: built-in functions — runs natively in the JVM
df.withColumn("clean_name", F.upper(F.trim("name")))
```

**When UDFs are acceptable:**
- Complex business logic that genuinely cannot be expressed with built-in functions
- Use `pandas_udf` (vectorized) over regular UDF — 10-100x faster
- Always test with `.limit(100)` first to verify correctness before running on full data

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

## Performance

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

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Collecting large DataFrames | `df.collect()` pulls all data to the driver, causing OOM | Use `.limit()`, `.take()`, or write to storage |
| Counting inside a loop | `df.count()` triggers a full scan every time | Count once, store the result |
| Wide shuffle operations | `groupBy` on high-cardinality keys creates millions of shuffle partitions | Reduce cardinality or pre-partition |
| Python UDFs in hot paths | Serialization overhead per row | Use built-in functions or `pandas_udf` |
| Not caching reused DataFrames | Same computation runs multiple times | `.cache()` before reuse, `.unpersist()` after |
| Overwriting bronze tables | Destroys the audit trail | Bronze is always append-only |
| Too many small partitions | Slow reads, metadata overhead | `OPTIMIZE` or `coalesce` before writing |

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
