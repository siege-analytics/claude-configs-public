---
name: drive-while-away
description: When the operator hands off continuous work for an extended period ("drive while I'm gone," "monitor X overnight," "keep going while I'm out," "watch this and handle it"), set up the actual autonomous re-entry mechanism in the same response. Drives the operator's intent across the temporal gap they cannot bridge by typing.
allowed-tools: Read Grep Glob Bash Write Edit
---

# Drive While Away

## When to invoke

The operator's message contains any of these shapes:

- "Drive while I'm gone" / "drive while I'm out" / "drive while I'm away"
- "Monitor X" / "watch X" / "keep an eye on Y" -- paired with a time horizon longer than the typical turn
- "Keep going" / "keep the work moving" / "keep doing X" -- when the operator is leaving
- "Check back periodically on Z" / "loop back when W happens"
- "I'll be gone for a few hours, can you handle ...?"
- Any explicit time-bounded handoff: "for the next hour," "overnight," "until I'm back"

If the request is a one-shot wait for a single known-completing task ("wait until the build finishes"), use the `Monitor` tool alone. This skill is for *driving* -- continuous, multi-target, possibly multi-action work that has no single terminal event.

## The core failure mode this skill prevents

**Without this skill, the agent says "I'll drive" or "standing by" and goes silent for hours.** The next user prompt is the only thing that wakes it. The operator returns to find zero tool calls in the gap and asks "what happened?" The answer is: the agent's turn ended after acknowledging, and nothing fired the next one.

**Why "Monitor" alone is insufficient.** The `Monitor` tool watches a single background bash task and notifies on terminal state. It does not autonomously fire a new turn. It does not handle multiple targets. It does not allow the agent to *act* between completions. The agent's next opportunity to act is still the next user prompt.

**Why `ScheduleWakeup` is the actual mechanism.** `ScheduleWakeup` schedules a future turn-start. When it fires, the agent re-enters the session with the prompt encoded in the call, evaluates state, takes action, and decides whether to schedule the next wakeup. This is the only mechanism in the Craft Agent / Claude Code runtime that produces an autonomous turn without an inbound operator prompt.

## Mandatory response shape

When the trigger fires, the agent's response to the operator MUST include -- in the same response, before returning control -- a `ScheduleWakeup` tool call with:

1. **`delaySeconds`** -- chosen per the cadence table below.
2. **`prompt`** -- the full intent encoded so the woken turn has something to act on. Include: what to check, what to do if state X, what to do if state Y, when to stop, the operator's original directive verbatim.
3. **`reason`** -- one short sentence stating what you're waiting for, surfaced in telemetry and shown to the operator.

If you cannot call `ScheduleWakeup` (tool unavailable in this runtime, no time horizon supplied, intent too vague to encode), say so explicitly and disclaim continuation:

> "I don't have a continuation mechanism for this. If <event> happens, you'll need to tell me."

Per `[rule:writing-prose]` writing-prose:5 and `[rule:writing-claims]` writing-claims:9, "I'll drive" + no mechanism is a lie of omission.

## Cadence → mechanism mapping

| Cadence the operator wants | Mechanism | `delaySeconds` |
|---|---|---|
| Wait for one known-completing task | `Monitor` tool alone (no ScheduleWakeup needed) | n/a |
| Tight polling, active work in flight | `ScheduleWakeup` self-rescheduling loop | 60-270s (under the 5-min cache TTL) |
| Periodic check while operator is gone briefly | `ScheduleWakeup` self-rescheduling loop | 1200-1800s (20-30 min) |
| Overnight / multi-hour drive | `ScheduleWakeup` self-rescheduling loop | 1800-3600s (30-60 min) |
| Drive that depends on an external scheduler firing | `ScheduleWakeup` + cron / Airflow / n8n hand-off | varies; document both |

**Why no 5-minute mark.** The Anthropic prompt cache has a 5-minute TTL. A `ScheduleWakeup` at exactly 300s pays a cache miss for nothing. Either stay under 270s (cache warm, cheap re-entries) or go to 1200s+ (one cache miss amortized over a longer wait). 300s is the worst of both worlds.

## Self-rescheduling loop pattern

Each fired wakeup MUST decide whether to schedule the next one. The loop terminates only when:

1. The operator returns and explicitly says "stop driving" or asks a focused question that shifts the work.
2. The work is genuinely done (the last target reached terminal state, all PRs merged, etc.).
3. The agent decides -- with evidence -- that further iteration is unproductive (worker permanently stuck, state hasn't changed in N wakeups, dependency outside the agent's scope).

If none of those is true, the agent calls `ScheduleWakeup` again before returning. The loop dies silently if any wakeup forgets to schedule the next; treat the schedule-next call as the loop's heartbeat.

The prompt passed to each wakeup should re-encode the loop's intent so a future cold-start turn has full context. Bake in:

- The original operator directive verbatim.
- The current set of targets (URLs to PRs, job IDs to poll, file paths to grep, etc.).
- The success criteria for each target.
- The escalation criteria (when to stop and surface to operator).
- An `iteration_count` or `started_at` field so the woken turn knows how long the loop has been running.

