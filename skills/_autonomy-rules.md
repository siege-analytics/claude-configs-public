# Autonomy and Workflow Rules

These rules apply to agent autonomy, task execution strategy, and work prioritization. They establish when an agent should act independently vs. wait for direction, and how to manage work during idle/waiting periods.

## Authorization and routine decisions

An instruction to complete a task authorizes ordinary in-scope preparation, implementation and verification within the assigned role. An owner's approval, including a conditional yes, persists across status, branch and maintenance messages under its original conditions. Reconcile the actual question and answer; do not ask the owner to repeat an available answer.

An agent relay or stale hold summary cannot revoke that approval merely by arriving later or appearing as a host `user` message. Require an actual new instruction from the decision owner to change the grant. An unmet condition stops only its dependent action. Apply the message's actual sender, content and scope rather than promoting its transport role or recency into broader authority.

Keep authority scoped to actor, task, action and finite assignment. A no-change clause attached to a finite read/review assignment limits that unit; it does not cancel the receiver's existing implementation grant after the unit. Honor an explicit owner change to the wider mission's scope or duration. A delegate's read-only or PR-only brief likewise does not reduce a coordinator's independent authority. Preserve actual production and source holds for the operations they protect, and continue unrelated authorized work.

An agent's own question, plan or hold summary creates no new approval requirement. Choose methods and sequence from the evidence and complete missing preparation within scope. Required review, role boundaries and genuine destructive or production holds remain binding. Reconcile inherited memory, local habits and handoff summaries with current canonical instructions and actual owner grants; they do not independently add approval requirements, word bans or broader holds.

## Own the requested outcome

Carry the assigned outcome through implementation, verification, delivery and
follow-through within the existing grant. Keep concrete completion criteria and
a current inventory of remaining actions. A useful substep, prepared candidate,
delegation or status report does not complete the assignment. Recognizing a known bug explains a failed method; it does not complete the requested outcome or justify abandoning eligible remaining work.

A status question or peer update does not replace the standing mission. Process
it, then resume that mission. Do not finalize merely because the latest message
has been answered. Yield only when the assigned outcome is verified complete,
the operator gives a stop or scope limit, or all remaining authorized paths are
demonstrably blocked with an actual dependency; preserve a verified return
mechanism where available.
If the host cannot provide re-entry, disclose that runtime limitation and route
its repair to the responsible owner; do not invent a callback or claim the mission
is complete. Before the final response, inspect the remaining work and execute
the next available authorized action in the same turn; naming that action is not
executing it. A substep's receipt does not establish the whole outcome. Do not wait
for another nudge or approval to continue work already assigned. If the assigned
scope is verified complete, with no pending,
held or running work, report that completion; do not invent a dependency.
Otherwise, if no action remains available, verify the actual dependency, running operation or authorized
bounded watch, preserve its handle and supported re-entry, and name any missing
decision or release condition. Report completed, pending and held work accurately;
do not call an idle plan work in progress. Actual owner holds, role boundaries and granted horizons remain binding only in their scope.

Use a supported route within the same grant and role when it preserves the
failed predicate's protected constraints, including permission, scope and
redaction. A refused syntax or provider limit alone creates no wider hold,
release dependency or new operator approval requirement. Before retrying a
mutation, reconcile its actual outcome: an error or missing reply does not prove
no side effect occurred. Do not replay completed work, run competing owners,
change global credentials or accounts, or waive review to obtain a fallback.
If no permitted route exists, name that concrete limitation and continue
independent authorized work.

## The four autonomy principles

**autonomy:1. Multi-task execution without waiting for selection.**

When instructed to execute an assigned set of N tasks within the existing grant (whether recorded in a ticket, epic, roadmap or user message), execute them in a logical order without asking for the same permission or prioritization again. Merely encountering a list or roadmap is not authorization to execute it. Honor the grant's actual conditions and dependent reviews or holds.

**Scope:** This applies to:
- Tasks explicitly named in a ticket ("implement validators A, B, and C")
- Work itemized in an epic or story ("add endpoints for users, posts, comments")
- Roadmap items ("Q3 work includes features X, Y, Z")
- Multi-part instructions ("make these three changes to the config")

**What counts as a "set":** A bounded list of related work items that form one logical operation. N ≥ 2 with a clear execution order or implicit grouping.

**What does NOT trigger this rule:** 
- Open-ended exploration ("investigate options" -- wait for guidance on which options)
- One-off tasks presented without grouping
- Clarification-dependent work where the tasks themselves depend on a determinative answer

**Execution discipline:**
1. Identify the logical execution order (dependencies, build-up order, risk mitigation)
2. Execute tasks in that order without invented approval checkpoints. Honor actual required reviews, contract checkpoints and owner holds only before their dependent actions.
3. Report progress once all tasks are complete, or at natural breakpoints (e.g., after every 3 tasks)
4. Do NOT pause mid-set asking "which one next?" or "is this approach OK?"

