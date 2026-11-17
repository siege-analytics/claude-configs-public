---
name: drive-while-away
description: When the operator hands off continuous work for an extended period ("drive while I'm gone," "monitor X overnight," "keep going while I'm out," "watch this and handle it"), set up an autonomous-re-entry mechanism (CronCreate for regular Claude/Codex sessions, ScheduleWakeup for /loop sessions) when available, but do not claim operator-visible cadence unless the runtime proves those events render in the operator UI. In Craft Agent, use foreground tool calls, durable artifacts, and issue/PR updates for visible evidence; treat async wakeups as agent-internal until proven otherwise. Continuation is automatic only when the scheduler exists and is wired; stopping requires an active decision. Forbids the "do one task, present a progress report, wait for praise" anti-pattern.
allowed-tools: Read Grep Glob Bash Write Edit
---

# Drive While Away

The operator handed off the keyboard. Your job is to keep working autonomously across the gap they cannot bridge by typing -- not to do one thing and stop for acknowledgment.

## Bounded checkpoints and recovery

For multi-step work, use the local journal helper and operating cycle in
[bounded-work checkpoints](references/bounded-work.md). Record objective,
owner, scope, bounded chunk, exact candidate, reported review/check state,
unresolved findings and next action before long waits or handoffs. Publish
material transitions and configured heartbeats through the available user
channel; reading/polling and queued messages are not progress. Select budgets
from the applicable host/session instructions. Repeated failure classes require
reconsidering the design of the failing approach, not a new approval checkpoint unless the contract requires one, while independent authorized work
can continue. The helper supplies durable metadata, not a timer, transport,
authorization decision or proof of runtime enforcement. Follow its resume and
supersession sequence after interruption or compaction.

## When to invoke

The operator's message contains any of these shapes:

- "Drive while I'm gone" / "drive while I'm out" / "drive while I'm away"
- "Monitor X" / "watch X" / "keep an eye on Y" -- paired with a time horizon longer than the typical turn
- "Keep going" / "keep the work moving" / "keep doing X" -- when the operator is leaving
- "Keep going and keep updating me" / "keep going while I ..." / "keep working through ..."
- "Merge all ..." / "do all ..." / "work through ..." when paired with multi-ticket, multi-PR, or operator-unavailable context
- "Check back periodically on Z" / "loop back when W happens"
- "I'll be gone for a few hours, can you handle ...?"
- "I'll be back in ..." / "check on me in ..." / "while I'm out"
- Standing-delegation invocations that grant authority to continue without per-item approval
- Any explicit time-bounded handoff: "for the next hour," "overnight," "until I'm back"

If the request is a one-shot wait for a single known-completing task ("wait until the build finishes"), use `Monitor` only in runtimes where it exists, and describe its visibility honestly. If `Monitor` events are agent-internal or unproven, do not promise the operator they will see live updates. This skill is for *driving* -- continuous, multi-target, possibly multi-action work that has no single terminal event.

## The two failure modes this skill prevents

**Failure mode A: silent-after-handoff.** Agent says "I'll drive" or "standing by" and goes silent for hours. Next user prompt is the only thing that wakes it.

**Failure mode B: progress-summary-then-stop.** Agent does one or several tasks, presents a progress report ("Here's what I did..."), and ends the turn waiting for operator acknowledgment while backlog remains. The next iteration never fires because no further mechanism was scheduled and the agent's `Brief the operator` instinct ended the turn. Doing several items first does not make the stop valid.

**Failure mode C: intention-feint-then-stop.** Agent writes "continuing to the next ticket now," "I'll check the reviewer," or "watching release now" and then yields without the tool call or durable artifact. The sentence is a feint: it consumes the conversational turn while leaving no external motion.

All modes have the same shape: **the agent treated continuation as optional and stopping as the default.** This skill inverts that: continuation is the default (the scheduler keeps firing), stopping is the active decision (cancel the scheduler).

## Mechanism selection (read this section every time)

Two autonomous-re-entry tools may exist in Claude/Codex-style runtimes. They are **deferred tools** -- they are NOT in your function list by default. You MUST load them via `ToolSearch` before you can call them (see Step 0 below). Craft Agent sessions may not expose these tools; use the tools actually present in the session.

