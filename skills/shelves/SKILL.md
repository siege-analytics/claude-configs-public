---
name: shelves
description: Meta-router for the DBrain book-skill library. Dispatches to one of 11 topic shelves (engineering-principles, systems-architecture, languages, data-and-pipelines, product, marketing, sales, strategy, design, team, storytelling). Read this before consulting any individual book skill.
disable-model-invocation: false
---

# DBrain — Book-Skill Library

Each shelf is a router that dispatches to individual book skills. Load the shelf for the topic, the shelf names the right book, you read the book in full.

This pattern keeps the description budget small: one slot per shelf, not one per book.

## Shelves

| Shelf | When to load |
|---|---|
| [skill:engineering-principles] | Code quality, design, refactoring rationale, principles arguments |
| [skill:systems-architecture] | Distributed-system design, storage choice, replication, scaling, system-design interview |
| [skill:languages] | Idioms and best practices for Python, JVM (Java/Kotlin/Scala-on-Spark), TypeScript, Rust |
| [skill:data-and-pipelines] | Pipeline design, batch/stream, scheduled jobs |
| [skill:product] | Discovery, JTBD, lean experimentation, retention |
| [skill:marketing] | Messaging, copy, conversion, positioning |
| [skill:sales] | Pipeline, pricing, negotiation, influence |
| [skill:strategy] | Market entry, positioning, EOS, blue ocean |
| [skill:design] | UI, UX heuristics, typography, microinteractions |
| [skill:team] | Motivation, ways of working |
| [skill:storytelling] | Communicating data, slide animation |

## How shelves work

Each shelf's `SKILL.md` is a thin router (≤ 2 KB) with:

1. A trigger table mapping task signals to the book to load.
2. A list of book skills in the shelf with one-line descriptions.

Books themselves (`shelves/<shelf>/<book>/SKILL.md`) are fat — they carry their full `references/` knowledge bank from the upstream source.

## Sources

The book skills are imported from two upstream MIT-licensed projects with attribution:

- [ZLStas/skills](https://github.com/ZLStas/skills)
- [wondelai/skills](https://github.com/wondelai/skills)

See [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md) for the per-book mapping and commit pins.

## Status

Shelves are populated incrementally via the `feat/dbrain-*` PR stack. Until a given shelf merges, its router link from this meta-router will 404 — that is expected and resolves as each PR lands.
