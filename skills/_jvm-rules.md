---
description: Always-on JVM-language standards. Apply when working with Java, Kotlin, or Scala-on-Spark code. Merged from Effective Java (Bloch) and Effective Kotlin (Moskała).
---

# JVM Standards (Java / Kotlin / Scala-on-Spark)

These standards apply to any JVM-language file: Java, Kotlin, and -- by extension -- Scala for Spark/Databricks work, where the cost model and failure modes are JVM-shaped.


# Effective Java Standards

Apply these principles from *Effective Java* (Joshua Bloch, 3rd edition) to all Java code.

## Object creation

- Prefer static factory methods over constructors -- they have names, can return subtypes, and can cache instances
- Use a builder when a constructor or factory would have more than 3 parameters
- Never create unnecessary objects; reuse `String` literals, prefer `Boolean.valueOf(x)` over `new Boolean(x)`

## Classes and mutability

- Minimize mutability -- all fields `private final` by default; add setters only when needed
- Favor composition over inheritance; document classes designed for extension or mark them `final`
- Override `@Override` on every method that overrides or implements; the annotation catches typos at compile time

## Methods

- Validate parameters at entry; throw `IllegalArgumentException`, `NullPointerException`, or `IndexOutOfBoundsException` with a message
- Return empty collections or `Optional`, never `null`, from methods with a non-primitive return type
- Use `Optional` for return values that may be absent; don't use it for fields or parameters

## Exceptions

- Use checked exceptions for recoverable conditions; unchecked (`RuntimeException`) for programming errors
- Prefer standard exceptions: `IllegalArgumentException`, `IllegalStateException`, `UnsupportedOperationException`, `NullPointerException`
- Don't swallow exceptions -- at minimum log with context before ignoring; never `catch (Exception e) {}`

## Generics and collections

- Use generic types and methods; avoid raw types (`List` → `List<E>`)
- Use bounded wildcards (`? extends T` for producers, `? super T` for consumers -- PECS)
- Prefer `List` over arrays for type safety; use arrays only for performance-sensitive low-level code

## Concurrency

- Synchronize all accesses to shared mutable state; prefer `java.util.concurrent` utilities over `synchronized`
- Prefer immutable objects and thread confinement over shared mutable state


# Effective Kotlin Standards

Apply these principles from *Effective Kotlin* (Marcin Moskała, 2nd edition) to all Kotlin code.

## Safety

- Prefer `val` over `var`; use `var` only when mutation is genuinely required
- Use nullable types via `T?`; avoid `!!`; narrow with `?.`, `?:`, `let`, or `checkNotNull()`
- Use `require()` for argument preconditions and `check()` for state preconditions at function entry

## Functions

- Use named arguments when passing more than 2 parameters, especially when they share the same type
- Use default arguments instead of overloads for optional behavior
- Prefer extension functions over utility classes for domain operations on a type you own

## Classes and design

- Use data classes for value objects -- they get `equals`, `hashCode`, `copy`, and `toString` for free
- Prefer sealed classes over open hierarchies when the set of subtypes is finite and known
- Use `object` for singletons, `companion object` for factory methods and class-level constants

## Collections

- Use functional operators (`map`, `filter`, `fold`, `groupBy`) over manual loops
- Prefer `Sequence` for large collections or multi-step pipelines -- avoids intermediate lists
- Use `buildList { }` / `buildMap { }` instead of a mutable variable followed by `.toList()`

## Coroutines

- Launch coroutines in a structured `CoroutineScope`; never use `GlobalScope` in production
- Use `withContext(Dispatchers.IO)` for blocking I/O; never block the main/UI thread
- Prefer `Flow` over callbacks for asynchronous streams; use `StateFlow` for observable state


---

## Attribution

Adapted from [ZLStas/skills](https://github.com/ZLStas/skills) at commit `3b87ad338fe18b68371a69827372746729074c0e` (`rules/`). MIT-licensed; copyright © ZLStas and contributors. See repo-root `THIRD_PARTY_NOTICES.md`.