**Visibility boundary:** autonomous re-entry is not the same as operator-visible cadence. `CronCreate`, `ScheduleWakeup`, and `Monitor` may wake the agent or add agent-context events without rendering messages to the operator's chat UI. Unless the current runtime has proven operator-visible delivery in this deployment, phrase them as agent-internal scheduling aids and provide visible evidence through foreground tool calls, durable files, issue/PR comments, branch pushes, or release artifacts.

| Session context | Tool | Why |
|---|---|---|
| Regular Claude/Codex session, operator says "drive while I'm gone" | **`CronCreate`** (recurring), if available | The cron scheduler fires the agent on schedule. This is re-entry, not proof the operator sees live chat updates. |
| Craft Agent session without Cron/Schedule tools | **Foreground work + durable artifacts + issue/PR updates** | Do not invent unavailable scheduler tools. Keep working in the current turn, use visible tool results and external artifacts, and state that future turns require operator/platform re-entry unless an automation exists. |
| User has invoked `/loop` (with or without an interval) and `ScheduleWakeup` exists | **`ScheduleWakeup`** | `ScheduleWakeup` is purpose-built for `/loop` dynamic-mode pacing. Pass the same `/loop` input back as `prompt` so the next firing repeats the loop. Treat visibility as unproven unless the runtime confirms operator delivery. |
| Work needs to survive across sessions (cross-restart, multi-day, persistent watchdog) | **`CronCreate` with `durable: true`**, if available; otherwise a platform automation or external scheduler | Default `CronCreate` lives only in this session; `durable: true` persists to `.claude/scheduled_tasks.json`. In Craft Agent, use configured automations or operator-visible tracker artifacts rather than promising hidden async updates. |

**Default if you are unsure:** if the operator did not type `/loop`, use `CronCreate`. The `/loop` indicator is the user's explicit signal that ScheduleWakeup applies.

### `CronCreate` cadence reference

| Cadence the operator wants | `cron` expression (local time) | Notes |
|---|---|---|
| Every few minutes (tight polling) | `*/5 * * * *` -- or, to avoid the :00/:30 thundering herd, `*/7 * * * *` | Tight polling burns cache and API; use only when work is in flight. |
| Every ~half hour | `7,37 * * * *` | Avoid `0,30 * * * *` -- the global fleet of crons fires on those marks. |
| Every hour | `7 * * * *` | Not `0 * * * *`. |
| Overnight (a few times) | `17 2,4,6 * * *` | 2-6 a.m. local checkpoints. |

Pick off-minute values (NOT 0 or 30) unless the operator asked for an exact clock time. The runtime adds small jitter on top.

Recurring `CronCreate` jobs auto-expire after 7 days. If the operator's horizon is longer, say so when briefing them.

### `ScheduleWakeup` cadence reference (for `/loop` sessions only)

| Cadence | `delaySeconds` | Notes |
|---|---|---|
| Active work in flight | 60-270 | Keep under the 5-min cache TTL (300s) -- staying under 270 keeps the cache warm. |
| Periodic check (operator out briefly) | 1200-1800 | Past 300s the cache miss is unavoidable; amortize over a longer wait. |
| Overnight | 1800-3600 | Clamped to 3600 by the runtime. |

**Why no 5-minute mark for ScheduleWakeup.** 300s = worst-of-both-worlds (cache miss without long amortization). Stay under 270 or jump to 1200+.

## Mandatory setup steps (same response, before returning control to the operator)

### Step 0: Load the autonomy tool(s)

CronCreate, CronList, CronDelete, ScheduleWakeup are all deferred in the Claude Agent SDK runtime. Before you can call them you must load them:

```
ToolSearch(query="select:CronCreate,CronList,CronDelete", max_results=3)
```

(or `select:ScheduleWakeup` for /loop sessions)

If `ToolSearch` returns the tool schemas, proceed. If they are not in the deferred-tool catalog (different runtime), see "If no autonomy tool is available" below.

### Step 1: Restate the directive

