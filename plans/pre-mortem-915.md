---
ticket_refs:
  - siege-analytics/claude-configs-public#915: comment posted (https://github.com/siege-analytics/claude-configs-public/issues/915#issuecomment-5675260648)
---

# Pre-mortem: siege-analytics/claude-configs-public#915

Implementation may proceed: YES

## Tigers

### Tiger 1 -- Severity: Track
**Scenario:** a peer thread with no activity for over `stale_seconds` (default 3600s) gets pruned from `open_threads` while the hub still considers the exchange meaningful (e.g. waiting on a slow reply). If the hub later messages that same peer again, the hook no longer sees it as "already open" (`hooks/agent-comms/hub-concurrency-gate.sh`, continuing-thread branch checks `target in peers`) -- it's re-treated as a *new* thread-open, consuming a cap slot a second time.
**Ground:** direct read of the patched hook's control flow; `peers` is recomputed from the post-prune `open_threads` list before the continuing-vs-new check.
**Coherence check:** consistent with the cited code path -- prune happens strictly before `peers` is derived, so a pruned peer is never in `peers` for the rest of that invocation.
**Why Track, not Launch-Blocking or Fast-Follow:** this hook only gates the hub's own *outbound new-thread opens* -- it never blocks inbound replies, so no message is lost and no reply path breaks. The worst case is the cap engaging one slot sooner than an unpruned world would. Mitigation: `HUB_THREAD_STALE_SECONDS` is operator-tunable per the existing `HUB_THREAD_CAP` override pattern if this proves disruptive in practice.

## Paper Tigers

### Paper Tiger 1
**Scenario sounds concerning:** concurrent `PreToolUse` hook invocations could race on a read-modify-write of `hub-threads.json`, with the second write clobbering the first.
**Why it's handled:** this race exists identically in the pre-fix code (the original append-on-allow logic already does an unsynchronized read-modify-write) -- this PR does not introduce or worsen it. `PreToolUse` hooks for a single session's tool calls execute sequentially, one call at a time, per session turn.
**Citation:** `hooks/agent-comms/hub-concurrency-gate.sh` state-file resolution comment block (session-scoped path is the primary resolution target).

### Paper Tiger 2
**Scenario sounds concerning:** a hand-edited or buggy `last_activity` timestamp set in the future would make `(now_dt - parsed).total_seconds()` negative, permanently defeating the prune for that entry.
**Why it's handled:** the gate is the sole *normal* writer of `last_activity` (it always writes `now`). A hub that hand-edits the file to defeat its own cap already has a strictly more direct option (delete the entry outright, the documented drain path) -- not a new attack surface, and the file is session-local, not exposed to any untrusted input.

## Elephants

### Elephant 1
Enforcement of this whole hook class may be advisory rather than hard-blocking under some Craft Agent runtimes (`NOTE (#335)` in the hook's own header, inherited unchanged by this PR). Out of scope for this PR -- already flagged by the original P1 author, tracked separately.

### Elephant 2
The default staleness threshold (3600s) is a reasoned default (matches this workspace's observed ~20-30 min hub check-in cadence with margin), not an empirically-derived-across-the-whole-fleet number. Deferred: the env-override mechanism exists precisely so the default can be revisited once real usage data accumulates, mirroring how `HUB_THREAD_CAP` is also a flat default rather than data-derived.
