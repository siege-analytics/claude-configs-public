---
name: unity-catalog
description: "Catalog discipline for Unity Catalog / Hive Metastore. TRIGGER: writing Delta/Parquet/Iceberg, saveAsTable, registering tables, or touching any catalog-managed S3 path. Enforces catalog-first: never raw-path writes for catalog-managed data."
---

# Unity Catalog Discipline

## TRIGGER

This skill fires when you are about to:

- Write Delta / Parquet / Iceberg / ORC to any S3 path.
- Call `df.write.save(...)`, `df.write.parquet(...)`, `df.write.format("delta").save(...)`, `df.write.format("iceberg").save(...)`.
- Call `df.write.saveAsTable(...)`.
- Touch paths under `s3a://hive-warehouse/*`, `s3://silver/*`, `s3://gold/*`, `s3://bronze/*`, or any other bucket that backs a catalog-managed schema.
- Register a table in Hive Metastore or Unity Catalog.
- Modify a `SparkApplication` CRD that writes Delta/Parquet to shared storage.

If **any** of the above is true, this skill is mandatory reading before you act.

---

## Rule

**Catalog-managed data is only ever written through the catalog.**

The catalog (UC in this environment) is the source of truth for:

- Table identity — the name downstream consumers reference.
- Storage location — the physical path the catalog delegates reads/writes to.
- Schema — column names, types, nullability.
- Format — Delta, Parquet, Iceberg.
- Access control — which identities can read/write.

Writing directly to `s3a://...` bypasses all of it. Downstream readers querying `SELECT * FROM catalog.schema.table` will not see your data because the catalog points elsewhere. You will either:

1. **Be invisible** — your output lives at a path nobody queries; Consumer sees stale data.
2. **Corrupt state** — you overwrite a path that another process manages, causing schema/format drift.
3. **Orphan data** — storage fills up with writes nobody owns and nobody cleans.

All three have happened. The fix is always the same: use the catalog.

---

## The correct API

### Writing a Spark DataFrame to a catalog table

```python
# UC-managed table (catalog chooses location):
df.write.format("delta").mode("overwrite").saveAsTable("enterprise_bulk.individual_contributions")

# If the schema doesn't exist yet:
spark.sql("CREATE SCHEMA IF NOT EXISTS enterprise_bulk")
df.write.format("delta").mode("overwrite").saveAsTable("enterprise_bulk.individual_contributions")

# If you need overwriteSchema on a repeated run:
(df.write.format("delta")
   .mode("overwrite")
   .option("overwriteSchema", "true")
   .saveAsTable("enterprise_bulk.individual_contributions"))
```

### Writing via SQL

```python
df.createOrReplaceTempView("src")
spark.sql("INSERT OVERWRITE TABLE enterprise_bulk.individual_contributions SELECT * FROM src")
```

### Never (without explicit direction)

```python
# WRONG: bypasses catalog entirely
df.write.format("delta").save("s3a://hive-warehouse/enterprise_bulk/individual_contributions")

# WRONG: same bucket, same bypass
df.write.parquet("s3a://silver/enterprise_bulk/individual_contributions")

# WRONG: raw Delta path write "for testing" — this is how orphans start
df.write.format("delta").mode("overwrite").save("s3a://hive-warehouse/enterprise_bulk_v2/...")
```

Raw-path writes are only acceptable for **private, non-catalog-managed locations** like a scratch bucket the catalog doesn't cover, and even then the path must be outside any warehouse prefix.

---

## Pre-flight checks

Before writing, verify the target table's catalog state:

```bash
# Hit the UC REST API directly for truth
curl -sS "http://app-unity-catalog.electinfo.svc.cluster.local:8080/api/2.1/unity-catalog/tables?catalog_name=electinfo&schema_name=<schema>" \
  | python3 -m json.tool
```

For each target table confirm:

1. **Exists** — if not, schema needs creation or the name is wrong.
2. **`table_type`** — MANAGED (UC chooses storage) vs EXTERNAL (points to a fixed location). Write accordingly.
3. **`data_source_format`** — DELTA, PARQUET, ICEBERG. Match your writer's format. Mixing Parquet writes onto a Delta table corrupts it.
4. **`storage_location`** — sanity check it matches what UC's storage credential covers. If UC can't generate creds for the location (`FAILED_PRECONDITION` on `generateTemporaryTableCredentials`), the table is broken at the registration level and needs re-registration before any write.
5. **`columns`** — non-empty, schema matches what you're writing. A table registered with 0 columns is broken.