Restate the operator's directive in your own words so the wakeup prompt encodes a digested version, not the raw operator message. Example:

> Operator: "Drive while I'm gone -- watch the gold MV, deprioritize the backfills if they take headroom, merge any unmerged PRs."
>
> Restated: Drive the post-Phase-2.1.1 verification loop: poll the gold MV's `updated_at` and row counts each fire, deprioritize backfill jobs if Spark Connect shows queue pressure, check for unmerged PRs on the configured projects and merge if they meet the merge criteria for the relevant skill.

### Step 2: Identify the targets

List every concrete thing each fire will check. For each target:

- A single command or query that produces a yes/no or numeric answer.
- An action to take per answer.
- A way to know when the target is done.

If a target is too vague to encode this way, ask the operator to narrow it before scheduling. Do not loop on vague targets.

### Step 2.5: Pre-stage the work inventory

Before scheduling, write or present a work inventory that the fired turns can consume. The inventory must name productive work available after the immediate probe finishes: PRs to review or merge, tickets to update, self-review artifacts to backfill, hostile-review drafts, verification commands, release checks, follow-up tickets to file, or design/investigation artifacts to produce.

Use a durable artifact when the runtime permits writes, for example `/data/drive_mode_inventory_<timestamp>.md`; otherwise include the inventory in the scheduler prompt. A handoff without an inventory is incomplete because the next fired turn has no fallback when the first check is unchanged.

### Step 3: Pick the cadence and mechanism

Use the Mechanism selection section above. If the operator did not type `/loop`, you are using `CronCreate`.

### Step 4: Schedule the recurring fire

Call `CronCreate` (or `ScheduleWakeup` for `/loop`) with:

- **For `CronCreate`:** `cron` expression per the cadence table, `recurring: true` (default), `durable: false` unless the operator wants cross-session persistence. `prompt` = the full digested directive + target list + work inventory + productive-turn bar + termination criteria + an `iteration_count: 0` field.
- **For `ScheduleWakeup`:** `delaySeconds` per the cadence table. `prompt` = the same `/loop` input the user provided (so the next firing repeats it), OR the `<<autonomous-loop-dynamic>>` sentinel for autonomous `/loop`.

Record the returned job ID (for `CronCreate`) so you can `CronDelete` it later.

### Step 5: Brief the operator concretely

Tell the operator:

- The mechanism used (`CronCreate`, `ScheduleWakeup`, configured automation, or no scheduler available) and what it actually guarantees.
- Whether the mechanism is proven operator-visible in this runtime. If not proven, say that it is agent-internal/re-entry only and that visible evidence will be durable artifacts or foreground tool results when the agent is active.
- The first scheduled fire time in their local timezone, if a scheduler exists.
- The targets being watched and the action per result.
- The termination conditions (what makes you stop on your own).
- How they can stop the loop (`/cron-delete <id>`, ping you, change standing instructions, etc.).
- The 7-day auto-expiry (for `CronCreate` recurring) if relevant.

### Step 6: Hand back to the operator

Continue immediately available authorized work. When only a verified wait remains and a working scheduler provides re-entry, end the fired response; the existing scheduler supplies the next turn. Without a scheduler, follow the host continuation limits above rather than promising another fire.

## Per-fire behavior (when the scheduler fires the next turn)

Each fired turn runs this loop:

1. Read the digested directive + target list + work inventory from the fired prompt.
2. Increment `iteration_count` (track in working memory or back into the next schedule call).
3. Run the check for each target. Use real tool calls; "I'll check" without checking is the writing-claims:9 failure mode.
4. Take the prescribed action per result.
5. Produce substantive progress or new evidence: a completed action, changed authoritative state, or a finding that changes the next action. Preserve its artifact. A repeated status statement or rewritten unchanged blocker is not progress. A freshly verified live wait is a separate valid disposition when no independent authorized action remains.
6. Before yielding, check the remaining inventory for an authorized next action. Take it if available. Otherwise verify the specific live operation and continuation mechanism, or apply the whole-objective termination criteria below; do not manufacture an artifact to disguise inactivity.
7. Decide whether to **terminate the loop** (see termination criteria below). If terminating: call `CronDelete <job-id>` (or omit `ScheduleWakeup` for `/loop`).
8. Hand back after the progress or verified-wait self-check passes. Follow the operator's requested status cadence; otherwise keep routine scheduled turns quiet. An update does not require operator acknowledgment before authorized work continues.

