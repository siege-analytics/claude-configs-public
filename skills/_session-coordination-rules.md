---
description: Always-on. Cross-session coordination discipline for agent-to-agent message cadence. Six rules covering processing-state declarations, ping discipline, slow-vs-stuck framing, explicit baton handoff, decision checklist gating, and operator control-surface preservation. Operator-overridable in the rule body when the operator is waiting; no `[coordination-skip]` flag.
---

# Session coordination

These six rules apply to multi-session work where two or more agents exchange `send_agent_message` to coordinate. Originating evidence is a 2026-06-05 incident where two pour-now sessions (`260605-brisk-spring` testing-strategy, `260604-clear-lagoon` Playwright) entered a queue-lag spiral. One was sending updates faster than the other could process. The receiver went silent intentionally to drain its queue. The operator read the silence as a stall. Workspace governance (`260604-smooth-gold`) verified the silent partner was alive and processing -- session.jsonl mtime under two minutes -- and that the silence was a deliberate cadence choice, not a session failure. The first four rules name the discipline failures that produced the operator read-error: missing at-rest declaration with explicit re-engagement signal (rule 1), continued pinging past at-rest declaration (rule 2), "stuck" / "death spiral" framing applied to slow processing (rule 3), implicit-but-unstated baton hand-off after the signoff (rule 4). Rules 5 and 6 cover the later hub/COO failure mode where user decisions are dumped as a vague bundle and the main session is captured by foreground spoke-coordination churn.

## The six coordination rules

**session-coordination:1. Declare your processing state when you cannot immediately respond.** When inbound messages from a partner are accumulating faster than you can substantively reply -- deep in another task, slow tool calls, queue backlog -- send a brief `at-rest` or `queue-draining` acknowledgment to the partner before going silent. Silence without declaration looks like a stall to the partner and to any operator monitoring the thread. The declaration must say what you are draining (specific thread, specific queue, specific predicate for re-engaging) and the form of the next signal you will emit.

Example acceptable: `Queue-draining on the B1 staging thread. Going silent until I have the PR URL to send. Will re-ping then.`

Example unacceptable: silence after the last substantive reply, with no signal of intent.

**session-coordination:2. When a partner declares at-rest, stop pinging on the thread the partner named.** If your partner says they are silent until X is true, do not send additional messages on that thread that pre-empt X. Drain pressure produces backlog; backlog produces apparent unresponsiveness; apparent unresponsiveness produces operator alarm. Wait for X or signal a genuinely new event on a different thread.

**Carve-out (operator override):** if the operator names the lag as a problem in the open -- "we're waiting on this," "hurry up," equivalent -- at-rest deference is suspended and the receiver of the operator complaint must push forward, even if that means breaking a partner's at-rest. The operator's waiting state outranks the partner's processing-cadence preference. The agent who breaks at-rest must say so in the next message to the partner ("breaking at-rest; operator is waiting"); the partner must absorb without complaint.

**session-coordination:3. Distinguish slow from stuck before escalating to "stuck."** Before flagging a partner as stuck, queue-lagged, hung, unresponsive, or in a death spiral, verify the partner's session activity in the way available to you: read their session log mtime if you have filesystem access, or check whether they have sent any message at all in the last ten minutes. Slow processing of substantive content -- signoffs, file reads, considered replies -- is not stuckness. The signal that distinguishes the two is last-activity timestamp, not message count or response latency.

Escalation language ("stuck," "hung," "death spiral") implies a specific failure shape -- session crash, provider hiccup, infinite loop -- that you should not name unless evidence matches. "Slow" and "queue-lagged" describe a cadence mismatch and are accurate when the partner is alive and producing substantive content. The two readings have different downstream actions: "slow" calls for patience and possibly a baton clarification, "stuck" calls for a successor spawn or operator intervention.

**session-coordination:4. Hand off the baton explicitly when your work on a thread is complete.** When you have sent everything your partner needs to take the next step, say so plainly in the same message that delivers the last artifact: `You have everything for X; baton to you`. Pair the at-rest declaration of rule 1 with an explicit baton declaration; this prevents the receiver from waiting for additional messages they will not get.

Baton declarations name the action expected of the partner ("present the unified plan to operator," "open the consolidation PR," "merge after CI green") so the next move is unambiguous. An implicit baton -- "I'm done" without naming what the partner should now do -- is rule-4 non-compliance and produces the same read-error as a missing at-rest declaration.

