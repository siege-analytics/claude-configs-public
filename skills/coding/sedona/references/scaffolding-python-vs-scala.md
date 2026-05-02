# Sedona Scaffolding: Python vs Scala

The spatial logic is identical. The scaffolding around it diverges in 5–10 known ways. This file is the diff.

## Same — the spatial logic

Whether you write `df.createOrReplaceTempView("points")` then `sedona.sql("SELECT ST_Within(...) ...")`, or you do the equivalent in Scala, the **SQL strings are identical** and the optimizer behavior is identical. ST_* functions are JVM-native; Python and Scala both call into the same JVM implementations.

This means: you can prototype in PySpark notebooks, then port to Scala for production with no spatial-logic rewrites — only scaffolding changes.

## Different — session creation

**PySpark:**
```python
from sedona.spark import SedonaContext

config = (
    SedonaContext.builder()
    .appName("spatial-pipeline")
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
    .getOrCreate()
)
sedona = SedonaContext.create(config)
```

**Scala:**
```scala
import org.apache.sedona.spark.SedonaContext
import org.apache.spark.sql.SparkSession

val config = SedonaContext
  .builder()
  .appName("spatial-pipeline")
  .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
  .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
  .getOrCreate()

val sedona = SedonaContext.create(config)
```

## Different — DataFrame creation

**PySpark:**
```python
df = sedona.read.format("geoparquet").load("s3://bucket/data.parquet")
df = df.withColumn("geom", expr("ST_GeomFromWKT(wkt_col, 4326)"))
df.createOrReplaceTempView("points")
```

**Scala:**
```scala
import org.apache.spark.sql.functions.expr

val df = sedona.read.format("geoparquet").load("s3://bucket/data.parquet")
  .withColumn("geom", expr("ST_GeomFromWKT(wkt_col, 4326)"))

df.createOrReplaceTempView("points")
```

## Different — UDF registration (avoid both, but if you must)

**PySpark — vectorized Pandas UDF:**
```python
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import StringType
import pandas as pd

@pandas_udf(StringType())
def my_udf(s: pd.Series) -> pd.Series:
    return s.str.upper()
```

**Scala — typed UDF:**
```scala
import org.apache.spark.sql.functions.udf

val myUdf = udf((s: String) => s.toUpperCase)
sedona.udf.register("my_udf", myUdf)
```

Both still pay the per-row serialization cost. **Always prefer ST_* SQL — see [`udf-vs-builtin.md`](udf-vs-builtin.md).**

## Different — when to use which

| Situation | Recommended scaffolding |
|---|---|
| Notebook exploration, ad-hoc analysis | **PySpark** — REPL is faster, plotting is easier |
| Production batch job on Databricks | Either; team preference. Scala has slightly better job startup time and JVM type safety. |
| Spark Streaming spatial work | **Scala** — Streaming APIs are first-class in Scala, second-class in Python |
| Heavy ML around the spatial work | **PySpark** — better integration with sklearn/torch on the driver |
| Already in a Scala codebase (existing transformations) | **Scala** — don't introduce a Python boundary |

## Different — DataFrame typing

**PySpark** is dynamically typed. Schema errors surface at runtime:

```python
df = sedona.sql("SELECT bad_col FROM points")  # runs
df.show()  # ERRORS HERE: column doesn't exist
```

**Scala** has typed `Dataset[T]` (when you use it):

```scala
case class Point(id: Long, geom: Geometry)

val ds: Dataset[Point] = df.as[Point]
// Compile-time error if df doesn't match Point schema
```

If you want compile-time safety on column names and types, Scala + `Dataset[T]` is the path. Otherwise stay with `DataFrame` and the typing differences vanish.

For Spark/Scala typing patterns generally, see [`coding/scala-on-spark/SKILL.md`](../../scala-on-spark/SKILL.md).

## Different — error handling

**PySpark** uses Python exceptions:

```python
try:
    result = sedona.sql("...")
    result.write.format("parquet").save("...")
except Exception as e:
    logger.error(f"Spatial join failed: {e}")
    raise
```

**Scala** uses `Try`/`Either` patterns or Java exceptions:

```scala
import scala.util.{Try, Success, Failure}

Try(sedona.sql("...").write.format("parquet").save("...")) match {
  case Success(_) => logger.info("Done")
  case Failure(e) => logger.error(s"Spatial join failed: ${e.getMessage}"); throw e
}
```

## Different — testing

**PySpark** uses pytest + `pyspark.testing` or your own fixtures:

```python
@pytest.fixture
def sedona():
    config = SedonaContext.builder().master("local[2]").appName("test").getOrCreate()
    return SedonaContext.create(config)

def test_spatial_join(sedona):
    points = sedona.createDataFrame(...)
    counties = sedona.createDataFrame(...)
    result = sedona.sql("SELECT ... FROM points JOIN counties ON ST_Within(...)")
    assert result.count() == 100
```

**Scala** uses ScalaTest + sedona-test JARs:

```scala
class SpatialJoinSpec extends AnyFlatSpec with BeforeAndAfterAll {
  val sedona: SparkSession = SedonaContext.builder().master("local[2]").getOrCreate()
  
  "spatial join" should "match expected count" in {
    // ...
    result.count() shouldBe 100
  }
}
```

## Same — partition tuning, broadcast, AQE

All Spark-level tuning is identical. `spark.sedona.global.partitionnum`, `broadcast()`, AQE settings all apply equally.

## Same — debugging

`EXPLAIN`, the Spark UI, `result.explain()` work identically. Plan output is the same JVM plan in both languages.

## Mental model

Treat Sedona spatial logic as **language-agnostic SQL** that you wrap in either Python or Scala scaffolding. The choice of scaffolding is a workflow / team / context decision, not a spatial-logic decision.

For Scala-specific patterns around Spark generally (case classes for Dataset[T], encoder gotchas, immutability with `val`), see [`coding/scala-on-spark/SKILL.md`](../../scala-on-spark/SKILL.md).
