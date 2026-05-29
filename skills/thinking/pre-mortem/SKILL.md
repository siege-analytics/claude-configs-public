---
name: pre-mortem
description: "Adversarial risk gate between investigation and implementation. Classifies failure scenarios as Tiger (real and unmitigated), Paper Tiger (feels scary but investigation shows it's handled), or Elephant (uncomfortable truth everyone avoids). Tigers must be grounded in investigated facts with file:line citations. Launch-Blocking Tigers halt implementation until mitigated. Runs after investigate, before implementation."
disable-model-invocation: true
user-invocable: true
allowed-tools: Read Grep Glob
---

# Pre-Mortem

Adversarial risk classification. Given what investigation has established as fact, ask: "If this ships and fails, why?"

## Why

Investigation tells you what is true. Pre-mortem asks what could go wrong given those truths. Without investigation, pre-mortem degrades into speculation ("what if the API is down?"). With investigation, pre-mortem becomes precise ("the API returns paginated results but our code reads only page 1 — `catalog.py:87`").

The failure this skill prevents: the agent investigates thoroughly, confirms the data shapes are correct, and then implements a solution that fails for a reason nobody asked about as a separate, adversarial pass.

## Framework: Tiger / Paper Tiger / Elephant

### Tiger (real risk, unmitigated)

A failure scenario that:
- Is grounded in investigated facts (must cite Fact Sheet with file:line)
- Has a plausible trigger (can name the condition, not hypothetical)
- Is not currently mitigated by existing code, tests, or infrastructure

Tigers require mitigation before implementation proceeds, or an explicit accept-risk decision documented in the ticket.

**Urgency tiers:**

| Tier | Definition | Action |
|---|---|---|
| Launch-Blocking | Failure would corrupt data, break existing functionality, or violate a documented contract | Implementation halts until mitigated |
| Fast-Follow | Failure would degrade quality or miss edge cases but not break existing behavior | Implementation proceeds; fix is the next task |
| Track | Failure is possible under unusual conditions; monitoring or future hardening addresses it | Logged in ticket; no immediate action |

### Paper Tiger (feels scary, actually handled)

A failure scenario that:
- Sounds concerning on first pass
- Is already mitigated by existing code, tests, or infrastructure
- Investigation evidence shows why it's handled

Paper Tigers are documented to prevent future reviewers from re-raising the same concern. Each must cite the mitigation with file:line evidence.

### Elephant (uncomfortable truth, avoided)

A failure scenario or design flaw that:
- Everyone can see but nobody wants to name
- Often involves scope, timeline, or architectural debt
- Doesn't have a clean fix within the current task

Solo-agent discipline: if you notice yourself thinking "that's out of scope" or "we'll handle that later" — write it down as a candidate Elephant before dismissing it.

Elephants don't block implementation, but they must be documented in the ticket with a rationale for deferral.

## The pre-mortem process

### Step 1: Assemble the evidence base

Read the Investigation Fact Sheet. Non-negotiable — the pre-mortem operates on investigated facts, not on the agent's mental model.

Inputs required:
- Investigation Fact Sheet (with impact chain, verified shapes, logic trace)
- Think design note (approach selection)
- Ticket (goal, hypothesis, falsification criteria)

### Step 2: Failure brainstorm

For each node in the impact chain (upstream, this task, downstream), ask:

- **What input could arrive that the code doesn't handle?** (Empty, null, wrong type, unexpected shape, too large, concurrent, stale)
- **What assumption could be wrong?** (Cross-reference the Fact Sheet's "Assumptions my task makes" for each entity)
- **What could change between investigation and deployment?** (Schema migration, dependency update, config change, data migration)
- **What does the test suite NOT cover?** (Integration paths, error paths, edge cases named in the logic trace)
- **What would a user (or downstream system) experience if this fails?** (Silent corruption is worse than a loud error)

### Step 3: Classify each scenario

For each failure scenario identified:

1. **Name it** — one sentence describing the failure
2. **Ground it** — cite the Fact Sheet finding or entity that makes this plausible (file:line required for Tigers)
3. **Classify it** — Tiger, Paper Tiger, or Elephant
4. **For Tigers:** assign urgency tier and propose mitigation
5. **For Paper Tigers:** cite the existing mitigation (file:line required)
6. **For Elephants:** state why it's being deferred and what the deferral costs

### Step 4: Launch-Blocking gate

If any Tiger is classified Launch-Blocking:

- Implementation does not proceed.
- The mitigation must be designed (via think) and investigated before implementation resumes.
- The ticket is updated with the blocking finding.

This is a hard gate. "I'll handle it during implementation" is not acceptable for Launch-Blocking Tigers.

### Step 5: Update the ticket

The ticket receives:
- List of Tigers with urgency tiers and mitigations (or accept-risk decisions)
- List of Elephants with deferral rationale
- Paper Tigers are documented in the pre-mortem artifact but do not clutter the ticket

## Pre-Mortem artifact format

```
## Pre-Mortem
Task: <one-line description>
Ticket: <reference>
Fact Sheet: <path to investigation artifact>
Design note: <path to think artifact>

### Tigers

#### Tiger 1: <name>
- **Scenario:** <what happens>
- **Evidence:** <Fact Sheet citation with file:line>
- **Urgency:** Launch-Blocking | Fast-Follow | Track
- **Trigger condition:** <specific input or state that causes this>
- **Mitigation:** <what prevents or handles the failure>
- **Status:** Mitigated | Accept-Risk (with rationale) | Blocks-Launch

### Paper Tigers

#### Paper Tiger 1: <name>
- **Scenario:** <what it sounds like>
- **Why it's handled:** <existing mitigation with file:line>

### Elephants

#### Elephant 1: <name>
- **What it is:** <the uncomfortable truth>
- **Why it's deferred:** <rationale>
- **Cost of deferral:** <what gets worse while this is unaddressed>
- **Trigger for revisiting:** <when this should be re-evaluated>

### Launch-Blocking Assessment
- [ ] No Launch-Blocking Tigers remain unmitigated
- [ ] All Tiger mitigations are grounded in investigated facts
- [ ] Elephants have deferral rationale and revisit triggers
- Implementation may proceed: YES | NO (blocked by Tiger <N>)
```

## Solo-agent adaptation

The original Tiger/Paper Tiger/Elephant framework is designed for team brainstorming. In solo-agent execution:

- **There is no room full of perspectives.** Adopt adversarial stance deliberately. The prompt: "If I were reviewing someone else's plan and looking for reasons it would fail, what would I find?"
- **The agent's blind spots are systematic.** The SU#632-636 audit shows the agent consistently assumes data shapes match its mental model. Specifically stress-test data shape assumptions against the Fact Sheet.
- **Confirmation bias is the default.** The agent wants to confirm its approach works. The pre-mortem's job is to find evidence it won't.
- **Time pressure tempts shortcuts.** A 5-minute pre-mortem that catches a Launch-Blocking Tiger saves hours of debugging. A skipped pre-mortem that misses a Tiger costs the user's trust.

## Composition with other skills

- **investigate** produces the evidence base. Pre-mortem consumes it. A pre-mortem without a Fact Sheet is speculation.
- **think** produces the approach. Pre-mortem stress-tests it.
- **self-review** references the pre-mortem. The Lead checks: were the Tigers actually mitigated in the implementation?
- **post-mortem** traces failures back to the pre-mortem. Was this failure a Tiger that was missed? A Paper Tiger that was misclassified? An Elephant that finally charged?

## Hard rules

1. **No Tigers without evidence.** Every Tiger must cite the Fact Sheet with file:line. "The API might be slow" is not a Tiger — it's anxiety. "The API returns paginated results but `fetch_all()` at `catalog.py:87` reads only the first page" is a Tiger.
2. **Launch-Blocking means blocking.** Do not implement around a Launch-Blocking Tiger. Mitigate it first.
3. **Paper Tigers earn their name.** Don't classify something as Paper Tiger to avoid dealing with it. The mitigation must be real and cited.
4. **Elephants are named, not hidden.** The agent's natural tendency is to scope-exclude uncomfortable truths. Deferral is acceptable; invisibility is not.
5. **Pre-mortem runs after investigation.** Not before, not in parallel, not "I'll investigate as I go." The evidence base must exist before the adversarial pass begins.
6. **The ticket gets the Tigers.** Tigers and Elephants are documented in the ticket. The pre-mortem artifact is the detailed record; the ticket is the durable summary.
7. **Artifact destination is the ticket.** Post the pre-mortem artifact (or a structured summary with Tigers, Paper Tigers, and Elephants) as a comment on the ticket before implementation begins. The session plans folder is a working copy, not the canonical home. If the artifact is too long for a comment, commit it to the repo and link from the ticket.
