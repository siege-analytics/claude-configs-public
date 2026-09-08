# Source: Designing Data-Intensive Applications

Bibliographic source: Martin Kleppmann, *Designing Data-Intensive Applications: The Big Ideas Behind Reliable, Scalable, and Maintainable Systems*, O'Reilly Media, First Edition, March 2017, ISBN 978-1-449-37332-0.

## Repository handling

The user provided a PDF copy for review. The PDF itself is copyrighted and is **not** redistributed in this repository. This shelf contains short, original notes and review prompts derived from the book's publicly citable structure and concepts, not copied book text.

## Shelf coverage map

| DDIA area | Shelf file |
|---|---|
| Ch. 1: reliability, scalability, maintainability | `fault-tolerance.md` + `SKILL.md` quick diagnostics |
| Ch. 2: data models and query languages | `data-models.md` |
| Ch. 3: storage and retrieval | `storage-engines.md` |
| Ch. 4: encoding and evolution | `data-integration-correctness.md` |
| Ch. 5: replication | `replication.md` |
| Ch. 6: partitioning | `partitioning.md` |
| Ch. 7: transactions | `transactions.md` |
| Ch. 8: trouble with distributed systems | `consistency-consensus.md` + `fault-tolerance.md` |
| Ch. 9: consistency and consensus | `consistency-consensus.md` |
| Ch. 10-11: batch and stream processing | `batch-stream.md` |
| Ch. 12: future of data systems | `data-integration-correctness.md` |

## Citation discipline

When using this shelf in artifacts or reviews, cite it as a framework source rather than quoting the book. Prefer:

> Applied the DDIA data-systems checklist: data model, storage engine, replication, partitioning, transaction/isolation, distributed-systems assumptions, and derived-data correctness.

Do not paste long excerpts from the PDF into tickets, PRs, rules, or generated docs.