If any of these fail, **stop and fix the registration before writing**.

---

## Spark session requirements

For `saveAsTable` to reach UC, the Spark session must be configured with the UC catalog:

```
spark.sql.catalog.spark_catalog=info.elect.spark.catalog.PatchedUCSingleCatalog
spark.sql.catalog.spark_catalog.uri=http://app-unity-catalog.electinfo.svc.cluster.local:8080
spark.sql.catalog.spark_catalog.uc-catalog=electinfo
```

This is already set on `spark-connect-server` (see `spark-on-kubernetes/manifests/spark-connect/base/spark-connect-server.yaml`). For `SparkApplication` CRDs (Spark Operator), add those three `sparkConf` keys to the driver + executor config.

Spark Connect clients get the UC catalog automatically when they remote into the configured server — no extra config needed.

---

## Schema registration flow (new table)

If the table doesn't exist yet:

```python
# 1. Create schema (idempotent)
spark.sql("CREATE SCHEMA IF NOT EXISTS <schema>")

# 2. Create + populate table in one step via saveAsTable
df.write.format("delta").saveAsTable("<schema>.<table>")

# OR: 2b. Explicit CREATE TABLE with chosen location (EXTERNAL):
spark.sql("""
    CREATE TABLE IF NOT EXISTS <schema>.<table>
    (col1 STRING, col2 DECIMAL(14,2), ...)
    USING DELTA
    LOCATION 's3a://hive-warehouse/<managed-path>/<schema>/<table>'
""")
df.write.format("delta").mode("overwrite").insertInto("<schema>.<table>")
```

Verify afterwards via the UC REST API that the table landed with the columns you expect.

---

## Checklist before any Delta/Parquet write

- [ ] Did I check the target table in UC REST first? (`storage_location`, `data_source_format`, `columns`)
- [ ] Am I using `saveAsTable` (catalog path) or `INSERT INTO ... SELECT` (catalog path), not `save(s3a://...)` (raw path)?
- [ ] If new schema: did I `CREATE SCHEMA IF NOT EXISTS` first?
- [ ] If the table exists: does my DataFrame's schema match? If not, did I explicitly set `overwriteSchema=true` and accept the drift?
- [ ] Does the Spark session have the UC catalog configured? (Spark Connect: yes by default. Spark Operator: check the CRD `sparkConf`.)
- [ ] Have I confirmed with the user that the schema / location decision is what they want, for anything downstream consumers depend on?

If any answer is "no" or "I don't know" — stop and resolve it before writing.

---

## If UC is broken for your target table

Symptoms: `generateTemporaryTableCredentials` returns 400 `FAILED_PRECONDITION`, or `DESCRIBE TABLE` fails, or the table has 0 columns registered.

- **Do not work around by writing to a raw path.** That creates orphans and doesn't solve the downstream-read problem.
- **Diagnose**: query UC REST directly to see the registration state. Check whether the `storage_location` bucket is covered by UC's storage credentials (`s3.bucketPath.N` in `app-unity-catalog` configmap).
- **Coordinate**: if UC needs a new storage credential binding or the table needs re-registration, this is a config/ops change — surface it as a ticket and get confirmation before touching UC's configuration.
- **Do not re-register existing production tables without explicit authorization.** They may be referenced by consumers, views, or jobs you don't know about.

---

## Related

- `skills/coding/spark/SKILL.md` — broader Spark patterns
- `skills/coding/pipeline-jobs/SKILL.md` — pipeline orchestration
- `electinfo_claude_skills/skills/pipeline-guard/SKILL.md` — don't bypass Spark Operator for batch jobs
- `electinfo_claude_skills/skills/rundeck-job/SKILL.md` — Rundeck YAML for pipeline jobs

---

## History

This skill was written after repeatedly writing Delta files directly to `s3a://hive-warehouse/enterprise_bulk/*` paths that bypassed UC. The "cutover" was invisible to Consumer (whose reader resolves `enterprise_bulk.*` through UC), and left 99 orphaned objects in shared storage. The rule existed in `pipeline-guard` ("Register in Unity Catalog") but as a footnote, not an enforced trigger. This skill exists so the rule fires before the write, not after.