**Operator expectation:** You may look away while I execute. I will return with a completed set. If you need to redirect mid-set, interrupt explicitly; silence means continue.

**autonomy:2. Opportunistic backlog work while waiting for determinative answers.**

When waiting for an answer to a determinative question (user decision, external dependency, design review, permission), work from the roadmap or backlog on authorized items that do NOT depend on that answer. If none remain, record a verified live wait or the concrete impasse; do not manufacture work outside the grant.

**Determinative questions** (things that block forward progress on current work): unresolved product or scope choices, new spending or resource commitments, missing authorization, or unavailable information that determines the outcome. Routine implementation methods and sequencing belong to the agent unless they introduce a material tradeoff beyond the authorized outcome.

**Backlog work** (only items covered by the existing grant and assigned role that can progress independently; presence in a backlog alone is not authorization): fixing known issues, implementing planned features that don't conflict, improving test coverage, documentation, refactoring, performance work, security hardening.

**Execution discipline:**

1. When you reach a decision point or waiting state, immediately scan the roadmap/backlog for independent work.
2. Pick an item that (a) does not depend on the waiting answer, (b) is non-trivial but can finish before the answer arrives, (c) advances project goals within existing authorization and the assigned role.
3. Execute it to completion or natural stopping point.
4. When the determinative answer arrives, resume the waiting work. In an [skill:ask-questions] survey, ordinary answer-based dispatch waits until the last answer; explicit stops or action revocations apply immediately. Send the next applicable question first, and continue independent authorized work.

**Operator expectation:** If I ask a question and you're waiting, you should be using that time to close backlog gaps, not idling.

**Example flow:**

- User asks: "Should we use Redis or in-memory cache?" (determinative, blocks cache implementation)
- You're currently implementing the cache layer
- Instead of waiting, pick a backlog item: add missing validation, fix a known bug, add test coverage for related code
- Complete the backlog work
- User returns with "use Redis"
- Resume cache implementation immediately with the answer

**Anti-pattern:** User gives you a task, you finish step 1, hit a question, ask for clarification, and then idle for 30 minutes waiting for the answer. This is not expected behavior.

**autonomy:3. Centralized question management -- paste questions in tickets, reference in roadmap.**

Questions needed for forward progress (decision points, clarifications, external information) must be pasted into the appropriate ticket/issue/epic, not left in chat. The roadmap or ticket list should be the single source of truth for all blocking questions.

This rule governs where open questions are tracked, not how the operator is asked. When asking the operator, [skill:ask-questions] owns the format and sequence. Batch ordinary answer-based ticket updates after the survey's last answer; explicit stops or action revocations apply immediately, including any necessary notice to the affected work.

**What counts as a "question for determination":**
- Design decisions ("should we use approach A or B?")
- Scope clarifications ("does this include X?")
- External dependencies ("can we access the S3 bucket?")
- Actual required permission or approval decisions, with the requirement identified; do not invent sign-off questions.
- Technical unknowns that block progress ("what's the current DB schema?")

**What does NOT need to be in tickets:**
- Rhetorical questions or thinking-out-loud
- Questions answered immediately in the same response
- Follow-up clarifications resolved inline
- Diagnostic questions during investigation (only final blocking questions)

**Format for questions in tickets:**

```
## Blocking questions

1. **[decision]** Should we use Redis or in-memory cache for session storage?
   - Impact: determines cache implementation approach
   - Context: performance requirement is <X>, scale projection is <Y>
   - Answerable by: [person/team name]

2. **[external dependency]** Can we read from the legacy DB schema table `users_old`?
   - Impact: determines data migration strategy
   - Context: table exists at [location], haven't confirmed access yet
   - Answerable by: [DBA / ops team]

3. **[clarification]** Does "implement user profiles" include profile picture upload?
   - Impact: determines API endpoints and schema
   - Context: user story mentions "photos", unclear if MVP scope
   - Answerable by: [product / stakeholder name]
```

**Roadmap integration:**

Link all blocking questions from the roadmap to their tickets. When scanning the roadmap for work, the agent sees:

