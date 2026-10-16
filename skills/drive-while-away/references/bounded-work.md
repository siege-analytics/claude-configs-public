# Bounded work checkpoints

Use `scripts/work_cycle.py` beside this skill for a local durable checkpoint of
one work item. It complements the existing session-coordination rules and
[skill:stalled-session-recovery]. The same helper and reference ship with the
skill in both layouts. It requires Python 3.10+ on macOS or Linux (`fcntl`).

This is coordination metadata, not a policy resolver, authorization record,
review verifier, timer, message transport or scheduler. Its output always says
`authorization: not-evaluated`. An accepted review is a **reported** external
verdict: independently inspect its source, candidate SHA and applicable gates
before any consequential action. A passing local test or recorded checkpoint
cannot grant permission. Integrations with #848/#851 must consume their reviewed
contracts; this helper neither reads nor changes those decisions.

## Operating cycle

1. Announce the objective, bounded chunk and expected evidence. Select explicit
   heartbeat, chunk and repeated-failure budgets from applicable host/session
   instructions. The values below are examples, not universal kernel rules.
2. Read the journal before each chunk. Reconcile the live candidate, checks,
   reviewer status and unresolved findings. A queued reviewer remains queued
   until an actual start is observed. Do useful work within the selected chunk.
3. Record receipts and a checkpoint, then publish a concise update in the user
   channel and relevant issue/PR. Include state, what changed, evidence, next
   action and any decision needed. Before a planned wait longer than the
   heartbeat, publish a `waiting` checkpoint naming the dependency. Respect a
   stricter host limit. The helper only reports time due when invoked; the host
   must supply interruptible waits/timers. It cannot enforce cadence inside a
   hung tool or wake a terminated session.
4. Read without writing for unchanged polls. `changed: false` means no new
   transition to announce. Acknowledge a handoff once; do not acknowledge an
   acknowledgement. A new message ID is not itself progress. Scheduled heartbeat
   updates can explain continued waiting, but do not reset `last_progress_at`.
5. At a meaningful phase boundary, give the operator a chance to steer. A design
   fork or exhausted failure budget names the concrete alternatives and trade-offs.
   Stop automatic edits to the suspended approach; keep independent authorized
   work and read-only diagnosis available. A coordinator records an already made
   decision with its evidence; the record does not create authority to decide.

`working` means a bounded chunk is underway; `waiting` names an external result;
`blocked` names an obstacle; `needs-input` names a decision; `complete-for-review`
means a candidate and evidence are ready for review, not that review/CI/merge
has finished. Suspended approaches are visible even during independent work.
Do not describe a merely overdue heartbeat as a stalled session: consult the
last coherent transcript and actual tool state using the recovery skill.

## Start a journal

Keep journals and receipts outside tracked source (or in a private session
artifact directory). Use one shared local journal per work item. Separate
copies on separate hosts do not share a lock; coordinate those via the existing
issue/PR owner instead. Do not put secrets or private transcript excerpts in
public receipts. All actor names and evidence strings are caller supplied,
not authenticated or cryptographically verified.

Save this as `init.json`, replacing the example timestamp with current Unix
seconds and selecting budgets appropriate to the session:

```json
{
  "id": "start-1005",
  "actor": "hub",
  "generation": 1,
  "at": 1792116000,
  "kind": "init",
  "data": {
    "objective": "Finish the bounded checkpoint pilot",
    "scope": "One coordination work item; no rollout",
    "owner": "worker-1",
    "coordinator": "hub",
    "heartbeat_seconds": 60,
    "chunk_seconds": 600,
    "failure_budget": 2,
    "next_action": "Implement and run focused scenarios"
  }
}
```

From this skill directory (use the resolved installed path for your layout):

```sh
python3 scripts/work_cycle.py /path/to/session/work.json --event init.json --expect 0
python3 scripts/work_cycle.py /path/to/session/work.json
```

The parent directory must exist. Each write requires the latest `revision` via
`--expect`. Reload after a conflict; do not blindly retry with a new revision.
The sidecar lock and atomic replacement prevent lost updates on a local POSIX
filesystem. Replay validates the event sequence after restart; it does not
detect malicious edits to this trusted local file. It creates no git hook or
global approval gate and has no network side effects.