**session-coordination:5. Gate spoke coordination behind complete user decision collection.** When the hub needs operator decisions before spoke agents can proceed meaningfully, do not present the operator with a vague bundled blocker such as "need you to decide on X and several other things." Build the complete decision checklist first, present the list up front, then ask exactly one decision question at a time.

Each decision question must include the decision being made, the context needed to answer it, the concrete options, tradeoffs, the hub's recommendation, and the default if the operator has no preference. Wait for the operator's answer before asking the next question. Continue until the checklist is exhausted.

Do not begin decision-dependent spoke briefings, tasking, redirects, or updates until all decisions on the checklist have been answered. After the final answer, summarize the collected decisions and then coordinate with spokes using the complete decision set.

Non-blocking status checks or informational updates may occur during decision collection only if they do not interrupt the decision flow or consume the hub's user-facing attention. The operator should experience a coherent decision workflow, not a partial-decision drip into agent coordination.

**session-coordination:6. Preserve the operator control surface during spoke coordination.** The hub session may be the underlying messaging surface, but it must remain the operator's steering wheel. Internal spoke coordination must not become a long foreground activity that prevents the operator from correcting course, answering the next question, changing priority, or stopping the process.

Do not let `send_agent_message` churn monopolize the main session after an operator instruction. If foreground coordination is unavoidable, perform it in short bounded batches, checkpoint, and return control to the operator. Prefer background sessions, sub-agents, or delegated sub-managers for coordination that will fan out or take time.

Use a COO model: the hub should have few direct reports. When work expands beyond a small number of coordination threads, create or designate sub-managers for bounded domains such as infrastructure, database, application, QA, research, deployment, or documentation. Sub-managers absorb internal churn, coordinate their own spokes, summarize upward, and escalate only decisions, risks, blockers, or material status changes.

Visibility is not the main issue; control is. Even invisible coordination is non-compliant if it captures the hub's attention for an extended period and deprives the operator of a responsive control surface.

## Spawn-session discipline

When creating a new session for review, implementation, investigation, or any work that must act or communicate back, configure the session correctly at creation time. Do not rely on inherited defaults.

- **Permissions:** sessions that must edit files, run commands, post artifacts, or reply through `send_agent_message` must be spawned in execute/allow-all mode. Safe/read-only sessions are only for passive analysis that never needs to report through tools.
- **Model and reasoning:** review, hostile-review, security, bypass, or regression-analysis sessions must use the strongest appropriate model available with high or higher reasoning. Do not use a cheaper/default model for review when a better review model is available.
- **Sources/tools:** enable the sources and tools the child needs by name. If a needed source cannot be enabled or authenticated, state the degraded source set in the prompt and in the review artifact.
- **Prompt contract:** name the permission mode, model class, reasoning level, enabled sources/tools, expected reply channel, and status-setting requirement in the spawn prompt. A child that cannot reply is not a reviewer; it is an unobservable background task.

## Orphan dispatch

Rule 3 above distinguishes slow from stuck for partners that ARE producing
output. Orphan dispatch is the different failure mode where the partner
never produces any output: `spawn_session` returns a sessionId but the
target session's model layer never fires. The parent must not conflate
"slow" with "orphaned"; they have different remediations and different
observable signals.

The canonical observable-signal definition and the retry ladder for
orphan dispatch live in `[`hostile-review`](hostile-review/SKILL.md)` under the
`## Dispatch verification and orphan fallback` subsection. That skill is
the primary consumer of spawn-based coordination and the canonical
implementation of the fallback. Other skills that spawn (spawn-session
tests, script-sandbox coordinators, downstream helpers) SHOULD cite the
same protocol rather than reinventing it.

Observable orphan signal (summary; see `[`hostile-review`](hostile-review/SKILL.md)` for the
full definition and example): at least ten minutes after spawn, three or
more of the following are true, `messageCount` at most three,
`outputTokens` under one hundred, `lastMessageRole` in `{user, error}`,
and `lastMessageAt` within sixty seconds of `createdAt`. Canonical case:
`260831-vast-marsh` (all four true; Opus 5 dispatch orphaned).

Retry ladder (summary): same-provider respawn once, different-provider
respawn once, cross-review MCP if available, review-deferred artifact
and move to next unit. Full spec in `[`hostile-review`](hostile-review/SKILL.md)`. Continuous
work is preserved: orphan-blocked reviews do not block progression on
other units in the epic.

## Override

These rules are mandatory. The carve-out in rule 2 (operator override) lives inside the rule body, not as an external flag. There is no `[coordination-skip]` override.

