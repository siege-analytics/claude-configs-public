---
name: stalled-session-recovery
description: How to diagnose and recover a session that has stopped producing useful turns -- stuck on a repeating error, silent for an abnormal stretch, or looping on the same tool call. Invoke when checking on a session that "seems stuck," when a session's own error looks like it should have cleared but hasn't, when a hub is deciding whether to nudge or respawn a worker, or when auditing a fleet of sessions for health. Covers three failure shapes (transient error, persistent misconfiguration, wedged tool call) with distinct diagnostics and distinct fixes, the discipline of reading the last coherent content instead of trusting the error label, and how to respawn without duplicating work or losing in-flight state.
allowed-tools: Read Grep Glob Bash mcp__session__get_session_info mcp__session__list_sessions mcp__session__send_agent_message mcp__session__spawn_session mcp__session__archive_session mcp__session__list_background_tasks
---

# Stalled-Session Recovery

A session that has stopped producing useful turns is not one problem -- it is at least three different problems that happen to look similar from the outside. Treating all of them the same way (wait, or nudge-and-wait) fixes one and wastes hours on the other two. This skill is the diagnostic-then-fix procedure, and the discipline that makes it reliable: **never classify a stalled session from its error's `errorCode`/`errorTitle` alone.** Read the last *coherent* content before deciding what happened.

Before choosing a repair, read [host controls and deployment navigation](host-controls.md). Verify actual supported controls, current operation state and your existing authority. An observation timeout is not proof that the operation stopped. Preserve actual owner holds and continue independent authorized work.

## When to invoke

- Checking a session at its duration/context checkpoint, or one that "seems stuck" or has not produced useful progress.
- A session's own error (rate limit, timeout, generic failure) looks like it should have cleared on retry, but hasn't after several attempts.
- You are a hub (see `hub/SKILL.md`) deciding whether to nudge a worker once more or replace it.
- Auditing a fleet of sessions for health, e.g. before a large coordinated action.

## Duration checkpoints and session renewal

Workspace Config owns session health and renewal; hubs report evidence about
their workers and TC keeps delivery ownership current. Choose a renewal interval
**D** appropriate for the role and expected work, using an existing supported
health sweep or return event. Unless the role sets another interval, use **D =
4 hours of active session time**. Workspace Config must include active sessions
in a recurring health sweep at least hourly; do not create a separate timer per
session by default. A checkpoint is an execution trigger, not a reason to wait
for an operator prompt.

At each checkpoint compare the unfinished objective with actual recent tools
and results, current instructions, pending messages/tools and the event that
will resume the work. A Working label or status summary alone is not progress.
Then keep the mission moving while applying these lifecycle rules:

- **D reached with active work:** start a successor handoff as routine
  maintenance even when the predecessor is healthy; D is not a stuckness
  judgment. The predecessor keeps its current ownership and continues
  eligible work until the successor has accepted the handoff and produced a
  useful, non-overlapping turn. Transfer ownership exactly once before the
  successor writes, reconcile pending operations and return routes, then retire
  the predecessor. Do not wait for context failure
  or an operator acknowledgment.
- **Context pressure reaches the host's renewal warning:** start that same
  handoff immediately rather than waiting for D. Do not require an in-place
  context refresh first. If the host exposes no
  warning, use 75% of usable context as the renewal threshold. Include the
  context evidence and a compact, durable checkpoint so the successor starts
  with room to work.
- **No active work or real dependency:** mark the session and any completed,
  duplicate or superseded children as archive candidates after verifying that
  no open task, pending return, live operation or required audit history still
  depends on them. Preserve the transcript and durable handoff; do not leave
  completed children attached as if they still own work.
- **Missing wake-up or unnecessary stop:** deliver the missing result, correct
  the mistaken restriction, or route the next concrete step under the existing
  grant. Do not use a fresh session to avoid repairing a failure that it would
  inherit.
- **Credential/configuration failure or an uncertain live mutation:** use the
  corresponding diagnosis below. Respawning with the same expired connection
  is not recovery; replacement does not settle an operation's unknown outcome.

Use the host's supported trigger for D (health sweep, scheduled check or return
event) and verify that it actually runs. If the host cannot schedule checks,
Workspace Config must keep D in its normal recurring workspace sweep and act
on it there; do not claim automatic renewal until a real check and successor
handoff have been observed. Renewal must not interrupt unrelated mission work.

