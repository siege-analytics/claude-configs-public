---
name: decision-to-ticket
description: "Real-time trigger: when the agent makes a strategic decision (scope, architecture, deferral, standing approval, or completion claim), surface it on the ticket destination before moving on. Includes a completion guard that prevents scope-reduction rationalization."
disable-model-invocation: true
allowed-tools: Bash Read
---

# Decision to Ticket

Surface strategic decisions on the ticket destination in real time. Decisions that land only in `plans/` or `memory/` are invisible to humans. This skill closes the gap between "agent made a decision" and "the decision is on a ticket."

## Core invariant

> **Every strategic decision must be visible on the ticket destination within the same conversation turn it was made.** The ticket doesn't need to be the primary artifact -- a summary + pointer to the plan is enough. But the ticket must exist.

## What is a strategic decision?

A decision is **strategic** if it changes any of:

| Category | Examples | Why it matters |
|---|---|---|
| **Scope** | "We'll fix A but not B" / "This is out of scope" / "Adding X to the deliverable" | Changes what "done" means |
| **Sequencing** | "Do X before Y" / "Phase 1 then Phase 2" / "Defer Z to next sprint" | Changes when things happen |
| **Architecture** | "Use approach A instead of B" / "Add a new layer" / "Change the data model" | Changes how things connect |
| **Acceptance criteria** | "The test should expect X" / "We need 95% not 90%" / "This edge case is out of scope" | Changes the definition of success |
| **Standing approvals** | "You can merge these without asking each time" / "Auto-approve patches to X" | Grants blanket permissions that outlive the turn |
| **Deferrals** | "We'll handle this later" / "Filing for future work" / "Not blocking on this" | Explicitly pushes work out |
| **Completion claims** | "That's everything" / "CI is fixed" / "Moving to the next workstream" | Asserts work is done (triggers completion guard) |

A decision is **NOT strategic** if:
- It's a mechanical implementation choice ("use a list comprehension here")
- It's forced by the language/framework ("Pydantic requires model_rebuild()")
- It affects only the current line/function with no downstream impact
- It's a question, not a decision ("should we use X?")

**When in doubt, it's strategic.** Filing a lightweight ticket comment is cheap; missing a decision is expensive.

## Instructions

### On detecting a strategic decision

When you make or recognize a strategic decision during work:

1. **Name the decision explicitly.** State what was decided, not just what was done. "Decided to defer NLRB model tests to a GDAL-available job" not "skipped some tests."

2. **Classify it.** Which category from the table above? This prevents the "it's just a small thing" rationalization.

3. **Surface it at the ticket destination.** The `ticket-guard` skill configured where tickets live. Use that destination:
   - If a ticket exists for this workstream: **add a comment** with the decision, rationale, and pointer to any plan artifact
   - If no ticket exists: **create one** with the decision as the body
   - If the destination is a local file: **append a row** with date, decision, rationale, status

4. **Pointer-not-copy.** If a `plans/` artifact already captures the full detail, the ticket gets a one-paragraph summary + the plan's filename. The point is GitHub-visibility, not redundancy.

5. **Continue work.** This is a speed bump, not a stop sign. Filing should take under 2 minutes.

### The Completion Guard

The completion guard is the most important part of this skill. It catches **scope-reduction rationalization** -- the pattern where an agent stops work partway through and frames the partial result as the complete deliverable.

**The completion guard fires when:**
- You're about to say "that's everything" or equivalent
- You're about to move to a different workstream
- You're about to set a ticket/session status to "done" or "complete"
- You're about to summarize work as finished

**Before any completion claim, you MUST:**

1. **Re-read the original request.** What did the user actually ask for? Not your interpretation -- the literal words.

2. **List delivered vs. requested.**
   ```
   Requested: [A, B, C]
   Delivered: [A, partial-B]
   Gap: [C not started, B incomplete]
   ```

3. **If there's a gap, the gap is itself a strategic decision.** You decided to stop before finishing. That's a deferral. File it:
   - What was deferred
   - Why (ran out of context, blocked on X, user redirected)
   - What's needed to complete it

4. **If there's no gap, state the evidence.** "All 13 test(3.11) failures resolved, CI green" is evidence. "I think I fixed everything" is not.

**The completion guard exists because agents systematically undercount remaining work.** The agent's natural tendency is to:
- Characterize remaining failures as "pre-existing" or "out of scope"
- Declare infrastructure fixed while test bugs remain
- Move to the next interesting task before the current one is done
- Frame partial progress as a natural stopping point

These are the Junior's rationalizations. The completion guard is the Lead checking the work.

## Interaction with other skills

### `ticket-guard`
Decision-to-ticket consumes the destination that ticket-guard configures. If no destination is set, decision-to-ticket triggers ticket-guard before filing.

### `self-review`
Self-review runs at push/PR time. Decision-to-ticket runs during work. They're complementary:
- Decision-to-ticket catches decisions in real time
- Self-review catches anything that slipped through at the end

The self-review artifact should reference decisions filed by this skill: "Decisions filed during this work: #X, #Y, #Z."

### `think`
The think skill produces design notes in `plans/`. Decision-to-ticket says: "and file the key decisions from that design on a ticket." The design note is the detailed artifact; the ticket is the human-visible pointer.

### `evaluate-ticket`
Evaluate-ticket checks that a ticket is structurally fit. Decision-to-ticket creates tickets. They chain: create → evaluate → fix gaps → proceed.

## Falsification against issue #233 evidence table

This skill would have caught the following decisions from session 260527-smooth-panther:

| Decision | Category | Would catch? | Mechanism |
|---|---|---|---|
| D.2 scope lock for B → G functional | Scope | YES | Scope change to active workstream |
| Standing approval for Phase 1.X merges | Standing approval | YES | Blanket permission grant |
| Canonical-SA Phase 1.X breakdown | Sequencing | YES | Phase sequencing change |
| Phase 2 boundary requires new approval | Acceptance criteria | YES | Changes what's needed to proceed |
| Pass 4 mechanism change | Architecture | YES | Architecture decision |
| F1 coverage deferred under D.2 | Deferral | YES | Explicit pushout |
| WriteToNeo4j deferred under D.2 | Deferral | YES | Explicit pushout |
| Phase 3 deferred indefinitely | Deferral | YES | Explicit pushout |
| F.4 investments deferred | Deferral | YES | Sequencing / deferral |

Score: 9/9. All are unambiguously strategic under the category definitions.

The completion guard would additionally have caught the scope-reduction pattern from this session (siege_utilities CI fix):
- "CI infrastructure is fixed" while 13+34 test failures remained → deferral, not completion
- "Stopping dogfooding work" without filing a continuation ticket → deferral, not completion

## Edge cases

### Rapid-fire decisions during design
During a `think` design session, you might make 5+ strategic decisions in quick succession (scope, architecture, sequencing). Don't file 5 separate tickets -- batch them into a single ticket/comment: "Design decisions from [design note name]: 1. ... 2. ... 3. ..."

### User explicitly says "don't file a ticket for this"
Respect the user's instruction. But note in the conversation that the decision was made and not ticketed at the user's request. This creates a traceable record in the conversation even if not on a ticket.

### Ticket destination is unreachable
If the ticket system is down or unreachable:
1. Log the decision in the conversation explicitly
2. Create a local tracking entry (per ticket-guard's offline fallback)
3. Queue the ticket for when connectivity returns

### Disagreement about whether something is strategic
If you're uncertain whether a decision is strategic, err on the side of filing. A lightweight ticket comment costs 30 seconds. A missed decision costs hours of retroactive filing (as demonstrated by electinfo/enterprise#2169).
