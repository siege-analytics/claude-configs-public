---
name: scala-on-spark
description: Scala for Spark / Databricks. Thin delegating skill — pulls JVM idiom rationale from the languages shelf and Spark cost-model rationale from the data-intensive shelf and the existing Spark skill. Read this when you're about to write or review Scala in a Databricks notebook, a `.scala` file, or `Dataset[T]` Spark code.
routed-by: coding-standards
---

# Scala on Spark

Most Scala you'll write in a Siege project is **glue around Spark**: notebook cells, `Dataset[T]` transforms, UDFs, Encoder boilerplate. The cost model and failure modes are JVM-shaped, and the language idioms have direct analogues in Java and Kotlin. Rather than maintain a parallel Scala-style guide, this skill **delegates** to the books that already cover those concerns.

## Companion shelves (load these)

- [`effective-java`](../../shelves/languages/effective-java/SKILL.md) — `equals`/`hashCode`, immutability, exception handling, generics. Items map almost 1:1 to Scala case classes and `Either`-shaped APIs.
- [`effective-kotlin`](../../shelves/languages/effective-kotlin/SKILL.md) — null-safety idioms (Scala `Option`/`Either` ≈ Kotlin nullable + `let`), DSLs, scope functions.
- [`data-intensive`](../../shelves/systems-architecture/data-intensive/SKILL.md) — partitioning, replication, batch/stream, the *why* behind Spark's cost model.
- [`spark`](../../coding/spark/SKILL.md) — Siege-specific Spark patterns (catalog, medallion, transform shape).

Always-on: [`jvm`](../../_jvm-rules.md) is loaded when JVM code is touched and applies to Scala notebook cells equally.

## Scala-specific quick rules

- **Encoders:** prefer `Dataset[T]` over `DataFrame` when the schema is known; you get type-checked column access and avoid string-typo bugs. Use `Encoders.product[T]` when implicits go missing.
- **Case classes are value-objects.** Don't add behavior; use companion objects or extension methods. Mirrors the "deep-modules / no behavior in DTOs" advice in Ousterhout (`software-design-philosophy`).
- **`Option` over `null`.** Wrap any Spark API call that *could* return null. UDFs that take primitives must accept `java.lang.Long`/`java.lang.Double` to handle nullable columns.
- **`for`-comprehensions over nested `flatMap`.** Cleaner, but watch for unintended early termination on `None`.
- **Avoid implicit conversions in production code.** Implicit *parameters* (e.g., `SparkSession`) are fine; implicit *value conversions* obscure intent and slow review.
- **Serialization.** Anything captured in a closure crosses the wire — keep it `Serializable`, avoid capturing the `SparkSession` or large `Map`s. Kryo is usually the right registrar; register custom classes.
- **Don't write your own `equals`/`hashCode` on case classes.** The compiler generates correct ones; manual versions break `groupBy`/`distinct`.

## Disambiguation vs other skills

- **vs `coding/spark/`:** the Spark skill is *what* to do (Siege medallion, catalog rules, transform structure). This skill is *how* the Scala expression of those patterns should look.
- **vs `shelves/languages/effective-java/`:** Effective Java is the canonical reference. This skill exists so the agent knows to load it when the file is `.scala` or the notebook cell starts with `%scala`.