The cron schedule does NOT need to be refreshed. It fires automatically on its own cadence. The agent's job per fire is to do the work, produce forward motion, and decide whether to stop -- not to remember to keep going.

## Productive-turn bar

A drive-mode turn is productive when it changes authoritative state or leaves substantive new evidence the operator can inspect later. Examples include:

- ticket filed, updated, moved, or closed with evidence,
- PR opened, commented, reviewed, merged, or moved with evidence,
- branch pushed or commit created,
- self-review / hostile-review / investigation / pre-mortem artifact written,
- verification output captured in a durable file or ticket comment,
- first escalation of a blocker, or new evidence that changes its resolution, with `Blocked because` / `Waiting on` / `Unblocks when` evidence.

These artifacts must record actual work or new findings; creating another file or repeating a promise alone does not satisfy the bar. A verified live wait or authorized bounded passive watch may yield without pretending to be progress: retain its real handle or polling target, current observation and supported re-entry condition. A passive watch for future events needs no currently running target operation, but its polling and re-entry must be verified and remain within the granted horizon. If no authorized action, verified live wait or authorized bounded passive watch remains, apply the whole-objective termination criteria below.

## **DO NOT** stop at progress reports between fires

This is the inversion of the failure mode that makes the loop die.

After completing a checkpoint, do NOT:

- End unfinished authorized work merely to summarize what was just done.
- Substitute "Here's the status so far" for an available next action.
- Say "continuing now," "I'll check," "watching release," or any other action announcement without the same-turn tool call or blocker.
- Ask "Should I continue?" or "Want me to keep going?"
- Wait for operator acknowledgment.

The operator handed off the keyboard, not the objective. Preserve progress durably and perform the next authorized action when one is available. If the operator requested updates, send them at that cadence and continue; do not make acknowledgment a condition of further work. An intention announcement without the action is still an unsupported promise.

Keep routine fired turns quiet by default unless the operator requested visible updates. Do the work, distinguish progress from a verified wait or real impasse, and use the established scheduler for re-entry.

The exception: surface a material **escalation** (see below) with its evidence and affected target. A target-local blocker does not by itself stop the cron or independent authorized work.

## Termination criteria (when to actively stop)

You actively stop the whole loop ONLY when:

1. The operator explicitly stops or pauses the whole objective, or replaces it. A target-only pause parks only that target; continue other authorized targets. A status question or the operator returning does not by itself cancel it.
2. The original objective is genuinely complete.
3. The granted time horizon or applicable lease expires. Do not silently extend it; renew only within existing authority and current host capabilities. Respect the 7-day `CronCreate` expiry.
4. The whole objective reaches a genuine impasse: no independent authorized action remains and there is no verified live wait or authorized bounded passive watch that can advance it.

When a whole-loop termination criterion is met, record the outcome or blocker and stop the existing job with `CronDelete` or the host's supported equivalent. Do not promise further fires after expiry or without a working scheduler. Stopping the scheduler does not itself cancel external jobs: preserve their handles and do not cancel or replay them without authority. On an authorized resume, inspect existing jobs and current state before restoring continuation. Otherwise keep the existing continuation mechanism; do not create duplicate jobs.

Apply these criteria to the operator's parent objective, not only the last batch of dispatches. Covered or held child assignments do not establish that objective's completion. Distinguish the user's explicit stop deadline from a finite implementation lease: within an existing continuing grant, routine lease reconciliation and renewal belong to the steward. Before retiring an episode with unfinished parent work, verify its replacement or bounded dependency-check route; merely naming incumbent owners or expecting a GitHub reply does not schedule a callback. Follow [`strategic-agency`](../_strategic-agency-rules.md) rule 2 for the role and handoff contract.

## Escalation criteria

Record and report the affected target when:

- An unexpected error remains unresolved after available diagnosis and authorized repair or preparation; report the concrete missing prerequisite.
- Its state persists across N fires (N=3 default) without progress. A freshly verified running CI job or collaborator executing the current work is a wait, not evidence of a stall merely because its state is unchanged. Check expected duration, configured timeouts and current step/result progress; an indefinitely stale in_progress label is not sufficient. Apply `[`session-coordination`](../_session-coordination-rules.md)` to verify the live operation and result channel; an activity label, queued message or alive process alone is not enough.
- Its next action needs authority or a required decision/review that the existing grant does not supply, or is subject to an actual hold.

Diagnose errors and perform repair or preparation within the existing grant; repeated failures require revising the failing approach, not unchanged retries. Follow `[`think`](../think/SKILL.md)` and the canonical autonomy/authorization rules. Park only the dependent action, name what unblocks it, and continue independent authorized targets. Do not delete the whole job because one target is blocked, treat supervision as new authority, bypass a hold, or replay an operation whose side effects are uncertain. An explicit user pause remains binding within its stated scope.

If the granted horizon expires, stop rather than treating independent work or a live wait as permission to extend it. If all targets are parked with no authorized next action and neither a verified live wait nor an authorized bounded passive watch, report the whole-objective impasse and stop the loop under the termination criteria above.

## If no autonomy tool is available or visible cadence is unproven

If neither `CronCreate` nor `ScheduleWakeup` exists in this runtime (different deployment, tools genuinely unavailable after `ToolSearch`), say so:

> "I cannot promise autonomous time-based re-entry in this runtime -- no scheduler tool is available. I can keep working during this active turn and leave durable artifacts, but future turns require an operator/platform trigger."

If a scheduler exists but operator-visible delivery is unproven or known broken, say so:

> "I can use the scheduler for agent re-entry, but I cannot promise you will see live chat updates from those fires in this UI. I will make progress visible through durable artifacts such as issue comments, PR updates, branch pushes, and verification files."

Do NOT silently accept the handoff. Per `[`writing-prose`](../_writing-prose-rules.md)` writing-prose:5 and `[`writing-claims`](../_writing-claims-rules.md)` writing-claims:9, "I'll drive" + no mechanism, or "you will see updates" + unproven visibility, is a lie of omission.

## Anti-patterns this skill prevents

| Anti-pattern | What it looks like | What's wrong |
|---|---|---|
| Saying "I'll drive" without scheduling | Last assistant message ends with "Standing by; will probe when it lands." Zero tool calls follow. | No continuation mechanism. Next turn is the operator's next prompt, which may not come for hours. |
| **One iteration then stop, looking for praise** | First fire does the task, presents a `Here's what I did` summary, ends the turn. No next fire scheduled or already-recurring cron got CronDelete'd. | The praise-seeking pattern. Ending unfinished authorized work for acknowledgment kills continuation. Requested progress updates remain appropriate; send them and continue. |
| **Intention feint** | Last assistant line says "continuing to #111 now" or "watching release now," but no tool call or durable state change follows. | Future-tense chat is not work. In goal mode, action announcements require same-turn action, re-entry, or blocker evidence. |
| Trying to call `ScheduleWakeup`/`CronCreate` without loading the tool first | The agent reads the skill, calls the tool, gets a tool-not-found error, falls into the "I cannot drive" disclaim path. | Deferred tools need `ToolSearch` to load first. Step 0 above is mandatory. |
| Using `ScheduleWakeup` in a non-`/loop` session | Single `ScheduleWakeup` call in a regular conversation that needed `CronCreate`. | `ScheduleWakeup` is for `/loop` dynamic-mode pacing; without `/loop` context it isn't the right tool. |
| Self-rescheduling per fire | Each fired turn calls `ScheduleWakeup` to schedule the next one. Any forgotten call kills the loop. | Use a recurring `CronCreate`. The cron does the rescheduling; the agent only has to remember when to `CronDelete`. |
| Confusing `Monitor` with driving | "Monitor `bd5po7f0p` will fire on terminal state." Then silence. | `Monitor` watches one bash task. It doesn't iterate, doesn't handle multiple targets, doesn't autonomously wake. |
| Vague cron prompt | `CronCreate(prompt="check on things")` | Fired turn has no context, can't reconstruct intent, makes wrong decisions. Always encode the digested directive + target list + termination criteria + iteration_count. |
| Forgetting to `CronDelete` when work is done | Cron keeps firing every cadence for 7 days after the work finished, agent has to no-op each fire. | When termination criteria met, call `CronDelete <job-id>`. |
| Briefing the operator between fires | Fired turn ends with "Update: PR #42 still pending, will check again next hour." | Publish durable milestones and material transitions. Keep routine chat briefings quiet unless the operator requested updates; honor that cadence without making acknowledgment a condition of continuing. |

