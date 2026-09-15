---
name: pre-mortem
description: "Adversarial risk gate between investigation and implementation. Classifies failure scenarios as Tiger (real and unmitigated), Paper Tiger (feels scary but investigation shows it's handled), or Elephant (uncomfortable truth everyone avoids). Tigers must be grounded in investigated facts with file:line citations. Launch-Blocking Tigers halt implementation until mitigated. Runs after investigate, before implementation."
user-invocable: true
allowed-tools: Read Grep Glob
---

# Pre-Mortem

Adversarial risk classification. Given what investigation has established as fact, ask: "If this ships and fails, why?"

## Why

Investigation tells you what is true. Pre-mortem asks what could go wrong given those truths. Without investigation, pre-mortem degrades into speculation ("what if the API is down?"). With investigation, pre-mortem becomes precise ("the API returns paginated results but our code reads only page 1 -- `catalog.py:87`").

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

Solo-agent discipline: if you notice yourself thinking "that's out of scope" or "we'll handle that later" -- write it down as a candidate Elephant before dismissing it.

Elephants don't block implementation, but they must be documented in the ticket with a rationale for deferral.

## The pre-mortem process

### Step 1: Assemble the evidence base

Read the Investigation Fact Sheet. Non-negotiable -- the pre-mortem operates on investigated facts, not on the agent's mental model.

Inputs required:
- Investigation Fact Sheet (with impact chain, verified shapes, logic trace)
- Think design note (approach selection)
- Ticket (goal, hypothesis, falsification criteria)

### Step 1b: Fact Sheet correction check

If the Fact Sheet was revised during investigation (e.g., stale branch data corrected, entity discovered to exist when initially reported absent), verify that the design note from think is still valid against the corrected facts. For each correction in the Fact Sheet:

- Does the design depend on the assumption that was corrected?
- If yes: the design must be re-derived before pre-mortem can proceed. A pre-mortem that stress-tests an invalidated design is wasted work.
- If no: note "design unaffected by correction" and proceed.

This is not a soft check. The dogfood incident that motivated this rule: the agent corrected its Fact Sheet (entity existed on develop, not absent as initially claimed) but proceeded with pre-mortem against the original design that assumed the entity was absent. The pre-mortem found no Tigers because it was stress-testing a plan built on falsified premises.

### Step 2: Failure brainstorm

For each node in the impact chain (upstream, this task, downstream), ask:

- **What input could arrive that the code doesn't handle?** (Empty, null, wrong type, unexpected shape, too large, concurrent, stale)
- **What assumption could be wrong?** (Cross-reference the Fact Sheet's "Assumptions my task makes" for each entity)
- **What could change between investigation and deployment?** (Schema migration, dependency update, config change, data migration)
- **What does the test suite NOT cover?** (Integration paths, error paths, edge cases named in the logic trace)
- **What would a user (or downstream system) experience if this fails?** (Silent corruption is worse than a loud error)
- **Does the test mock the layer being changed?** (A test that mocks the function you're modifying will pass regardless of your change -- it's testing the mock, not the code. See the "Test-fragility" named Tiger pattern below.)

### Step 3: Classify each scenario

For each failure scenario identified:

1. **Name it** -- one sentence describing the failure
2. **Ground it** -- cite the Fact Sheet finding or entity that makes this plausible (file:line required for Tigers)
3. **Coherence check** -- does the scenario logically follow from the cited evidence? A Tiger that cites "field X at file:line" but whose trigger scenario assumes a different field, type, or behavior is internally incoherent -- the scenario is not grounded in the evidence it claims. Resolve the contradiction: either the scenario is wrong (reclassify or discard) or the citation is wrong (find the real evidence). Do not classify an incoherent scenario.
4. **Classify it** -- Tiger, Paper Tiger, or Elephant
5. **For Tigers:** assign urgency tier and propose mitigation
6. **For Paper Tigers:** cite the existing mitigation (file:line required)
7. **For Elephants:** state why it's being deferred and what the deferral costs

### Named Tiger patterns

These are recurring failure shapes identified through dogfooding. Check for each explicitly during the brainstorm.

#### Test-fragility Tiger (wrong mock layer)

**Pattern:** The implementation changes function F, but the existing test for F mocks F itself (or mocks the layer F calls in a way that bypasses the changed code path). The test passes before and after the change -- it's testing the mock, not the behavior.

**How to detect:** The Fact Sheet's "Tests as verified shapes" section (investigate Phase 2) records what each test mocks. If a test mocks at or above the layer being changed, flag it.

**Classification:** Fast-Follow Tiger. The implementation is correct, but the test suite provides false confidence. Mitigation: write or fix the test to exercise the actual code path, not the mock.

**Grounding incident:** Dogfood session on #836 -- the agent wrote a test that mocked `_load_credential_backends()`, the exact function the fix modified. The test asserted the new error was raised, but the assertion was against the mock's behavior, not the real credential-loading logic. A regression in the real function would pass the test.

### Tiger severity scoring

For each Tiger, score severity across five dimensions (0-100 each)
to produce a composite priority that is more informative than the
binary urgency tier alone. The urgency tier (Launch-Blocking /
Fast-Follow / Track) remains as the action label; the composite
score provides the quantitative backing for the tier assignment.

| Dimension | Weight | What it measures |
|---|---|---|
| Data integrity | 25% | Risk of data corruption, loss, or silent wrong answers |
| User impact scope | 25% | How many users, workflows, or downstream systems are affected |
| Reversibility | 20% | How hard to undo if the Tiger materializes (rollback difficulty) |
| Dependency chain | 15% | Number of downstream systems that would propagate the failure |
| Detection latency | 15% | Time between failure and discovery (silent = high, loud error = low) |

**Composite score** = weighted sum of dimension scores.

| Score | Priority tier | Maps to urgency |
|---|---|---|
| 80-100 | Emergency-stop | Launch-Blocking |
| 60-79 | Mitigate-before-ship | Launch-Blocking or Fast-Follow |
| 40-59 | Monitor-after-ship | Fast-Follow or Track |
| 0-39 | Accept-and-document | Track |

**Scoring a Tiger (worked example):**

> **Tiger: API returns paginated results but fetch_all() reads only page 1**
>
> | Dimension | Score | Rationale |
> |---|---|---|
> | Data integrity | 80 | Silent data truncation — callers get partial results |
> | User impact scope | 70 | Every caller of fetch_all() affected |
> | Reversibility | 30 | Fix is a code change, no data migration needed |
> | Dependency chain | 60 | 3 downstream modules call fetch_all() |
> | Detection latency | 90 | Silent — no error, just fewer rows |
>
> Composite = (80×.25) + (70×.25) + (30×.20) + (60×.15) + (90×.15)
>           = 20 + 17.5 + 6 + 9 + 13.5 = **66** → Mitigate-before-ship

Use the composite score to justify the urgency tier. A Tiger that
"feels" Launch-Blocking but scores 45 should be re-examined — either
the scoring missed a dimension or the gut feeling is wrong. A Tiger
that "feels" minor but scores 75 should be escalated.

The scoring dimensions can be overridden per project in PROJECT.md
(different weights for data-heavy vs. UI-heavy projects). The
defaults above apply when no project override exists.

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
Fact Sheet: <ticket-comment-link | committed-file-path | plans/investigate-*.md>
Design note: <ticket-comment-link | committed-file-path | plans/think-*.md>

### Tigers

#### Tiger 1: <name>
- **Scenario:** <what happens>
- **Evidence:** <Fact Sheet citation with file:line>
- **Severity:** <composite score> (<priority tier>)
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
- **Time pressure tempts shortcuts.** The Junior optimizes for speed of one task -- it wants to skip the pre-mortem because "I already know what to build." The Lead optimizes for speed of the project -- it knows a 5-minute pre-mortem that catches a Launch-Blocking Tiger saves the human hours of debugging rework. The agent's seconds are cheap; the human's hours are not.

## Post to ticket and continue (hard gate)

When the pre-mortem artifact is complete, post it to the ticket NOW. Use `gh issue comment <number> --body "..."` or equivalent. The session copy is a working draft; the ticket comment is the canonical copy.

Do not proceed to implementation until the pre-mortem is on the ticket.

**Then continue autonomously to implementation.** Do not wait for parent approval or operator acknowledgement. The pipeline is self-driving: produce the artifact, post it, advance. If a Tiger is Launch-Blocking, mitigate it as part of implementation -- that's what the pre-mortem is for.

## Composition with other skills

- **investigate** produces the evidence base. Pre-mortem consumes it. A pre-mortem without a Fact Sheet is speculation.
- **think** produces the approach. Pre-mortem stress-tests it.
- **self-review** references the pre-mortem. The Lead checks: were the Tigers actually mitigated in the implementation?
- **post-mortem** traces failures back to the pre-mortem. Was this failure a Tiger that was missed? A Paper Tiger that was misclassified? An Elephant that finally charged?

## Hard rules

1. **No Tigers without evidence.** Every Tiger must cite the Fact Sheet with file:line. "The API might be slow" is not a Tiger -- it's anxiety. "The API returns paginated results but `fetch_all()` at `catalog.py:87` reads only the first page" is a Tiger.
2. **Launch-Blocking means blocking.** Do not implement around a Launch-Blocking Tiger. Mitigate it first.
3. **Paper Tigers earn their name.** Don't classify something as Paper Tiger to avoid dealing with it. The mitigation must be real and cited.
4. **Elephants are named, not hidden.** The agent's natural tendency is to scope-exclude uncomfortable truths. Deferral is acceptable; invisibility is not.
5. **Pre-mortem runs after investigation.** Not before, not in parallel, not "I'll investigate as I go." The evidence base must exist before the adversarial pass begins.
6. **The ticket gets the Tigers.** Tigers and Elephants are documented in the ticket. The pre-mortem artifact is the detailed record; the ticket is the durable summary.
7. **If the work has a ticket, the pre-mortem goes on the ticket. This is not optional.** Post the pre-mortem artifact (or a structured summary with Tigers, Paper Tigers, and Elephants) as a comment on the ticket before implementation begins. The session plans folder is a working draft, not the canonical home. If the artifact is too long for a comment, commit it to the repo and link from the ticket. A pre-mortem that only exists in a session plans folder is a pre-mortem that doesn't exist.