For renewal, save the unfinished outcome, next executable step, task/board
ownership, exact source and evidence references, real holds and pending
operations. Settle concurrent ownership before the successor writes. Confirm
that the successor has accepted that objective and produced a useful turn,
not merely a spawn receipt, before retiring the predecessor through supported
controls. Actual acceptance satisfies this condition; do not add a separate
Root/operator acknowledgment. Carry forward existing authority and real holds,
not obsolete waiting instructions. Mark an ended predecessor for cleanup only
after its durable handoff and retirement conditions are satisfied.

This procedure does not itself install a scheduler or guarantee background
execution. Verify the configured trigger and a real resulting check before
claiming automatic supervision or renewal is active.

### Make the trigger operational

Workspace Config owns closing this loop. A skill rule or an enabled schedule is
not proof that renewal is running. In the target workspace, verify all of the
following and repair a missing piece within the existing grant:

1. One recurring health check is enabled and runs at least hourly. It measures
   active time against **D** and the host's usable-context warning. On Craft
   workspaces that persist readable `session.jsonl` files, it also measures
   transcript bytes against the size threshold above. On other hosts, use the
   strongest supported context metric and record when byte size is unavailable.
   The check must reach the workspace's actual session inventory.
2. Automation history shows a completed check and its result. A scheduler tick,
   successful prompt-session creation, queued message, or `needs-review` status
   alone proves dispatch, not inspection, handoff, or recovery.
3. When a trigger is met, the check resumes the owning steward/hub and carries
   out the successor handoff in this skill. Do not downgrade a measured size or
   context trigger to a notification-only report because an unrelated scan,
   gate, or owner callback failed. Use supported native session reads or a
   narrower read-only inspection to establish the affected session's state;
   route a genuine hook defect for repair while continuing decisions supported
   by the evidence already obtained. Never bypass the gate or repeat an
   unchanged refused command.
4. A scheduled prompt that creates a separate session for each run must close
   its own run. `done` means this inspection episode finished; it does not
   claim the monitored mission is complete. After recording the result and
   delivering any deduplicated notification or continuation, set the run to
   `done` and mark it `delete-me`. Do not leave periodic runs in `needs-review`
   while waiting for a peer to consume a queued message or resolve the larger
   mission; keep that return in the existing durable task/ledger. Reserve
   `needs-review` for a decision the operator must make before this run can
   continue. Preserve the run transcript and durable result. Verify that the
   configured cleanup process consumes the marker; marking a session is not
   physical deletion.

Routine workspace-session inspection and lifecycle work are part of Workspace
Config's assigned maintenance role. Use the host's native session inventory,
message, spawn, status, label and retirement controls within that role. Do not
invent a business Task, review tier, posted artifact or operator GO as a
prerequisite for those native maintenance actions. Keep genuine host checks,
live-operation settlement, successor acceptance and role boundaries intact.
When an unrelated file gate blocks a compound inventory command, use supported
native session reads for the measured candidates and route the exact gate defect
without making that repair a prerequisite for a qualifying handoff.

If the host cannot inspect session size, preserve task ownership, start a
successor, or retire a settled predecessor, identify that exact missing
capability and route its repair to the owner. Do not report automatic renewal as
active until a measured trigger has resulted in an accepted successor and a
cleaned-up predecessor on the live host.

### End-to-end recovery acceptance

Treat recovery as complete only when the intended user-facing session works
again. A deployment stamp, healthy process, session-list entry, retained child
count, successful spawn, or queued message is useful evidence, but none proves
that a person can resume the conversation.

For each target session, verify the following through supported host controls:

1. The conversation loads without a connection or history-retrieval failure.
2. Its selected backend is available for that session. Do not infer backend
   health from the provider name appearing in a dropdown.
3. A harmless test message receives a response in the recovered session. If
   the predecessor cannot be loaded, verify that a successor accepted the
   handoff and that the successor also loads and answers a harmless test
   message.
4. The resumed conversation has the durable objective, last confirmed state,
   next action, pending returns, and genuine holds. Confirm these from the
   conversation or accepted handoff, not from a spawn receipt.
5. Required hub/steward peer levels, child ownership, and return routes match
   the intended workspace hierarchy.

Report recovery per session against these checks. If loading or a test turn
fails, name the observed host/backend failure and keep the task's checkpoint
and next supported recovery action visible; do not call the session restored
because package deployment or metadata repair succeeded. A failed session
does not suspend independent work elsewhere in the workspace. Do not send
test content that mutates project state, change authentication, or remove a
provider as a diagnostic shortcut.

### Transcript-size checkpoint