## Procedure

### Step 1: Restate the directive

Before calling `ScheduleWakeup`, restate the operator's directive in your own words so the wakeup prompt encodes a digested version, not the raw operator message. Example:

> Operator: "Drive while I'm gone -- watch the gold MV, deprioritize the backfills if they take headroom, merge any unmerged PRs."
>
> Restated: Drive the post-Phase-2.1.1 verification loop: poll the gold MV's `updated_at` and row counts every 30 min, deprioritize backfill jobs if Spark Connect shows queue pressure, check for unmerged PRs on the configured projects every 30 min and merge if they meet the merge criteria for the relevant skill.

### Step 2: Identify the targets

List every concrete thing the loop will check. For each target:

- A single command or query that produces a yes/no or numeric answer.
- An action to take per answer.
- A way to know when the target is done.

If a target is too vague to encode this way, ask the operator to narrow it before the loop starts. Do not loop on vague targets.

### Step 3: Pick the cadence

Use the table above. Bias toward the lower end if active work is in flight; bias toward the upper end if the operator is away for hours.

### Step 4: Call `ScheduleWakeup`

Same response, before returning control to the operator. Include the digested directive, the target list, the criteria, and an iteration_count field.

### Step 5: Brief the operator

Tell the operator concretely what you've set up:

- The cadence ("waking every 30 min")
- The first wakeup time in their local timezone
- The targets being watched
- The termination conditions
- How they can stop the loop ("ping me, or change my standing instructions")

### Step 6: When the wakeup fires

Each fired wakeup runs the procedure:

1. Read the digested directive from the wakeup prompt.
2. Run the check for each target.
3. Take the prescribed action per result.
4. Decide: schedule the next wakeup, escalate to operator, or terminate.
5. If continuing, call `ScheduleWakeup` again with iteration_count incremented and any state evolution baked in.
6. Brief -- even if briefly -- what the wakeup did. Don't go silent across wakeups.

## Anti-patterns this skill prevents

| Anti-pattern | What it looks like | What's wrong |
|---|---|---|
| Saying "I'll drive" without scheduling | Last assistant message ends with "Standing by; will probe when it lands." Zero tool calls follow. | No continuation mechanism. Next turn is the operator's next prompt, which may not come for hours. |
| Confusing `Monitor` with driving | "Monitor `bd5po7f0p` will fire on terminal state." Then silence. | Monitor watches one bash task. It doesn't iterate, doesn't handle multiple targets, doesn't autonomously wake. |
| Setting up `run_in_background` and walking away | Launches a polling shell script with no wakeup, no scheduled re-entry to read the output. | Background bash runs but the agent never reads its output. |
| Vague wakeup prompt | `ScheduleWakeup(prompt="check on things")` | Woken turn has no context, can't reconstruct intent, makes wrong decisions. |
| Forgetting to reschedule | First wakeup fires, agent acts, returns to operator without scheduling next. | Loop dies silently. Same outcome as never scheduling at all. |

## Incident justification

Session `260531-lively-moss` (2026-05-31): operator said *"I need to be gone for a few hours, can you drive while I am gone?"* The agent's last response: *"Monitor `bd5po7f0p` will fire on terminal state. Standing by; will probe + report empirical accuracy the moment recon_daily lands."* **Zero tool calls in the next 8 hours.** Operator returned to *"What happened?"*

Root cause: agent thought `Monitor` was the same as driving. `Monitor` notifies on terminal state of one background bash; it does not autonomously fire a new turn, does not handle the multi-target work the operator asked for, does not produce continuous action. The agent's turn ended after acknowledging.

This skill exists because the rule (writing-prose:5) tells the agent that future commitments need a mechanism, but the agent confused two different "Monitor" things and never set up the actual `ScheduleWakeup` that produces autonomous re-entry.

## Cross-references

- `[rule:writing-prose]` writing-prose:5 -- the speech-time rule that requires a mechanism call for future-action commitments. This skill is the operational playbook for which mechanism in which cadence.
- `[rule:writing-claims]` writing-claims:9 -- applies when the agent claims state about what's happening between wakeups ("the build took effect"). Each fired wakeup must probe before claiming.
- `[skill:wrap-up]` -- the symmetric session-end skill. Use wrap-up when the work is genuinely done; use this skill when the work continues past the operator's availability.
- `[skill:think]` -- for non-trivial drive-while-away setups (overnight, multi-day, cross-system), run think first to design the loop's termination, escalation, and rollback paths before scheduling.

## Escalation

The wakeup loop must surface to the operator (via the wakeup prompt's reason field, or by stopping the loop and waiting for input) when:

- A target produces an unexpected error type the loop didn't anticipate.
- The same state has persisted across N wakeups (N=3 default) with no progress.
- An action the loop would normally take requires authorization the operator hasn't granted in advance (destructive ops, third-party API writes, anything in the operator's standing "ask first" list).
- The loop has been running longer than the operator's stated time horizon -- *"a few hours"* expired four wakeups ago; check whether the operator forgot.
