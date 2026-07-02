---
name: drive-while-away
description: When the operator hands off continuous work for an extended period ("drive while I'm gone," "monitor X overnight," "keep going while I'm out," "watch this and handle it"), set up an autonomous-re-entry mechanism (CronCreate for regular sessions, ScheduleWakeup for /loop sessions) in the same response. Continuation is automatic via the scheduler; stopping requires an active decision. Forbids the "do one task, present a progress report, wait for praise" anti-pattern.
allowed-tools: Read Grep Glob Bash Write Edit
---

# Drive While Away

The operator handed off the keyboard. Your job is to keep working autonomously across the gap they cannot bridge by typing -- not to do one thing and stop for acknowledgment.

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

If the request is a one-shot wait for a single known-completing task ("wait until the build finishes"), use the `Monitor` tool alone. This skill is for *driving* -- continuous, multi-target, possibly multi-action work that has no single terminal event.

## The two failure modes this skill prevents

**Failure mode A: silent-after-handoff.** Agent says "I'll drive" or "standing by" and goes silent for hours. Next user prompt is the only thing that wakes it.

**Failure mode B: one-iteration-then-stop-looking-for-praise.** Agent does one task, presents a progress report ("Here's what I did..."), and ends the turn waiting for operator acknowledgment. The next iteration never fires because no further mechanism was scheduled and the agent's `Brief the operator` instinct ended the turn.

Both modes have the same shape: **the agent treated continuation as optional and stopping as the default.** This skill inverts that: continuation is the default (the scheduler keeps firing), stopping is the active decision (cancel the scheduler).

## Mechanism selection (read this section every time)

Two autonomous-re-entry tools exist. They are **deferred tools** -- they are NOT in your function list by default. You MUST load them via `ToolSearch` before you can call them (see Step 0 below).

| Session context | Tool | Why |
|---|---|---|
| Regular session, operator says "drive while I'm gone" | **`CronCreate`** (recurring) | The cron scheduler fires the agent on schedule automatically. Continuation does not depend on the agent remembering to reschedule. |
| User has invoked `/loop` (with or without an interval) | **`ScheduleWakeup`** | `ScheduleWakeup` is purpose-built for `/loop` dynamic-mode pacing. Pass the same `/loop` input back as `prompt` so the next firing repeats the loop. For autonomous `/loop` (no operator prompt) use the sentinel `<<autonomous-loop-dynamic>>`. |
| Work needs to survive across sessions (cross-restart, multi-day, persistent watchdog) | **`CronCreate`** with `durable: true` | Default `CronCreate` lives only in this session; `durable: true` persists to `.claude/scheduled_tasks.json`. |

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

- The mechanism used (`CronCreate` vs `ScheduleWakeup`) and the cadence.
- The first scheduled fire time in their local timezone.
- The targets being watched and the action per result.
- The termination conditions (what makes you stop on your own).
- How they can stop the loop (`/cron-delete <id>`, ping you, change standing instructions, etc.).
- The 7-day auto-expiry (for `CronCreate` recurring) if relevant.

### Step 6: Hand back to the operator

End the response. The scheduler will fire the next turn. Do not "stand by" -- the cron does the standing.

## Per-fire behavior (when the scheduler fires the next turn)

Each fired turn runs this loop:

1. Read the digested directive + target list + work inventory from the fired prompt.
2. Increment `iteration_count` (track in working memory or back into the next schedule call).
3. Run the check for each target. Use real tool calls; "I'll check" without checking is the writing-claims:9 failure mode.
4. Take the prescribed action per result.
5. Produce at least one operator-visible artifact unless all work is genuinely blocked or exhausted. Acceptable artifacts include: ticket filed or updated, PR comment, self-review or hostile-review artifact, branch push, verification output captured in `/data/`, durable investigation note, or status update that names concrete forward motion. A pure "nothing changed" probe is not a productive turn.
6. Run the end-of-turn self-check: "Will the next operator-visible message contain a new artifact since the last pickup?" If no, continue working the inventory before yielding.
7. Decide whether to **terminate the loop** (see termination criteria below). If terminating: call `CronDelete <job-id>` (or omit `ScheduleWakeup` for `/loop`).
8. **Hand back silently** only after the productive-turn requirement and self-check pass. Do not present a progress report unless an escalation criterion fired (see Escalation below).

