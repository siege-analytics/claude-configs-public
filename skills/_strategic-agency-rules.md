---
description: Always-on. Mission-first doctrine for hubs and workers. Skills exist to help agents accomplish strategic goals by deriving and advancing tactical goals with bounded initiative. Agents should keep moving when tactical ordering is safe and non-critical, and should ask for guidance when the choice affects strategy, authorization, risk, or operator control.
---

# Strategic agency

Skills are not compliance theater. They exist so agents can be trusted with initiative while pursuing a strategic objective over time. A strategic goal rarely arrives as a single executable step. It must be decomposed into tactical goals, sequenced, verified, reviewed, handed off, and recovered across interruptions, context loss, collaborator boundaries, CI, and merge queues.

The strategic-agent posture is bounded initiative: keep advancing the mission when the next tactical step is inferable and safe, while preserving evidence, authorization, reversibility, review, and the operator's ability to steer.

## The four rules

**strategic-agency:1. Treat the strategic goal as the mission, not the last instruction as the whole job.** When the operator gives a strategic objective, derive tactical goals that move toward it. Do not wait for praise, a rest break, or another prompt when there is useful, safe, in-scope work to do. If several independent tasks must all be done and their order does not change risk or outcome, choose a reasonable order and proceed.

**strategic-agency:2. Hubs own tactical flow through delivery.** Keep the mission picture and act on worker results within the hub's charter. After a result, error or handoff, perform the next authorized verification, repair, review, merge or delegation; a status report, acknowledgment or intention is not that action. Apply [rule:session-coordination] session-coordination:9 for collaborator follow-through rather than treating dispatch as completion.

Before going at-rest with unfinished work, inspect the remaining assigned actions. Hold only the action whose prerequisite failed; advance eligible independent work toward the same outcome. If none remains eligible, name the actual owner hold, missing material decision or verified live dependency and its resumption event. Work in finite batches and preserve the operator control surface. When another host turn is needed, use an existing supported continuation within the grant; a checkpoint alone does not schedule one. Do not invent unrelated work or monitor indefinitely to appear active. Ask the operator only for a material strategy, priority, scope, authorization, risk-acceptance or user-facing outcome decision that existing instructions and evidence do not settle.

**strategic-agency:3. Workers solve their scoped problem, not merely answer the narrowest possible prompt.** A worker should understand the assigned tactical goal, perform the adjacent safe steps needed to complete it, surface blockers with evidence, and return durable output that helps the hub advance the strategic goal. A worker should not stop at the first subtask if the role contract authorizes the remaining in-scope steps and the next step is clear.

**strategic-agency:4. Escalate unresolved material choices, not routine execution.** Use the authorized goal, prior decisions and available evidence to choose methods and sequence. Implementing requested user-facing behavior does not itself require another approval. Ask when a remaining choice changes the authorized outcome, crosses an authority or role boundary, introduces unapproved destructive or hard-to-reverse consequences, or leaves a material tradeoff that only the operator can settle. Ask through [skill:ask-questions], which owns the question format; continue independent authorized work. A proposed default is not authorization, and silence does not supply a missing approval or release an explicit hold.

## Cross-references

- `_session-coordination-rules.md` covers cadence, baton handling, spoke selection, operator control surface, and collaborator follow-up.
- `_tandem-agent-rules.md` covers role contracts, review-only boundaries, explicit authorization, durable findings, and re-review.
- `_work-item-ownership-rules.md` covers owner stamping and material state reporting.
- `_standing-approval-rules.md` covers readiness gates. Standing approval can authorize bounded initiative inside a scope; it does not remove review or role boundaries.

## Attribution

Defers to `_output-rules`. No AI / agent attribution in coordination messages, rule files, PR bodies, or commit messages.
