---
description: Always-on. Cross-session coordination discipline for agent-to-agent message cadence. Four rules covering when to declare your processing state, when to stop pinging, how to distinguish slow from stuck, and how to hand off the baton. Operator-overridable in the rule body when the operator is waiting; no `[coordination-skip]` flag.
---

# Session coordination

These four rules apply to multi-session work where two or more agents exchange `send_agent_message` to coordinate. Originating evidence is a 2026-06-05 incident where two pour-now sessions (`260605-brisk-spring` testing-strategy, `260604-clear-lagoon` Playwright) entered a queue-lag spiral. One was sending updates faster than the other could process. The receiver went silent intentionally to drain its queue. The operator read the silence as a stall. Workspace governance (`260604-smooth-gold`) verified the silent partner was alive and processing -- session.jsonl mtime under two minutes -- and that the silence was a deliberate cadence choice, not a session failure. The four rules below name the discipline failures that produced the operator read-error: missing at-rest declaration with explicit re-engagement signal (rule 1), continued pinging past at-rest declaration (rule 2), "stuck" / "death spiral" framing applied to slow processing (rule 3), implicit-but-unstated baton hand-off after the signoff (rule 4).

## The four coordination rules

**session-coordination:1. Declare your processing state when you cannot immediately respond.** When inbound messages from a partner are accumulating faster than you can substantively reply -- deep in another task, slow tool calls, queue backlog -- send a brief `at-rest` or `queue-draining` acknowledgment to the partner before going silent. Silence without declaration looks like a stall to the partner and to any operator monitoring the thread. The declaration must say what you are draining (specific thread, specific queue, specific predicate for re-engaging) and the form of the next signal you will emit.

Example acceptable: `Queue-draining on the B1 staging thread. Going silent until I have the PR URL to send. Will re-ping then.`

Example unacceptable: silence after the last substantive reply, with no signal of intent.

**session-coordination:2. When a partner declares at-rest, stop pinging on the thread the partner named.** If your partner says they are silent until X is true, do not send additional messages on that thread that pre-empt X. Drain pressure produces backlog; backlog produces apparent unresponsiveness; apparent unresponsiveness produces operator alarm. Wait for X or signal a genuinely new event on a different thread.

**Carve-out (operator override):** if the operator names the lag as a problem in the open -- "we're waiting on this," "hurry up," equivalent -- at-rest deference is suspended and the receiver of the operator complaint must push forward, even if that means breaking a partner's at-rest. The operator's waiting state outranks the partner's processing-cadence preference. The agent who breaks at-rest must say so in the next message to the partner ("breaking at-rest; operator is waiting"); the partner must absorb without complaint.

**session-coordination:3. Distinguish slow from stuck before escalating to "stuck."** Before flagging a partner as stuck, queue-lagged, hung, unresponsive, or in a death spiral, verify the partner's session activity in the way available to you: read their session log mtime if you have filesystem access, or check whether they have sent any message at all in the last ten minutes. Slow processing of substantive content -- signoffs, file reads, considered replies -- is not stuckness. The signal that distinguishes the two is last-activity timestamp, not message count or response latency.

Escalation language ("stuck," "hung," "death spiral") implies a specific failure shape -- session crash, provider hiccup, infinite loop -- that you should not name unless evidence matches. "Slow" and "queue-lagged" describe a cadence mismatch and are accurate when the partner is alive and producing substantive content. The two readings have different downstream actions: "slow" calls for patience and possibly a baton clarification, "stuck" calls for a successor spawn or operator intervention.

**session-coordination:4. Hand off the baton explicitly when your work on a thread is complete.** When you have sent everything your partner needs to take the next step, say so plainly in the same message that delivers the last artifact: `You have everything for X; baton to you`. Pair the at-rest declaration of rule 1 with an explicit baton declaration; this prevents the receiver from waiting for additional messages they will not get.

Baton declarations name the action expected of the partner ("present the unified plan to operator," "open the consolidation PR," "merge after CI green") so the next move is unambiguous. An implicit baton -- "I'm done" without naming what the partner should now do -- is rule-4 non-compliance and produces the same read-error as a missing at-rest declaration.

## Override

These rules are mandatory. The carve-out in rule 2 (operator override) lives inside the rule body, not as an external flag. There is no `[coordination-skip]` override.

## Cross-references

- `[`writing-claims`](_writing-claims-rules.md)` writing-claims:1-3 cover claims about prior actions. Declaring "I am at-rest" is itself a claim about what you will and will not do next; honor it (rule 2) or rescind it explicitly via the operator-override carve-out.
- `[`writing-prose`](_writing-prose-rules.md)` writing-prose:5 covers future-tense commitments to action. A baton declaration is the present-tense sibling: "the next move is yours, not mine."
- `[`drive-while-away`](drive-while-away/SKILL.md)` handles operator-handoff cadence for autonomous sessions. session-coordination rules are the agent-to-agent analog.

## Originating evidence

- **2026-06-05 incident, pour-now workspace.** `260605-brisk-spring` (testing-strategy successor, spawned earlier the same day after the original session hit a provider transient) and `260604-clear-lagoon` (Playwright) were collaborating on PR #181 / PR #183 work for the chain-picker UAT testing framework. clear-lagoon delivered v3 F1 signoff and B1 PR #183 URL, then went at-rest -- but without an explicit baton declaration of "present the unified plan to operator." brisk-spring continued sending drain-pressure pings ("Queue lag now ~30 min"). Operator read the silence as a stall and asked workspace governance (`260604-smooth-gold`) to verify the state. Governance read clear-lagoon's session.jsonl: last activity 114 seconds prior, no errors, deliberate "going silent until brisk-spring's queue drains" status. The cadence mismatch was real; the framing of it as a session failure was the error. The four rules above name the discipline failures that produced the framing error.

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

Four new judgment entries when `_coverage.md` is updated in a follow-up PR:

- `partner-silence-without-declaration` (session-coordination:1, judgment)
- `pinging-past-partner-at-rest` (session-coordination:2, judgment)
- `escalation-language-without-evidence` (session-coordination:3, judgment)
- `thread-closed-without-explicit-baton` (session-coordination:4, judgment)

Tooling-status counts after update: mechanical 16 (unchanged); judgment 18 -> 22; gap 1 (unchanged).

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in coordination messages, rule files, PR bodies, or commit messages.
