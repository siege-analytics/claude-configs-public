---
name: stalled-session-recovery
description: How to diagnose and recover a session that has stopped producing useful turns -- stuck on a repeating error, silent for an abnormal stretch, or looping on the same tool call. Invoke when checking on a session that "seems stuck," when a session's own error looks like it should have cleared but hasn't, when a hub is deciding whether to nudge or respawn a worker, or when auditing a fleet of sessions for health. Covers three failure shapes (transient error, persistent misconfiguration, wedged tool call) with distinct diagnostics and distinct fixes, the discipline of reading the last coherent content instead of trusting the error label, and how to respawn without duplicating work or losing in-flight state.
allowed-tools: Read Grep Glob Bash mcp__session__get_session_info mcp__session__list_sessions mcp__session__send_agent_message mcp__session__spawn_session mcp__session__archive_session mcp__session__list_background_tasks
---

# Stalled-Session Recovery

A session that has stopped producing useful turns is not one problem -- it is at least three different problems that happen to look similar from the outside. Treating all of them the same way (wait, or nudge-and-wait) fixes one and wastes hours on the other two. This skill is the diagnostic-then-fix procedure, and the discipline that makes it reliable: **never classify a stalled session from its error's `errorCode`/`errorTitle` alone.** Read the last *coherent* content before deciding what happened.

## When to invoke

- Checking on a session that "seems stuck" or hasn't produced a turn in an abnormal stretch.
- A session's own error (rate limit, timeout, generic failure) looks like it should have cleared on retry, but hasn't after several attempts.
- You are a hub (see `hub/SKILL.md`) deciding whether to nudge a worker once more or replace it.
- Auditing a fleet of sessions for health, e.g. before a large coordinated action.

## The three failure shapes

Do not assume the shape from the error message. Confirm it from the transcript.

### 1. Transient error (genuinely short-lived)

Last few transcript entries alternate an operator/system retry ("try again") with an error, and the error is a real, narrow, rate/quota-shaped failure that has not persisted long or shown a worsening pattern.

**Fix:** nudge once with a message asking it to continue. If it recovers, done. If the *same* error recurs after the nudge, stop treating it as transient -- move to shape 2 or 3 below. Do not nudge repeatedly hoping the Nth attempt is the one that clears; that is shape 2 wearing shape 1's clothes.

**A real transient error backs off; a masked one does not.** Retry gaps that grow between attempts are consistent with real backoff. Retry gaps that stay flat or *shrink* between attempts are not -- that is a tell the label is wrong, not that the system is under more load.

### 2. Persistent misconfiguration (will never clear on its own)

Every attempt fails identically, because the request itself cannot succeed, not because a shared resource is temporarily exhausted. Two common concrete causes, both observed producing a generic "rate limited"-shaped error in practice:

- **Wrong model/connection pair for the account tier** -- e.g. a model listed as selectable for a connection but not actually supported for that specific account type. Every turn errors immediately, with no other activity in between.
- **Oversized single request** -- e.g. a large diff pushed as one API call. Look for the session's own words a few turns *before* the error run starts; a model that already said something like "the JSON body was too large for a single API call, I'll split this into multiple commits" and then never got the chance to is exactly this shape. Retrying the identical oversized request fails identically forever.

**Fix:** cannot be repaired in place -- there is no tool to edit an existing session's model/connection, and no way to shrink a request that already failed to send. Respawn with a corrected configuration (a working model for the connection; instructions to chunk large pushes into smaller commits) and carry the original prompt/task forward verbatim plus the specific correction.

### 3. Wedged session (a stuck tool call, not a stuck request)

The most dangerous shape because it looks the most "alive." A single tool call gets stuck in an executing state indefinitely and never returns, so the turn never completes and the session can never process new input -- but `session.jsonl` keeps growing, because something (a heartbeat, a polling loop) keeps firing on a fixed interval underneath the stuck call.

**Signature:** a long run (dozens to hundreds) of consecutive tool-call entries, same tool name, at a fixed interval (e.g. every ~30s), sharing one parent tool-use id, with **no assistant text in between** and often empty tool input. This is different from a genuinely busy session dispatching to many workers, which shows *varied* targets/content and assistant narration describing what it's doing between calls. Grep the tail for an unbroken run of tool-type entries with zero interleaved assistant-type entries; a run in the hundreds, spanning hours, is the signature -- a handful is not.

**Fix:** cannot be un-stuck from outside; nothing available interrupts another session's in-flight tool call. Read backward from where the loop *started* (not the tail) to recover the last coherent state -- what it was doing, what was in flight, what tickets/mutations were mid-way. Spawn a successor with that context, plus an explicit instruction not to reproduce whatever produced the loop (e.g. don't build a manual sleep-and-poll pattern inside one tool call; use the platform's own scheduling/monitoring primitives instead).

