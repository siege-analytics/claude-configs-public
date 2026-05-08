---
name: shelf-data-and-pipelines
description: Router for data-and-pipelines book skills. Currently dispatches to data-pipelines (Densmore — Data Pipelines Pocket Reference). Read this when designing batch/stream pipelines, scheduled jobs, ingestion frameworks, or moving data between systems.
disable-model-invocation: false
---

# Data and Pipelines — Shelf

Books on building data pipelines, scheduling, and moving data between systems.

## Trigger table

| Task signal | Book to read |
|---|---|
| Designing an ingestion pipeline, choosing batch vs stream, scheduling, reliability | [`data-pipelines`](../../shelves/data-and-pipelines/data-pipelines/SKILL.md) |
| Storage-engine choice or distributed-data internals (load this *and* DDIA) | also [`data-intensive`](../../shelves/systems-architecture/data-intensive/SKILL.md) |

## Books in this shelf

- [`data-pipelines`](../../shelves/data-and-pipelines/data-pipelines/SKILL.md) — *Data Pipelines Pocket Reference* (James Densmore). Practical patterns for ingestion, transformation, scheduling, and observability.

## Disambiguation

- **data-pipelines vs data-intensive (DDIA):** data-pipelines is *operational* — how to build and run a pipeline today. DDIA is *architectural* — what storage and replication primitives the pipeline rests on. Read both for greenfield work.
- **The original wondelai `data-intensive-patterns` skill is intentionally not here**; it duplicates `systems-architecture/data-intensive/` (DDIA) — see plan §2 overlap resolution.

## Source attribution

See per-book `SKILL.md` footers and the repo-root [`THIRD_PARTY_NOTICES.md`](../../../THIRD_PARTY_NOTICES.md).