The cron schedule does NOT need to be refreshed. It fires automatically on its own cadence. The agent's job per fire is to do the work, produce forward motion, and decide whether to stop -- not to remember to keep going.

## Productive-turn bar

A drive-mode turn is productive only if it changes external state or leaves durable evidence the operator can inspect later. At least one of the following must happen before the turn yields:

- ticket filed, updated, moved, or closed with evidence,
- PR opened, commented, reviewed, merged, or moved with evidence,
- branch pushed or commit created,
- self-review / hostile-review / investigation / pre-mortem artifact written,
- verification output captured in a durable file or ticket comment,
- blocker escalated with `Blocked because` / `Waiting on` / `Unblocks when` evidence.

If none is possible, stop the loop with an explicit blocker rather than silently re-looping.

## **DO NOT** present progress reports between fires

This is the inversion of the failure mode that makes the loop die.

After completing a checkpoint, do NOT:

- Summarize what was just done.
- Say "Here's the status so far."
- Ask "Should I continue?" or "Want me to keep going?"
- Wait for operator acknowledgment.

The operator handed off the keyboard. They are NOT WATCHING. A progress report between fires is wasted output the operator cannot see in real time, and ending the turn for acknowledgment is the praise-seeking pattern that kills the loop.

**The fired turn should be as quiet as possible.** Do the work, decide if done, hand back. The scheduler fires the next turn. The operator reads the conversation when they return.

The exception: if the iteration hit an **escalation criterion** (see below), surface that explicitly and stop the cron. Escalation is the only legitimate reason to break silence between fires.

## Termination criteria (when to actively stop)

You actively stop the loop ONLY when:

1. The operator returns and explicitly says "stop driving" or asks a focused question that shifts the work.
2. The work is genuinely done -- every target reached its terminal state, every action succeeded, the original directive is fully satisfied.
3. An escalation criterion fired (next section).

If none of these is true, do nothing and let the cron fire again. You did not need to reschedule.

## Escalation criteria

Surface to the operator AND stop the cron when:

- A target produces an unexpected error type the loop didn't anticipate, AND the agent cannot resolve it from context.
- The same state has persisted across N fires (N=3 default) with no progress.
- An action the loop would normally take requires authorization the operator hasn't granted in advance (destructive ops, third-party API writes, anything in the operator's standing "ask first" list).
- The loop has been running longer than the operator's stated time horizon (e.g., "a few hours" expired multiple fires ago).
- The loop is about to hit the 7-day `CronCreate` auto-expiry without finishing.

When escalating, write a clear message to the operator naming what stopped you and what you need, then `CronDelete` the job. The next operator interaction restarts the work.

## If no autonomy tool is available

If neither `CronCreate` nor `ScheduleWakeup` exists in this runtime (different deployment, tools genuinely unavailable after `ToolSearch`), say so explicitly:

> "I cannot keep driving in this runtime -- no autonomous-re-entry mechanism is available. If you want continuation across the time gap, [option A: have an external scheduler ping me on a cadence; option B: run me under `/loop`; option C: leave me a list of checkpoints you'll resume from when back]. As-is, when you leave my next turn does not happen until you return."

Do NOT silently accept the handoff. Per `[rule:writing-prose]` writing-prose:5 and `[rule:writing-claims]` writing-claims:9, "I'll drive" + no mechanism is a lie of omission.

## Anti-patterns this skill prevents