Measure the stored `session.jsonl` size alongside model-context usage. Craft's
documented Pi/Bun WebSocket implementation can reject logical messages above
16 MiB even when the Node implementation permits 100 MiB. A large transcript
may therefore break UI/session loading before the model reports context
exhaustion. Use 8 MiB as the proactive renewal threshold by default. If the
host advertises a lower maximum, set the threshold below that cap (for example,
half the advertised maximum). Keep the evidence packet and successor prompt
compact. A `sessions:getMessages` timeout (for example,
`30000ms`) while opening a large session is a concrete retrieval failure
signal: stop repeating full-history reloads and renew through supported session
controls. The threshold is a conservative trigger, not a claim that every
session load serializes the entire file or that every server uses Bun. Create a
successor with the active objective, verified state, evidence paths, owners,
real holds and return routes. Do not truncate or rewrite the predecessor
transcript. Preserve it as the read-only record and retire it only after the
successor has accepted the work and produced a useful turn.

Crossing the measured byte threshold triggers renewal in that sweep when the
session still owns an unfinished objective, active dependency or pending return
that needs a successor. Do not spawn a successor for completed work merely
because a stale `active`/`todo` status or large transcript remains: verify the
objective is terminal, preserve required audit history, and mark the session
for the normal archive path. For unfinished work, token usage and session
status do not override the measured transcript size.

## The three failure shapes

Do not assume the shape from the error message. Confirm it from the transcript.

### 1. Transient error (genuinely short-lived)

Last few transcript entries alternate an operator/system retry ("try again") with an error, and the error is a real, narrow, rate/quota-shaped failure that has not persisted long or shown a worsening pattern.

**Fix:** nudge once with a message asking it to continue. If it recovers, done. If the *same* error recurs after the nudge, stop treating it as transient -- move to shape 2 or 3 below. Do not nudge repeatedly hoping the Nth attempt is the one that clears; that is shape 2 wearing shape 1's clothes.

**A real transient error backs off; a masked one does not.** Retry gaps that grow between attempts are consistent with real backoff. Retry gaps that stay flat or *shrink* between attempts are not -- that is a tell the label is wrong, not that the system is under more load.

### 2. Persistent misconfiguration (will never clear on its own)

Every attempt fails identically, because the request itself cannot succeed, not because a shared resource is temporarily exhausted. Two common concrete causes, both observed producing a generic "rate limited"-shaped error in practice:

- **Wrong model/connection pair for the account tier** -- e.g. a model listed as selectable for a connection but not actually supported for that specific account type. Every turn errors immediately, with no other activity in between.
- **Missing or invalid provider authentication** -- the session cannot obtain credentials for its configured connection. Verify this through the host's supported connection-status control; do not diagnose from the generic error text alone. A successor configured with the same unauthenticated connection will fail the same way.
- **Oversized single request** -- e.g. a large diff pushed as one API call. Look for the session's own words a few turns *before* the error run starts; a model that already said something like "the JSON body was too large for a single API call, I'll split this into multiple commits" and then never got the chance to is exactly this shape. Retrying the identical oversized request fails identically forever.

**Fix:** inspect the host's supported configuration, authentication status and retry controls. If an authorized in-place correction or credential refresh is available, apply it and observe a real successful turn. Otherwise select a verified authenticated provider that fits the task and the operator's constraints. If no such provider or supported re-authentication route is available, keep independent authorized work moving and route one precise owner re-auth action with the evidence and return path; do not retry the unchanged failing request, repeatedly spawn against it, transfer raw credentials, or declare the objective complete. For oversized requests, chunk the work before resuming. Preserve the original objective, task state and specific correction.

### 3. Wedged session (a stuck tool call, not a stuck request)

The most dangerous shape because it looks the most "alive." A single tool call gets stuck in an executing state indefinitely and never returns, so the turn never completes and the session can never process new input -- but `session.jsonl` keeps growing, because something (a heartbeat, a polling loop) keeps firing on a fixed interval underneath the stuck call.

**Signature:** a long run (dozens to hundreds) of consecutive tool-call entries, same tool name, at a fixed interval (e.g. every ~30s), sharing one parent tool-use id, with **no assistant text in between** and often empty tool input. This is different from a genuinely busy session dispatching to many workers, which shows *varied* targets/content and assistant narration describing what it's doing between calls. Grep the tail for an unbroken run of tool-type entries with zero interleaved assistant-type entries; a run in the hundreds, spanning hours, is the signature -- a handful is not.

**Fix:** read backward from where the loop *started* (not the tail) to recover the last coherent state, pending tools and incomplete mutations. Inspect supported native interruption controls. Use one only within the existing grant, observe its result, and reconcile durable state before resuming or starting a successor. If interruption is unavailable or fails, report that specific live operation and use the successor procedure only when concurrent ownership is settled. Carry forward the failure diagnosis and instructions not to reproduce it; use supported scheduling/monitoring rather than an unbounded manual polling call.

