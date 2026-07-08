---
name: shelves
description: Meta-router for the DBrain book-skill library. Dispatches to one of 14 topic shelves (engineering-principles, systems-architecture, django, languages, data-and-pipelines, product, marketing, sales, strategy, design, team, storytelling, geospatial, statistical-inference). Read this before consulting any individual book skill.
---

# DBrain -- Book-Skill Library

Each shelf is a router that dispatches to individual book skills. Load the shelf for the topic, the shelf names the right book, you read the book in full.

This pattern keeps the description budget small: one slot per shelf, not one per book.

## Shelves

| Shelf | When to load |
|---|---|
| [`shelves--engineering-principles`](../shelves/engineering-principles/SKILL.md) | Code quality, design, refactoring rationale, principles arguments |
| [`shelves--systems-architecture`](../shelves/systems-architecture/SKILL.md) | Distributed-system design, storage choice, replication, scaling, system-design interview |
| [`shelves--django`](../shelves/django/SKILL.md) | Django best practices, scaling for production, legacy codebase rescue |
| [`shelves--languages`](../shelves/languages/SKILL.md) | Idioms and best practices for Python, JVM (Java/Kotlin/Scala-on-Spark), TypeScript, Rust |
| [`shelves--data-and-pipelines`](../shelves/data-and-pipelines/SKILL.md) | Pipeline design, batch/stream, scheduled jobs |
| [`shelves--product`](../shelves/product/SKILL.md) | Discovery, JTBD, lean experimentation, retention |
| [`shelves--marketing`](../shelves/marketing/SKILL.md) | Messaging, copy, conversion, positioning |
| [`shelves--sales`](../shelves/sales/SKILL.md) | Pipeline, pricing, negotiation, influence |
| [`shelves--strategy`](../shelves/strategy/SKILL.md) | Market entry, positioning, EOS, blue ocean |
| [`shelves--design`](../shelves/design/SKILL.md) | UI, UX heuristics, typography, microinteractions |
| [`shelves--team`](../shelves/team/SKILL.md) | Motivation, ways of working |
| [`shelves--storytelling`](../shelves/storytelling/SKILL.md) | Communicating data, slide animation |
| `shelves--geospatial` (planned) | CRS / spatial joins / MAUP / areal interpolation / spatial statistics -- geographic analysis grounded in methodology |
| `shelves--statistical-inference` (planned) | Causal inference (theory + applied), Bayesian / multilevel, applied EDA / hypothesis testing -- analytical rigor for any statistical claim |

## How shelves work

Each shelf's `SKILL.md` is a thin router (≤ 2 KB) with:

1. A trigger table mapping task signals to the book to load.
2. A list of book skills in the shelf with one-line descriptions.

Books themselves (`shelves/<shelf>/<book>/SKILL.md`) are fat -- they carry their full `references/` knowledge bank from the upstream source.

## Sources

The book skills are imported from two upstream MIT-licensed projects with attribution:

- [ZLStas/skills](https://github.com/ZLStas/skills)
- [wondelai/skills](https://github.com/wondelai/skills)

See [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md) for the per-book mapping and commit pins.

## Status

Shelves are populated incrementally via the `feat/dbrain-*` PR stack. Until a given shelf merges, its router link from this meta-router will 404 -- that is expected and resolves as each PR lands.
