# Sedona Scaffolding — Scala Variant

**PySpark is the Siege default** for Sedona work. This file documents the Scala variant — load it only when you're actually writing `.scala` files or `%scala` notebook cells. The spatial logic and SQL strings are identical between languages; only the scaffolding around them diverges.

## When you'd use Scala

| Situation | Why Scala over PySpark |
|---|---|
| Existing Scala codebase you're extending | Don't introduce a Python boundary |
| Spark Streaming spatial work | Streaming APIs are first-class in Scala, second-class in Python |
| You need compile-time `Dataset[T]` typing | Python is dynamic; Scala catches schema errors at compile time |
| Team / project preference | Already decided |

For everything else — notebook exploration, batch jobs, ML around the spatial work — **stay in PySpark**.

## The diff

### Session creation

**Default (PySpark):**
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

**Scala variant:**
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

### DataFrame creation

**Default (PySpark):**
```python
df = sedona.read.format("geoparquet").load("s3://bucket/data.parquet")
df = df.withColumn("geom", expr("ST_GeomFromWKT(wkt_col, 4326)"))
df.createOrReplaceTempView("points")
```

**Scala variant:**
```scala
import org.apache.spark.sql.functions.expr

val df = sedona.read.format("geoparquet").load("s3://bucket/data.parquet")
  .withColumn("geom", expr("ST_GeomFromWKT(wkt_col, 4326)"))

df.createOrReplaceTempView("points")
```

### UDF registration (avoid both, but if you must)

Always prefer ST_* SQL — see [`udf-vs-builtin.md`](udf-vs-builtin.md). Both per-row paths pay the same serialization cost and bypass the optimizer.

**Default (PySpark — vectorized Pandas UDF):**
```python
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import StringType
import pandas as pd

@pandas_udf(StringType())
def my_udf(s: pd.Series) -> pd.Series:
    return s.str.upper()
```

**Scala variant (typed UDF):**
```scala
import org.apache.spark.sql.functions.udf

val myUdf = udf((s: String) => s.toUpperCase)
sedona.udf.register("my_udf", myUdf)
```

### DataFrame typing

PySpark is dynamically typed; schema errors surface at runtime. Scala has typed `Dataset[T]` available — use it when you want compile-time safety on column names and types:

```scala
case class Point(id: Long, geom: Geometry)
val ds: Dataset[Point] = df.as[Point]
// Compile-time error if df doesn't match Point schema
```

If you don't need that safety, stay with `DataFrame` and the typing difference vanishes. For Spark/Scala typing patterns generally, see [`coding/scala-on-spark/SKILL.md`](../../scala-on-spark/SKILL.md).

### Error handling

**Default (PySpark — Python exceptions):**
```python
try:
    sedona.sql("...").write.format("parquet").save("...")
except Exception as e:
    logger.error(f"Spatial join failed: {e}")
    raise
```

**Scala variant (`Try`/`Either` or Java exceptions):**
```scala
import scala.util.{Try, Success, Failure}

Try(sedona.sql("...").write.format("parquet").save("...")) match {
  case Success(_) => logger.info("Done")
  case Failure(e) => logger.error(s"Spatial join failed: ${e.getMessage}"); throw e
}
```

### Testing

**Default (PySpark — pytest + fixtures):**
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

**Scala variant (ScalaTest + sedona-test JARs):**
```scala
class SpatialJoinSpec extends AnyFlatSpec with BeforeAndAfterAll {
  val sedona: SparkSession = SedonaContext.builder().master("local[2]").getOrCreate()

  "spatial join" should "match expected count" in {
    // ...
    result.count() shouldBe 100
  }
}
```

## Same in both — partition tuning, broadcast, AQE

All Spark-level tuning is identical. `spark.sedona.global.partitionnum`, `broadcast()`, AQE settings all apply equally.

## Same in both — debugging

`EXPLAIN`, the Spark UI, `result.explain()` work identically. Plan output is the same JVM plan in both languages.

## Mental model

Treat Sedona spatial logic as **language-agnostic SQL** that you wrap in either Python or Scala scaffolding. The choice of scaffolding is a workflow / team / context decision, not a spatial-logic decision.

For Scala-specific patterns around Spark generally (case classes for Dataset[T], encoder gotchas, immutability with `val`), see [`coding/scala-on-spark/SKILL.md`](../../scala-on-spark/SKILL.md).
