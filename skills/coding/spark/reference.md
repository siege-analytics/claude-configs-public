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