An archive refusal such as "currently processing a turn" reports a current host state; it does not by itself prove the session is wedged or that its tools stopped. Inspect supported controls and the live operation. Do not loop the same failing archive request. Preserve the predecessor until successor ownership, evidence and any required retirement conditions are settled.

## Diagnostic procedure (apply before deciding anything)

1. **Do not read only the last line.** Read the last several non-error entries -- specifically the last *assistant* content before the error run began, not just the trailing error.
2. **Look for an explicit statement of the real problem**, stated by the session itself shortly before it went quiet (an oversized-payload complaint, an "I don't have enough context to answer" admission, a mid-operation status line).
3. **Compare transcript size/density against comparable healthy sessions** (same role, similar age). A session that has grown unusually large per-message relative to peers, especially one that is *already* a successor spawned because an earlier predecessor exhausted a context/quota budget, is a candidate for shape 2 (context exhaustion presenting as a generic error) even without an explicit "too large" message. Compare its byte size with the host's advertised WebSocket cap too; a transport-size failure can present as a generic disconnect even when model context remains available.
4. **Check for an incomplete live mutation.** If the last coherent lines describe applying/writing/deploying a multi-step change and the count of "done" doesn't match the count "expected" (e.g. "all 5 objects match... applying now" followed by "all 4 objects applied"), the operationally important fact is the incomplete mutation, not the error label. The successor's first job is to verify actual live state against the intended end state -- not to blindly retry the operation, and not to assume nothing landed.
5. **Check for a live tool-call loop** (see shape 3's signature) before concluding "just busy" or "just quiet."

## Before respawning: check for a superseding session

Do not respawn a stuck session's exact original task without checking whether it has already been picked up elsewhere. Search for other active sessions on the same ticket/scope (`list_sessions`, search by ticket number or topic). If one exists and is active, either skip the respawn (archive the stuck one only) or fold "your original task may be superseded, check with X first" into the respawn prompt instead of repeating stale instructions. This is the stalled-session-recovery instance of the hub federation query protocol (`hub/SKILL.md` Part 4) -- the same duplicate-work risk applies whether the collision is between two live hubs or between a stuck session's stale task and a newer session already covering it.

If the failure involved provider authentication or model availability, check the candidate successor's connection and model through the host's supported status controls before sending its handoff. Do not start another session with the same failed configuration. If no working connection exists, keep the handoff and task visible, pursue independent work, and route the specific re-authentication action to the credential owner.

Check the session's status against its bounded objective and durable handoff.
A terminal status with a verified completed or transferred objective needs no
replacement, even if it has a trailing cosmetic error. A terminal label alone
does not establish completion: if assigned work remains, reconcile actual
ownership and pending results, then apply the checkpoint procedure above.
Resume the existing owner or deliver the missing event where that suffices;
do not automatically respawn or silently discard the unfinished objective.

## Respawning: what the successor needs

### Preserve the role and its mission

An operational respawn replaces a role holder; it is not a clean-room role
demo. Unless the operator explicitly limits a spawn to an isolated runtime
test, full succession is the default: recover the predecessor's durable
responsibilities, current task state, decisions, working relationships, direct
children, pending returns and intended hierarchy before treating the new
session as the role's successor. Search the predecessor's session record,
saved handoff files and relevant live task/board state; reconcile each claim
against current evidence. Do not assume Craft copied predecessor memory, and do
not stop at the successor's statement that it received only startup
instructions.

A runtime-only smoke test may deliberately exclude predecessor work, but that
session is a test candidate, not the operational replacement: keep it separate
from the designated role holder and do not retire, supersede, or redirect work
from the predecessor on the strength of the test. If the operator later asks
the test session to inherit the role or mission, that newer direction starts a
full succession. Treat test-specific limits such as "no transfer" as scoped to
the test; they do not override a later operator instruction to recover the
predecessor's work.

Before starting an operational successor, identify the current incumbent and
any other candidate sessions for that role. Keep one clearly designated
current holder. Send the durable handoff to the successor and the current
coordination partners at their existing level (WC, TC and DT remain workspace
root peers); an old predecessor is not the only valid reporting target. Verify
delivery and the successor's first useful, non-overlapping action. Then
transfer ownership exactly once, correct parent links through native controls,
and retire only the genuinely superseded predecessor. A missing reply from a
peer is not permission to duplicate the role: keep the handoff visible and
continue independent authorized work while the named owner acts.

Craft may initially parent a spawned successor to its creator. Correct that
link through the native parent control as the coordinator's first handoff
housekeeping, then verify the successor's actual parent with native session
info before describing it as a root-level steward or hub. The incorrect link
does not suspend the successor's assigned role or existing authority: it may
continue its authorized work while the coordinator corrects the metadata. The
coordinator records the exact parent discrepancy and correction result in the
successor's durable handoff/continuity record and explicit coordination roster
used to track role ownership and peer routing. If native correction is
unavailable, record the unresolved link in those same records and route its
repair to the coordinator; do not claim that peer placement is verified or
leave the successor idle.

When the work uses [skill:drive-while-away]'s bounded checkpoint journal, read it
alongside the last coherent transcript. Have the coordinator record supersession
before the successor writes, then resume and reconcile the actual candidate,
pending review/checks and unresolved findings. Preserve evidence links and the
objective; never transfer an accepted verdict to a changed SHA. The journal's
generation prevents accidental stale checkpoint writes; it does not stop the
old session's tools or grant the successor mutation authority. Reconcile inherited memory and habits against current canonical instructions and actual owner grants. Once succession and sole ownership are verified, resume the eligible remaining inventory within that grant; notification receipt or another lifecycle ACK is not a new prerequisite. Preserve real holds and settle any still-running predecessor mutation before acting on its scope.

A minimal respawn prompt is a liability. Include, at minimum:

- **The real diagnosis**, not the surface error -- state plainly what actually killed the predecessor and why the visible error was misleading, so the successor doesn't waste its own time re-diagnosing or repeat the same mistake.
- **The last coherent task state** -- what was confirmed done, what was in flight, what open question was blocking forward progress.
- **Any incomplete live mutation**, with instructions to verify actual state before continuing (see diagnostic step 4).
- **Children and return routes** -- inventory the predecessor's direct children and pending returns. Transfer their coordination ownership and report targets to the successor, preserving session IDs, work and subordinate trees. Use supported hierarchy controls to reparent non-steward children to the successor. Keep any steward children at the shared workspace level (WC, TC and DT are peers); transfer their coordination ownership and return routes without making them subordinate. Retain the successor's intended role level. Message sessions with unfinished work or pending returns directly with the new return target; do not wake an archived, completed child merely for an acknowledgment. Verify the resulting links rather than treating a role label as a hierarchy change. If reparenting is unsupported, record the remaining graph discrepancy and the explicit coordination roster; do not edit private session storage or respawn healthy workers to disguise it. This host limitation does not suspend their eligible work.
- **An explicit instruction not to reproduce the failure mode** that killed the predecessor (chunk large pushes; verify live state before big mutations; don't build ad hoc polling loops; manage context deliberately if the predecessor was already a quota/context-exhaustion successor itself).

## Archiving

Retire the predecessor only after the durable handoff is accepted, concurrent
ownership is settled, and the successor has produced a useful turn. D or a
context warning triggers this process but does not itself authorize deletion.
Once the handoff is settled, apply the host's retirement/deletion-candidate
label and retire the obsolete role assignment so it is visibly superseded;
preserve transcript and handoff history rather than physically deleting it
without authorization. For a wedged session, the host may refuse retirement
while it is processing. Record the exact session ID and terminal/ownership
state for WC's next session-management sweep; WC archives it through the host
after it reports idle. Keep unrelated work moving and do not work around the
host refusal or make the completed task wait on archival.

## Cross-references

- `hub/SKILL.md` -- federation query protocol (checking for superseding work before dispatching); this skill's "check for a superseding session" step is that protocol applied to respawn decisions specifically.
- `_session-coordination-rules.md` -- distinguishing slow from stuck (rule 3), at-rest declarations, baton hand-off; this skill's diagnostic procedure is the deeper mechanical version of "verify liveness before escalating."
- `_work-item-ownership-rules.md` -- `maintained-by` stamps, used by the superseding-session check.
- `drive-while-away/SKILL.md` -- the complementary skill for the operator-handoff side (scheduling re-entry); this skill covers what to do when a session you're depending on has already gone dark.

## What this skill is NOT

- **NOT a substitute for actually reading the transcript.** The diagnostic procedure requires reading real content, not pattern-matching on an error string. Skipping straight to "nudge" or "respawn" without reading the last coherent content is the exact failure mode this skill exists to prevent.
- **NOT a license to respawn reflexively.** Check for superseding work first; a duplicate successor is its own kind of waste.
- **NOT applicable to a verified completed or transferred objective.** A terminal label alone does not prove that unfinished assigned work has an owner or a return event.