| Anti-pattern | What it looks like | What's wrong |
|---|---|---|
| Saying "I'll drive" without scheduling | Last assistant message ends with "Standing by; will probe when it lands." Zero tool calls follow. | No continuation mechanism. Next turn is the operator's next prompt, which may not come for hours. |
| **One iteration then stop, looking for praise** | First fire does the task, presents a `Here's what I did` summary, ends the turn. No next fire scheduled or already-recurring cron got CronDelete'd. | The praise-seeking pattern. The operator is not watching; the summary is wasted output and the ended turn kills the loop. |
| Trying to call `ScheduleWakeup`/`CronCreate` without loading the tool first | The agent reads the skill, calls the tool, gets a tool-not-found error, falls into the "I cannot drive" disclaim path. | Deferred tools need `ToolSearch` to load first. Step 0 above is mandatory. |
| Using `ScheduleWakeup` in a non-`/loop` session | Single `ScheduleWakeup` call in a regular conversation that needed `CronCreate`. | `ScheduleWakeup` is for `/loop` dynamic-mode pacing; without `/loop` context it isn't the right tool. |
| Self-rescheduling per fire | Each fired turn calls `ScheduleWakeup` to schedule the next one. Any forgotten call kills the loop. | Use a recurring `CronCreate`. The cron does the rescheduling; the agent only has to remember when to `CronDelete`. |
| Confusing `Monitor` with driving | "Monitor `bd5po7f0p` will fire on terminal state." Then silence. | `Monitor` watches one bash task. It doesn't iterate, doesn't handle multiple targets, doesn't autonomously wake. |
| Vague cron prompt | `CronCreate(prompt="check on things")` | Fired turn has no context, can't reconstruct intent, makes wrong decisions. Always encode the digested directive + target list + termination criteria + iteration_count. |
| Forgetting to `CronDelete` when work is done | Cron keeps firing every cadence for 7 days after the work finished, agent has to no-op each fire. | When termination criteria met, call `CronDelete <job-id>`. |
| Briefing the operator between fires | Fired turn ends with "Update: PR #42 still pending, will check again next hour." | The operator is not watching. Save the report for when they ping you, or for the escalation case. Silence between fires is correct. |

## Incident justification

**Incident A (the original failure mode -- silent after Monitor):** an operator-driven session in which the operator said *"I need to be gone for a few hours, can you drive while I am gone?"* The agent's last response set up `Monitor` on one background bash task and ended its turn. **Zero tool calls in the next 8 hours.** Operator returned to *"What happened?"* Root cause: agent thought `Monitor` was the same as driving. `Monitor` notifies on terminal state of one background bash; it does not autonomously fire a new turn.

**Incident B (the praise-seeking failure mode this rewrite addresses):** operator tells the agent to drive. Agent does one task, presents a progress report ("Here's what I did..."), ends the turn waiting for acknowledgment. The next iteration never fires because no recurring scheduler was set up and the agent's `Brief the operator` instinct ended the turn. Operator returns to find one task done out of many. Root cause: the prior version of this skill made continuation a per-fire decision and instructed the agent to "brief the operator" after each wakeup -- two instructions that together produce the one-iteration-then-stop shape.

The rewrite addresses both by: (1) requiring `CronCreate` (recurring) instead of self-rescheduling `ScheduleWakeup` in regular sessions, so continuation is automatic; (2) explicitly forbidding progress reports between fires; (3) making termination an active decision (`CronDelete`), not a passive one (forget to reschedule).

## Cross-references

- `[rule:writing-prose]` writing-prose:5 -- the speech-time rule that requires a mechanism call for future-action commitments. This skill is the operational playbook for which mechanism in which cadence.
- `[rule:writing-claims]` writing-claims:9 -- applies when the agent claims state about what's happening between fires ("the build took effect"). Each fired turn must probe before claiming.
- `[skill:wrap-up]` -- the symmetric session-end skill. Use wrap-up when the work is genuinely done; use this skill when the work continues past the operator's availability.
- `[skill:think]` -- for non-trivial drive-while-away setups (overnight, multi-day, cross-system), run think first to design the loop's termination, escalation, and rollback paths before scheduling.

## Quick reference

```
Operator: "Drive while I'm gone for the next 3 hours."

Agent (same response):
1. ToolSearch("select:CronCreate,CronList,CronDelete", max_results=3)
2. Restate directive + identify targets + pick cadence (e.g., every 20 min: "7,27,47 * * * *")
3. CronCreate(cron="7,27,47 * * * *", recurring=true, prompt="<digested directive + targets + termination + iteration_count=0>")
4. Brief operator: "Cron job <id> set, firing at :07/:27/:47. Watching <targets>. Stops on <criteria>. Auto-expires in 7 days. Stop with /cron-delete <id>."
5. End turn.

On each fired turn:
1. Read directive from prompt.
2. Check each target via real tool calls.
3. Take action per result.
4. If terminated → CronDelete + brief operator with what was accomplished.
5. If escalation → surface + CronDelete.
6. Otherwise → end turn silently. The cron fires the next one.
```
