---
name: shelf-systems-architecture
description: Router for systems-architecture book skills. Dispatches to data-intensive, system-design, microservices-patterns, release-it, high-perf-browser, or system-design-interview based on task signals. Read this when designing distributed systems, choosing storage engines, planning replication or partitioning, hardening for production failure modes, or preparing for system-design interviews.
disable-model-invocation: false
---

# Systems Architecture — Shelf

Books on designing distributed systems, choosing storage and compute primitives, and surviving in production.

## Trigger table

| Task signal | Book to read |
|---|---|
| Storage engine choice (LSM vs B-tree, SQL vs NoSQL), replication, partitioning, transactions, consistency models, batch vs stream | [skill:data-intensive] |
| End-to-end system design — load balancers, caches, queues, capacity estimation, back-of-envelope math | [skill:system-design] |
| Service decomposition, sagas, API gateway, service discovery, distributed data patterns | [skill:microservices-patterns] |
| Production failure modes — circuit breakers, bulkheads, timeouts, capacity, "what breaks at 3am" | [skill:release-it] |
| Browser performance, latency budgets, HTTP/2/3, CDN, image optimization, critical-path render | [skill:high-perf-browser] |
| Tech-interview prep — design YouTube, Twitter, Uber, Dropbox; capacity drills | [skill:system-design-interview] |

## Books in this shelf

- [skill:data-intensive] — *Designing Data-Intensive Applications* (Kleppmann). Storage engines, replication, partitioning, transactions, batch + stream.
- [skill:system-design] — System design fundamentals: load balancing, caching, queues, capacity planning.
- [skill:microservices-patterns] — Chris Richardson. Service decomposition, sagas, distributed data, API gateway.
- [skill:release-it] — Michael Nygard. Stability and capacity patterns; production failure modes.
- [skill:high-perf-browser] — *High Performance Browser Networking* (Grigorik). Network primitives and frontend latency.
- [skill:system-design-interview] — Alex Xu. Common interview design problems, walkthroughs.

## Disambiguation

- **data-intensive vs system-design:** DDIA goes deep on the *storage layer*; system-design covers the *whole stack* at coarser resolution. Designing a feature → start with system-design; choosing a database → DDIA.
- **microservices-patterns vs system-design:** microservices-patterns assumes you've decided on services; it tells you *which patterns* to use. System-design is upstream of that decision.
- **release-it vs the rest:** Read release-it before going to production, not when designing on a whiteboard.

## Source attribution

See per-book `SKILL.md` footers and the repo-root [`THIRD_PARTY_NOTICES.md`](../../../THIRD_PARTY_NOTICES.md).