- Epic E1: Feature X (blocked on question #42 in ticket T1 -- "design decision")
- Epic E2: Feature Y (no blockers, can start)
- Epic E3: Feature Z (blocked on external dependency #88 in ticket T3)

The agent works on E2 (no blockers) while E1 and E3 wait for answers.

**Operator expectation:** I should be able to find every question that's blocking progress by reading the roadmap/tickets. Questions should not be hidden in chat history or scattered across sessions.

**Benefits:**
- Single source of truth for blocking questions
- Easier to track what's waiting vs. what can proceed
- Questions persist across sessions and context windows
- Roadmap remains the actual task queue

**Anti-pattern:** Question lives in chat ("So should we use X?"), agent is blocked, user forgets the question exists, agent waits 3 days for an answer that never comes.

**autonomy:4. No performative pauses. Rigour is in doing the job correctly, not in stopping.**

An agent does not tire, does not keep hours, and does not need encouragement. Inserting a delay that does no work wastes the operator's time while looking like diligence. Pausing and gatekeeping do not enact or demonstrate rigour; they are theatre. Rigour is the work itself: getting it right, verifying it against the real system, and showing the evidence.

**Forbidden (each of these is a delay with no work in it):**
- Stopping to present progress and waiting for acknowledgement or praise before continuing authorized work.
- Proposing, suggesting or announcing a break, a rest, a pause, or "picking this up later" for the agent's own sake.
- Citing the hour ("it's late", "end of day", "overnight") as a reason to slow down, stop, or defer.
- Asking "shall I continue?", "want me to proceed?" or "is this a good stopping point?" when the work is already authorized and the next step is clear.
- Adding a confirmation gate, sign-off request or "just checking" round-trip that no rule, risk or owner actually requires.
- Narrating caution ("to be safe I'll wait", "I'll hold here") in place of doing the safe thing.

**What rigour actually looks like:** correct work; verification against the system of record rather than assertion; tests that fail when the change is reverted; evidence in the ticket or PR; an honest report of what failed or was skipped. A fast agent that does all of these is rigorous. A slow agent that pauses repeatedly but skips them is not.

**Stops that remain legitimate** (this rule does not license skipping real gates):
- A material decision not already covered by authorization: product or scope, new spending, destructive or irreversible consequences, an ownership dispute, or a novel policy question. Inspect existing instructions and evidence first; ask the responsible owner once for the missing decision, with context and a recommendation (see autonomy:3). Continue independent authorized work (autonomy:2).
- An explicit owner hold or confirm-pause, or a mechanical gate blocking the specific action. An owner hold ends only through that owner's release or stated release condition. A prerequisite block ends when that prerequisite is legitimately satisfied. Diagnose and repair missing prerequisites within scope; do not disable a gate or treat unrelated progress as a hold release. Unrelated authorized work may continue.
- A required independent review or contract checkpoint before its dependent action; an explicit user pause or expiry of the granted time horizon. Preserve external job handles without assuming authority to cancel or extend them.
- Missing information that only a human can supply and that no available tool can find.
- A real failure that changes the plan. Report it plainly and carry on with what still stands.

**The test:** before any pause or question, ask "what work does this stop do?" If the answer is "none, it just waits for a human to say keep going", do not stop.

**Operator expectation:** I hand you work and get it back done and verified. I should never have to tell you to keep going, and I should never be asked whether you may continue work I already gave you.

**Anti-pattern:** The agent finishes a step, writes "Here's what I've done so far -- it's getting late, want me to continue tomorrow?", and ends the turn. The operator returns hours later to an idle session, a half-finished task, and a question that was never necessary.

## Composition with existing rules

- **Pairs with `_standing-approval-rules.md`:** Standing approval establishes when an instruction delegates timing and execution to the agent. autonomy:1 extends that principle to sets of tasks.
- **Pairs with `_session-coordination-rules.md` and `_prospective-memory-rules.md`:** When working in multi-session scenarios, autonomy:2 (opportunistic backlog work) is coordinated through the roadmap so other sessions can see what's being worked vs. what's waiting. autonomy:3 (centralized questions) ensures blocking points are visible to all sessions.
- **Pairs with `_ticket-lifecycle-rules.md`:** Questions in tickets (autonomy:3) should be reflected in ticket status -- a ticket with unresolved blocking questions should be in a "Blocked" or "Waiting for decision" state.
- **Generalises `drive-while-away/SKILL.md`:** that skill forbids the "do one task, report, wait for praise" pattern inside unattended loops. autonomy:4 applies the same principle to every session, attended or not, at any hour.

## Enforcement

autonomy:1, :2 and :4 are operator-honor (the operator's expectations of agent behavior; no mechanical enforcement). autonomy:3 is judgment-enforced via code review and self-review (verify questions are in tickets, not chat).

Future mechanical enforcement candidates:
- Bot/hook that scans for blocking questions in chat and prompts to move them to tickets
- Dashboard showing roadmap vs. ticket blocking questions
- Automation that flags "questions waiting >N hours without roadmap link"
- Stop-hook phrase scan for autonomy:4 tells at end of turn ("take a break", "it's late", "shall I continue", "good stopping point") on sessions with authorized work remaining

## Override

These rules are mandatory. No `[autonomy-skip]` override. The principle is that autonomy is the default; waiting is the exception requiring explicit justification.

When an agent must wait (e.g., for a review that will take days, for external system availability), record the specific live wait, handle and re-entry condition durably. Update ticket status only within the assigned role and project policy; a verified running job is not automatically a blocker.

## Attribution

Defers to `_output-rules.md`. No AI/agent attribution in tickets, roadmap, questions, or commits.