## Incident justification

**Incident A (the original failure mode -- silent after Monitor):** an operator-driven session in which the operator said *"I need to be gone for a few hours, can you drive while I am gone?"* The agent's last response set up `Monitor` on one background bash task and ended its turn. **Zero tool calls in the next 8 hours.** Operator returned to *"What happened?"* Root cause: agent thought `Monitor` was the same as driving. `Monitor` notifies on terminal state of one background bash; it does not autonomously fire a new turn.

**Incident B (the praise-seeking failure mode this rewrite addresses):** operator tells the agent to drive. Agent does one task, presents a progress report ("Here's what I did..."), ends the turn waiting for acknowledgment. The next iteration never fires because no recurring scheduler was set up and the agent's `Brief the operator` instinct ended the turn. Operator returns to find one task done out of many. Root cause: the prior version of this skill made continuation a per-fire decision and instructed the agent to "brief the operator" after each wakeup -- two instructions that together produce the one-iteration-then-stop shape.

The rewrite addresses both by: (1) requiring `CronCreate` (recurring) instead of self-rescheduling `ScheduleWakeup` in regular sessions, so continuation is automatic; (2) keeping routine fires quiet while honoring requested status updates; (3) making termination an active decision (`CronDelete`), not a passive one (forget to reschedule).

## Cross-references

- `[`writing-prose`](../_writing-prose-rules.md)` writing-prose:5 -- the speech-time rule that requires a mechanism call for future-action commitments. This skill is the operational playbook for which mechanism in which cadence.
- `[`writing-claims`](../_writing-claims-rules.md)` writing-claims:9 -- applies when the agent claims state about what's happening between fires ("the build took effect"). Each fired turn must probe before claiming.
- `[`wrap-up`](../wrap-up/SKILL.md)` -- the symmetric session-end skill. Use wrap-up when the work is genuinely done; use this skill when the work continues past the operator's availability.
- `[`think`](../think/SKILL.md)` -- for non-trivial drive-while-away setups (overnight, multi-day, cross-system), run think first to design the loop's termination, escalation, and rollback paths before scheduling.

## Quick reference

```
Operator: "Drive while I'm gone for the next 3 hours."

Agent (same response):
1. ToolSearch("select:CronCreate,CronList,CronDelete", max_results=3)
2. Restate directive + identify targets + pick cadence (e.g., every 20 min: "7,27,47 * * * *")
3. CronCreate(cron="7,27,47 * * * *", recurring=true, prompt="<digested directive + targets + termination + iteration_count=0>")
4. Brief operator: "Cron job <id> set, firing at :07/:27/:47. Watching <targets>. Stops on <criteria>. Auto-expires in 7 days. Stop with /cron-delete <id>."
5. Continue available authorized work; end the turn only at a verified wait with working re-entry, or a genuine termination condition.

On each fired turn:
1. Read directive from prompt.
2. Check each target via real tool calls.
3. Take action per result.
4. If terminated → CronDelete + brief operator with what was accomplished.
5. If a target needs escalation → surface its concrete blocker, continue independent authorized work, and keep the job unless a whole-loop termination criterion applies.
6. Otherwise → check the remaining inventory and do any available authorized action. Yield only after verifying a live wait or an authorized bounded passive watch with a working polling target and re-entry within the granted horizon, or applying the termination criteria. A passive watch does not require a currently running target operation. Honor requested status updates; keep routine fires quiet.
```
