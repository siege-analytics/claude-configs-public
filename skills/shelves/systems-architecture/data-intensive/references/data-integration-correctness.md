# Data Integration and Correctness

Use this reference when a system creates derived data: caches, search indexes, analytics tables, read models, feature stores, exports, event streams, materialized views, or reports. The review question is not just "does the job run?" but "can every derived state be explained, rebuilt, and verified from its source of truth?"

## Core model

A data system is often a network of specialized stores. Correctness comes from making the source of truth, derivation path, schema evolution, replay semantics, and verification checks explicit.

## Derived-data checklist

| Question | Why it matters | Evidence to require |
|---|---|---|
| What is the system of record? | Without one source of truth, conflicts become policy-by-accident. | Named table/log/API with ownership and retention. |
| Is every derived store rebuildable? | Caches and indexes will drift or need schema changes. | Replay plan, backfill command, or documented non-rebuildable exception. |
| How are changes propagated? | Dual writes lose updates under partial failure. | CDC, outbox, event log, transactionally written job input, or explicit reconciliation. |
| Are schemas versioned? | Long-lived data outlives code deploys. | Compatibility rule: backward, forward, full, or migration window. |
| What are replay and idempotency semantics? | Retries and backfills are normal. | Stable event IDs, merge/upsert keys, deterministic transforms, checkpoint behavior. |
| How is timeliness measured? | Freshness and correctness are different promises. | Lag metric, watermark, SLA/SLO, late-data policy. |
| How is integrity verified? | Trusting pipelines silently accepts corruption. | Row counts, checksums, reconciliation queries, sampled end-to-end traces, or invariant tests. |

## Schema evolution prompts

- Can old readers read new data?
- Can new readers read old data?
- Are default values, optional fields, and enum expansions safe?
- Is deletion/removal staged through deprecation before producers stop sending fields?
- Is the compatibility boundary the database schema, message schema, API response, file format, or all of them?

## Dataflow modes

| Mode | Use when | Watch for |
|---|---|---|
| Database-backed dataflow | State changes are primarily table writes. | Triggers, migrations, transaction boundaries, and replica lag. |
| Service/API dataflow | Systems communicate by request/response. | Idempotency keys, retry behavior, timeout budgets, partial failure. |
| Message/log dataflow | Consumers derive state asynchronously. | Ordering, partition keys, dedupe, poison messages, replay/backfill. |
| Batch dataflow | Inputs are bounded snapshots. | Snapshot consistency, partition discovery, late files, rerun semantics. |
| Stream dataflow | Inputs are unbounded event streams. | Event time vs processing time, watermarks, windowing, state recovery. |

## Correctness over convenience

- Avoid direct dual writes to two independent systems unless both writes are in a single transaction or a compensating reconciliation process exists.
- Prefer an append-only event/change log for auditability and replay when history matters.
- Make derived state disposable: if the index/cache/table cannot be rebuilt, it is no longer merely derived and needs stronger durability/governance.
- Separate timeliness from integrity: a stale but correct report and a fresh but corrupted report are different failures.
- For privacy-sensitive data, minimize derivations; every copy expands retention, deletion, and access-control obligations.

## Reviewer red flags

- "We will just update Elasticsearch after the database write."
- "Backfill is manual" with no command or tested plan.
- "Exactly once" without idempotent sink writes or transactional offset handling.
- `mergeSchema` or schema-on-read flexibility without consumer compatibility checks.
- Reports/exports with no row-count reconciliation against the source.
- Cache invalidation described only as TTL, when correctness requires invalidation on writes.
- Feature tables without point-in-time correctness or lineage.

## Related skills/rules

- `code-review` -- data integrity and performance review checklist.
- `self-review` -- data-engineering affirmative standards.
- `spark`, `databricks`, `sql`, `postgis`, `sedona` -- implementation-specific dataflow and storage guidance.
