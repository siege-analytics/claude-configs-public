---
name: shelf-languages
description: Router for language-idiom book skills. Dispatches to Effective Python/Java/Kotlin/TypeScript, Kotlin in Action, Spring Boot in Action, Programming with Rust, Rust in Action, Using Asyncio in Python, or Web Scraping with Python based on the language and task. Read this when writing or reviewing code in a specific language and you want canonical idioms beyond the project's house style.
disable-model-invocation: false
---

# Languages — Shelf

Language-specific idiom and best-practice books. Pair these with the always-on `_<lang>-rules.md` files (loaded by the resolver) for full coverage: rules give you the short maxims, books give you the deep rationale.

## Trigger table

| Language / task | Book to read |
|---|---|
| Pythonic style, idioms, stdlib usage | [skill:effective-python] |
| Async I/O in Python, `asyncio`, event loop, concurrency primitives | [skill:using-asyncio-python] |
| HTTP scraping, parsing, anti-bot, polite crawling | [skill:web-scraping-python] |
| Java idioms — `equals`/`hashCode`, immutability, generics, exceptions | [skill:effective-java] |
| Kotlin idioms — null safety, scope functions, DSLs, coroutines | [skill:effective-kotlin] |
| Kotlin from-the-ground-up — language features and patterns | [skill:kotlin-in-action] |
| Spring Boot apps, autoconfiguration, starters | [skill:spring-boot-in-action] |
| Rust ownership, traits, lifetimes, error handling | [skill:programming-with-rust] |
| Rust applied — networking, I/O, embedded, performance | [skill:rust-in-action] |
| TypeScript types, narrowing, generics, structural typing | [skill:effective-typescript] |

## Books in this shelf

- [skill:effective-python] — Brett Slatkin
- [skill:using-asyncio-python] — Caleb Hattingh
- [skill:web-scraping-python] — Ryan Mitchell
- [skill:effective-java] — Joshua Bloch
- [skill:effective-kotlin] — Marcin Moskała
- [skill:kotlin-in-action] — Jemerov & Isakova
- [skill:spring-boot-in-action] — Craig Walls
- [skill:programming-with-rust] — Donis Marshall
- [skill:rust-in-action] — Tim McNamara
- [skill:effective-typescript] — Dan Vanderkam

## Why JVM books matter for Python-first work

Spark on Databricks runs on the JVM. PySpark calls execute through JVM Spark, the cost model is JVM, the failures (Kryo serialization, partition skew, executor OOM) are JVM failures. Effective Java's items on `equals`/`hashCode`, immutability, and exception handling apply directly to Spark UDFs and Dataset code. Effective Kotlin applies to any Scala you touch — Scala's `Option`/`Either` ≈ Kotlin's nullable-with-let. The new `coding/scala-on-spark/` skill (PR 8) delegates here.

## Disambiguation

- **`effective-kotlin` vs `kotlin-in-action`:** Kotlin in Action teaches the language; Effective Kotlin sharpens existing knowledge with idiom-by-idiom items. Read the former before the latter.
- **`programming-with-rust` vs `rust-in-action`:** Programming with Rust is the language reference; Rust in Action is the applied counterpart with networking and systems examples.
- **Always-on rules vs full book:** for quick edits, the `_<lang>-rules.md` always-on file is enough. Load the book when writing nontrivial code, doing reviews, or designing module APIs.

## Source attribution

All books in this shelf are imported verbatim from [ZLStas/skills](https://github.com/ZLStas/skills). See per-book footers and the repo-root [`THIRD_PARTY_NOTICES.md`](../../../THIRD_PARTY_NOTICES.md).