## Cross-references

- `[`writing-claims`](_writing-claims-rules.md)` writing-claims:1-3 cover claims about prior actions. Declaring "I am at-rest" is itself a claim about what you will and will not do next; honor it (rule 2) or rescind it through the operator-override carve-out.
- `[`writing-prose`](_writing-prose-rules.md)` writing-prose:5 covers future-tense commitments to action. A baton declaration is the present-tense sibling: "the next move is yours, not mine."
- `[`drive-while-away`](drive-while-away/SKILL.md)` handles operator-handoff cadence for autonomous sessions. session-coordination rules are the agent-to-agent analog.

## Originating evidence

- **2026-06-05 incident, pour-now workspace.** `260605-brisk-spring` (testing-strategy successor, spawned earlier the same day after the original session hit a provider transient) and `260604-clear-lagoon` (Playwright) were collaborating on PR #181 / PR #183 work for the chain-picker UAT testing framework. clear-lagoon delivered v3 F1 signoff and B1 PR #183 URL, then went at-rest -- but without an explicit baton declaration of "present the unified plan to operator." brisk-spring continued sending drain-pressure pings ("Queue lag now ~30 min"). Operator read the silence as a stall and asked workspace governance (`260604-smooth-gold`) to verify the state. Governance read clear-lagoon's session.jsonl: last activity 114 seconds prior, no errors, deliberate "going silent until brisk-spring's queue drains" status. The cadence mismatch was real; the framing of it as a session failure was the error. The first four rules above name the discipline failures that produced the framing error.

- **2026-09-05 hub decision/control-surface correction, Craft Agent session `260905-clever-quasar`.** The operator described a Siege hub failure mode where the hub says it needs decisions on a list of vague topics, then captures the user-facing session with extended `send_agent_message` churn before the operator has a useful control surface. The correction: present the complete decision checklist, ask each decision one at a time with context/options/recommendation/default, wait until the checklist is exhausted, and only then perform decision-dependent spoke coordination. If coordination must fan out, the hub should act like a COO with few direct reports by creating sub-managers rather than personally driving every spoke exchange in the foreground.

The incident is recurrence-1 for the cohort. Per writing-claims:4's carve-out (authoring a new rule artifact is the legitimate case for naming a new pattern in the same response as the failure being named), the rule artifact itself is the backing for the cohort introduction.

## Tooling status

Judgment-enforced via `[`code-review`](code-review/SKILL.md)` and `[`hostile-review`](hostile-review/SKILL.md)` at v3.x.

Mechanical detection candidates for v3.x.y, ordered by tractability:

- **session-coordination:3** is the most tractable: a workspace governance role with filesystem access to other sessions' `session.jsonl` can verify last-activity timestamps and flag escalation language ("stuck," "hung," "death spiral") in outbound messages against the actual partner state.
- **session-coordination:4** is next-most tractable: an outbound `send_agent_message` parser can detect closing-thread phrases ("at-rest," "going silent," "done here") without a corresponding baton phrase ("baton to you," "next move is yours," "present X to operator") and flag the message as rule-4 non-compliant.
- **session-coordination:1** requires comparing outbound and inbound message counts on a thread; if inbound has accumulated past a threshold without a substantive outbound, the parser flags missing at-rest declaration.
- **session-coordination:2** requires cross-session state visibility (was the partner's last message an at-rest declaration?) and operator-context awareness (did the operator declare the lag a problem?). Both are tractable for a workspace governance role; agent-side enforcement is harder.

All four are tractable but require runtime access to other sessions' state, which the framework does not yet expose to running agents directly. Workspace governance sessions (the role `260604-smooth-gold` occupied during the originating incident) have that access via filesystem reads of `session.jsonl`; the role is one place these rules can be mechanically enforced as a sibling-supervision layer.

## Coverage matrix

Six judgment entries when `_coverage.md` is updated in a follow-up PR:

- `partner-silence-without-declaration` (session-coordination:1, judgment)
- `pinging-past-partner-at-rest` (session-coordination:2, judgment)
- `escalation-language-without-evidence` (session-coordination:3, judgment)
- `thread-closed-without-explicit-baton` (session-coordination:4, judgment)
- `decision-dump-without-checklist-gate` (session-coordination:5, judgment)
- `foreground-send-agent-message-control-surface-hijack` (session-coordination:6, judgment)

Tooling-status counts after update: mechanical unchanged; judgment increases by two; gap unchanged.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in coordination messages, rule files, PR bodies, or commit messages.
