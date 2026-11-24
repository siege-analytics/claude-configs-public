# Consistency, Clocks, and Consensus

Use this reference when a design depends on distributed truth: leader election, distributed locks, cross-node transactions, replicated reads, global ordering, idempotent retries, or claims such as "exactly once", "strong consistency", or "no stale reads".

## Core model

Distributed systems fail partially: one node can be healthy while another is slow, partitioned, paused, or seeing a different message order. Do not review these systems as if there were one global clock and one shared memory.

## Review checklist

| Question | Why it matters | Acceptable answer |
|---|---|---|
| What consistency guarantee is promised? | "Consistent" is ambiguous. | Names the guarantee: read-your-writes, monotonic reads, consistent prefix, linearizability, serializability, causal consistency, or eventual convergence. |
| What is the ordering source? | Cross-node order is not free. | Single leader log, consensus log, database transaction order, partition-local offset, Lamport/vector clock, or explicit "no cross-key order promised". |
| What clock is used? | Wall clocks can jump; process pauses break timing assumptions. | Monotonic clock for durations/timeouts; wall clock only for human timestamps or bounded-staleness with documented uncertainty. |
| What happens during network partition or coordinator pause? | Partial failure is normal, not exceptional. | Safety-first behavior is declared: reject writes, degrade reads, queue work, fence stale leaders, or accept eventual convergence with conflict semantics. |
| Does a quorum assumption actually hold? | Sloppy quorum and hinted handoff weaken the usual `w + r > n` intuition. | Specifies replica set, `n/r/w`, failure domains, read repair/anti-entropy, and whether quorums are strict or sloppy. |
| Is leader election fenced? | Split-brain corrupts data. | Uses epochs/terms/tokens and rejects stale leaders after failover. |
| Is "exactly once" really end-to-end? | Processing guarantees often stop at framework boundaries. | Idempotent outputs, transactional sink, dedupe key, or explicit at-least-once semantics with safe replay. |

## Consistency vocabulary

- **Linearizability**: each operation appears to take effect atomically at one point between request and response. Useful for locks, uniqueness, leader election, account balances, and other coordination-critical state. Expensive across regions.
- **Serializability**: transactions behave as if run one at a time, even if actually concurrent. This is about transaction isolation, not necessarily real-time order.
- **Causal consistency**: causally related operations are observed in causal order; unrelated concurrent operations may be seen in different orders.
- **Eventual consistency**: replicas converge if writes stop. Not enough by itself; name the conflict-resolution rule and convergence mechanism.

## Common traps

| Trap | Safer review response |
|---|---|
| "We use timestamps, so latest wins." | Ask whose clock, clock skew bounds, monotonicity, and whether lost concurrent updates are acceptable. |
| "Kafka gives exactly once." | Ask whether the sink write and offset commit are atomic and whether external side effects are idempotent. |
| "Quorum means strong consistency." | Check strict quorum membership, stale reads, sloppy quorum, read repair, and concurrent write reconciliation. |
| "The lock is in Redis." | Check fencing tokens and what happens if the lock holder pauses past TTL. |
| "Serializable" assumed from ACID. | Check the database's actual isolation level and test write skew/phantoms when invariants span rows. |

## Design moves

- Prefer single-writer or partition-local invariants when possible.
- Use consensus systems (Raft/Paxos-backed stores, etcd, ZooKeeper, database consensus) only for small coordination state, not high-volume data paths.
- Fence every lease/lock with a monotonically increasing token accepted by the protected resource.
- For multi-region systems, explicitly choose between local latency and global linearizability; do not imply both.
- Treat safety properties as non-negotiable; trade liveness/availability first when a partition forces a choice.

## Related shelf files

- `replication.md` -- leader/follower, multi-leader, leaderless replication and lag anomalies.
- `transactions.md` -- isolation levels, write skew, serializability, and 2PC trade-offs.
- `fault-tolerance.md` -- partial failure, timeouts, safety/liveness, Byzantine fault assumptions.
