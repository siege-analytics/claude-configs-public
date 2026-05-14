# Sedona Partitioning Strategies

How Sedona partitions data for spatial joins, and when to override the default.

## The default — KDB-tree

For spatial joins, Sedona's default partitioner is KDB-tree:

1. Sample both input DataFrames.
2. Build a balanced KDB-tree from the bounding boxes.
3. Repartition both sides into the tree's leaf partitions.
4. Run a local spatial join within each matched partition pair.

Properties:
- Balanced — each partition gets approximately equal row count.
- Adapts to data distribution — skewed datasets get more partitions in dense regions.
- One-pass — no global shuffle beyond the initial repartition.

For most workloads, KDB-tree is correct and you don't need to think about it.

## When to switch to quad-tree

`sedona.global.partitionnum` and `spark.sedona.join.gridtype` control the partitioner:

```python
sedona.conf.set("spark.sedona.join.gridtype", "quadtree")
sedona.conf.set("spark.sedona.global.partitionnum", "256")
```

Quad-tree:
- Pre-defined regular grid (recursively subdivided where dense).
- Better when data has very high spatial autocorrelation (clusters in specific regions).
- Worse when data is uniform — wastes partitions on empty quadrants.

Use case: dense urban points with mostly-empty rural areas. KDB-tree might over-partition the dense region; quad-tree keeps the dense region in fewer larger partitions.

## Broadcast join — when one side is small

If one side fits in memory (~100 MB compressed):

```python
from pyspark.sql.functions import broadcast

result = points.join(
    broadcast(counties),
    expr("ST_Within(points.geom, counties.geom)"),
    "left",
)
```

Bypasses the spatial partitioner entirely. Sedona builds an in-memory STRtree on the broadcast side and probes from each executor. The biggest single optimization for "billions of points × few thousand polygons."

For "is the small side broadcastable?" — check the compressed size of the parquet:

```python
from pyspark.sql.functions import lit
counties_size_mb = counties.write.format("noop").mode("overwrite").save() and \
                   sedona._jsparkSession.sessionState().executePlan(...)  # complex
# Practical: estimate from the Parquet file size on disk; <500 MB compressed usually broadcasts cleanly.
```

`spark.sql.autoBroadcastJoinThreshold` defaults to 10 MB — increase for larger broadcasts:

```python
sedona.conf.set("spark.sql.autoBroadcastJoinThreshold", "200m")
```

## Number of partitions

Default: derived from input. Often wrong for spatial workloads. Heuristics:

- **Points side: ~50,000 rows per partition.** Smaller and you're scheduling overhead-bound; larger and individual partitions OOM during the spatial join.
- **Polygons side (when not broadcasting): ~5,000 polygons per partition.** Polygons are bigger objects; fewer per partition.

Set explicitly:

```python
points = points.repartition(200)  # 200 partitions for 10M points (50K/partition)
```

For repartitioning *spatially* (so that nearby data lands in the same partition):

```python
sedona.conf.set("spark.sedona.global.partitionnum", "200")
# Sedona's spatial join will repartition both sides to 200 spatial partitions
```

## Skew — the silent killer

Spatial data is almost always skewed. New York has more points than Wyoming. Without intervention, one executor processes the NY partition for hours while everything else finishes in minutes.

### Detection

In the Spark UI, look at the spatial join stage. Tasks with very long runtimes ("straggler tasks") indicate skew. Check task input sizes — one task processing 10× the data of others.

### Mitigation

**Sedona partitioner**: KDB-tree is *adaptive* — it gives more partitions to dense regions automatically. This usually handles moderate skew. Increase `spark.sedona.global.partitionnum` if you still see stragglers.

**Salt the join key**: For severe skew, add a salt column to the heavy side and explode the small side:

```python
# Heavy side gets a salt 0..9
heavy = points.withColumn("salt", expr("FLOOR(RAND() * 10)"))

# Small side gets all 10 salts
small = counties.withColumn("salt_arr", expr("array(0,1,2,3,4,5,6,7,8,9)"))
small = small.withColumn("salt", explode("salt_arr"))

result = heavy.join(small, ["salt"], "inner") \
              .filter(expr("ST_Within(heavy.geom, small.geom)"))
```

Trade off: 10× more rows in the small side but the spatial join runs on partitions that fit in memory.

**Subdivide complex polygons**: If a few polygons (NYC borough boundary, Texas state boundary) are slow to test individually, subdivide them with `ST_Subdivide` before the join. Sedona supports it the same way PostGIS does.

```python
counties_sub = sedona.sql("""
    SELECT geoid, name, ST_Subdivide(geom, 256) AS geom
    FROM counties
""")
counties_sub.cache()
```

## Coalesce after join

The result of a spatial join inherits the partition count from the spatial partitioner — often higher than what you want for downstream writes:

```python
result = result.coalesce(20)  # or .repartition(20) if you need full shuffle
result.write.format("parquet").save("s3://output/")
```

Without this, you'll write 200+ small files. Coalesce to ~50-200 MB per file.

## Adaptive query execution (AQE)

Spark 3.x AQE can dynamically coalesce partitions and handle skew at runtime:

```python
sedona.conf.set("spark.sql.adaptive.enabled", "true")
sedona.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
sedona.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
```

AQE works on regular SQL joins but doesn't fully understand Sedona's spatial join optimizer. Test both with and without AQE on your workload — sometimes AQE-disabled is faster for spatial joins because Sedona's optimizer is already doing the right partitioning.

## Cluster-side considerations

| Setting | Recommendation for spatial workloads |
|---|---|
| Executor memory | 8–16 GB (geometry objects are larger than scalar values) |
| Executor cores | 4–8 (spatial joins are memory-bound, not CPU-bound) |
| `spark.sql.shuffle.partitions` | 200–400 (default 200 is OK for moderate workloads) |
| `spark.serializer` | KryoSerializer (always — see SKILL.md) |
| `spark.memory.fraction` | 0.7 (more for spatial caches) |

## When partitioning isn't the problem

If your spatial join is still slow after partitioning tuning, look at:

1. **Geometry complexity** — subdivide complex polygons.
2. **CRS in the predicate** — `ST_Distance(geom_4326, geom_4326)` is meaningless (degrees) and may also be triggering implicit conversions per row.
3. **Python UDFs in the join predicate** — they break the spatial optimizer; rewrite as `ST_*` SQL.

See [`spatial-joins-at-scale.md`](spatial-joins-at-scale.md) and [`pitfalls.md`](pitfalls.md).