Every event has the same envelope: unique stable `id`, `actor`, current ownership
`generation`, nondecreasing integer `at`, `kind`, and exactly the listed `data`
fields. Retry a delivery with the **identical event**; an ID reused for different
content rejects. The owner emits normal receipts; the named coordinator records
decisions and supersession. IDs/generations prevent accidental stale writes,
not hostile impersonation by another process with file access.

| Kind | Data fields | Effect |
| --- | --- | --- |
| `checkpoint` | `state`, `summary`, `next_action`, `dependency`, `wait_seconds`, `evidence` | Explicit heartbeat/chunk boundary. Waiting, blocked and needs-input require a dependency. A working checkpoint begins the next bounded chunk. |
| `candidate` | `sha` | Exact lowercase 40-character SHA; a change resets review/check status and retains invalidated history. Findings and failure counts survive. |
| `review` | `sha`, `verdict`, `evidence`, `failure_class` | Verdict: queued, active, accepted, changes-required or unavailable. Nonempty failure class only for changes-required. Evidence is a nonempty array of references. |
| `checks` | `sha`, `status`, `evidence` | Pending, passed or failed for the current SHA. Never resolves a finding or accepts a review. |
| `finding` | `finding_id`, `summary`, `evidence` | Records an unresolved falsification and invalidates current acceptance. |
| `resolve-finding` | `finding_id`, `evidence` | Records resolution evidence; a fresh review receipt is still needed. |
| `decision` | `failure_class`, `choice`, `evidence` | Coordinator records the design choice for a suspended approach. Resets only that class's budget; prior failures/reviews remain in the journal. |
| `interrupt` | `reason` | Preserve objective, SHA, evidence and unresolved decisions, enter waiting. |
| `resume` | *(empty object)* | Preserve records, require reconciliation before working. Never manufactures a review verdict. |
| `supersede` | `owner`, `reason` | Coordinator changes the one current owner, increments generation and requires successor resume/reconciliation. |

## Concrete transitions

Healthy chunk: `init → candidate(A) → checks(A, passed) →
checkpoint(complete-for-review) → review(A, queued) → review(A, active) →
review(A, accepted)`. Checks and external review remain distinct. Publishing
the last artifact includes an explicit baton naming the next action.

Waiting: after requesting review, checkpoint with `state: waiting`,
`dependency: "PR review at SHA A"`, `wait_seconds: 90`, and the review URL.
Publish it before waiting. Poll by reading only. Queued/active receipts and
waiting checkpoints do not count as material progress.

Needs input: `candidate(A) → rejected(parser-ambiguity) → candidate(B) →
rejected(parser-ambiguity)` reaches a budget of two for that class. Present
redesign, reduced scope, and continued repair trade-offs. New SHAs alone do not
consume the budget. Duplicate identical receipts do not increment it. Class
assignment is human/model judgment; renaming the same failure is not a reset.

Recovery: for safe-mode, rate-limited, wrong-scope or context-exhausted reviewers,
record `review(unavailable)` with the diagnostic reference, then a `blocked`
checkpoint naming the corrective action. Diagnose using the recovery skill;
do not infer a stall from elapsed time alone. If supersession is appropriate,
the coordinator records `supersede(worker-2, reason)`. The successor reads the
journal, inspects actual live state, records `resume`, then checkpoints the next
bounded chunk. Generation-1 writes from worker-1 reject after generation 2.
Pending review stays pending, unresolved findings survive, and changed candidate
SHAs cannot inherit earlier accepted verdicts. This metadata does not cancel a
running predecessor or revoke its host permissions; coordinate/stop that session
through the host before concurrent mutation.

The deterministic suite is `python3 bin/_test/work_cycle_test.py` from the source
repository. It exercises long rejection chains, duplicate delivery, resume,
supersession, competing writers, and green-CI-versus-falsification separately
from progress reporting. Local simulations are not live Craft/Codex canaries;
host capability/visibility claims belong to #1003.