**Expect `archive_session` (or equivalent) to fail on a wedged session** with something like "currently processing a turn" -- that failure is itself confirmation of the diagnosis, not a bug in the archiving step. If it keeps failing after the successor is confirmed alive, this needs whatever manual/UI-level intervention the platform provides for a hung session; don't loop retrying the same archive call expecting it to eventually succeed on its own.

## Diagnostic procedure (apply before deciding anything)

1. **Do not read only the last line.** Read the last several non-error entries -- specifically the last *assistant* content before the error run began, not just the trailing error.
2. **Look for an explicit statement of the real problem**, stated by the session itself shortly before it went quiet (an oversized-payload complaint, an "I don't have enough context to answer" admission, a mid-operation status line).
3. **Compare transcript size/density against comparable healthy sessions** (same role, similar age). A session that has grown unusually large per-message relative to peers, especially one that is *already* a successor spawned because an earlier predecessor exhausted a context/quota budget, is a candidate for shape 2 (context exhaustion presenting as a generic error) even without an explicit "too large" message.
4. **Check for an incomplete live mutation.** If the last coherent lines describe applying/writing/deploying a multi-step change and the count of "done" doesn't match the count "expected" (e.g. "all 5 objects match... applying now" followed by "all 4 objects applied"), the operationally important fact is the incomplete mutation, not the error label. The successor's first job is to verify actual live state against the intended end state -- not to blindly retry the operation, and not to assume nothing landed.
5. **Check for a live tool-call loop** (see shape 3's signature) before concluding "just busy" or "just quiet."

## Before respawning: check for a superseding session

Do not respawn a stuck session's exact original task without checking whether it has already been picked up elsewhere. Search for other active sessions on the same ticket/scope (`list_sessions`, search by ticket number or topic). If one exists and is active, either skip the respawn (archive the stuck one only) or fold "your original task may be superseded, check with X first" into the respawn prompt instead of repeating stale instructions. This is the stalled-session-recovery instance of the hub federation query protocol (`hub/SKILL.md` Part 4) -- the same duplicate-work risk applies whether the collision is between two live hubs or between a stuck session's stale task and a newer session already covering it.

Also check the session's own `status` field. A session already at a terminal status (e.g. `done`) that happens to have a trailing error is not stalled -- it finished. Don't respawn it.

## Respawning: what the successor needs

A minimal respawn prompt is a liability. Include, at minimum:

- **The real diagnosis**, not the surface error -- state plainly what actually killed the predecessor and why the visible error was misleading, so the successor doesn't waste its own time re-diagnosing or repeat the same mistake.
- **The last coherent task state** -- what was confirmed done, what was in flight, what open question was blocking forward progress.
- **Any incomplete live mutation**, with instructions to verify actual state before continuing (see diagnostic step 4).
- **Dependents that need re-routing** -- any other session that was told to report back to the now-dead session and doesn't know about the successor. Message each directly with the new session ID; don't wait for them to discover it.
- **An explicit instruction not to reproduce the failure mode** that killed the predecessor (chunk large pushes; verify live state before big mutations; don't build ad hoc polling loops; manage context deliberately if the predecessor was already a quota/context-exhaustion successor itself).

## Archiving

Archive the predecessor once the successor is confirmed alive (a real turn produced, not just a spawn acknowledgment) -- not before, and not automatically. For shape 3 (wedged), see the note above: archiving may fail while the platform still considers the session mid-turn; that is expected, not an error to work around.

## Cross-references

- `hub/SKILL.md` -- federation query protocol (checking for superseding work before dispatching); this skill's "check for a superseding session" step is that protocol applied to respawn decisions specifically.
- `_session-coordination-rules.md` -- distinguishing slow from stuck (rule 3), at-rest declarations, baton hand-off; this skill's diagnostic procedure is the deeper mechanical version of "verify liveness before escalating."
- `_work-item-ownership-rules.md` -- `maintained-by` stamps, used by the superseding-session check.
- `drive-while-away/SKILL.md` -- the complementary skill for the operator-handoff side (scheduling re-entry); this skill covers what to do when a session you're depending on has already gone dark.

## What this skill is NOT

- **NOT a substitute for actually reading the transcript.** The diagnostic procedure requires reading real content, not pattern-matching on an error string. Skipping straight to "nudge" or "respawn" without reading the last coherent content is the exact failure mode this skill exists to prevent.
- **NOT a license to respawn reflexively.** Check for superseding work first; a duplicate successor is its own kind of waste.
- **NOT applicable to a session that finished normally.** A terminal `status` with a trailing cosmetic error is not stalled.
