---
name: post-mortem
description: "Blameless learning from confirmed failures. Triggered when a shipped implementation contradicts its ticket hypothesis or a pre-mortem Tiger materializes. Produces a root cause analysis with contributing factors, timeline, and action items with testable acceptance criteria. Traces backward through the skill pipeline (self-review → pre-mortem → investigation → think) to identify where the failure could have been caught. Action items update skills, not just code."
disable-model-invocation: true
user-invocable: true
allowed-tools: Read Grep Glob Bash
---

# Post-Mortem

Blameless learning from confirmed failures. Examines not just what went wrong in the code, but what went wrong in the process that let the bad code ship.

## Why

Bugs get fixed. The conditions that produced them often don't. A post-mortem examines systemic conditions (missing gates, insufficient evidence requirements, skill gaps) rather than "I should have been more careful." "Be more careful" is not an action item — it's a wish.

The Allspaw test: "Would I send this post-mortem to the engineer who pushed the button, and would they find it fair, accurate, and useful?" In solo-agent context: would the operator read this and understand what systemic change prevents recurrence?

## When to trigger

Required when:

- A shipped implementation contradicts its ticket hypothesis.
- A pre-mortem Tiger materializes (the risk identified actually happened).
- A pre-mortem Paper Tiger turns out to be a real Tiger (the cited mitigation didn't work).
- An Elephant charges (the deferred issue becomes urgent).
- The self-review missed a finding that a downstream reviewer or user caught.
- A test failure reveals a shipped bug in code that passed self-review.

NOT required for:

- Bugs caught during development (before push) — normal iteration.
- Test failures in code that hasn't been self-reviewed yet — fix and move on.
- External changes that break existing code (dependency update, API change) — those are incidents, not post-mortems.

## The post-mortem process

### Phase 1: Timeline reconstruction

Before analysis, establish what actually happened:

```
## Timeline
- <timestamp>: Ticket created with goal: <goal>
- <timestamp>: Think design note produced (or: think was SKIPPED)
- <timestamp>: Investigation Fact Sheet produced (or: investigation was SKIPPED)
- <timestamp>: Pre-mortem completed (or: pre-mortem was SKIPPED)
- <timestamp>: Implementation began
- <timestamp>: Self-review artifact produced
- <timestamp>: Code pushed / PR created
- <timestamp>: Failure discovered by <who/what>
- <timestamp>: Post-mortem triggered
```

Skipped steps are the most important entries. They are not neutral — they are contributing factors.

### Phase 2: Root cause analysis

Use either **5 Whys** or **Causal Tree**, depending on the failure shape.

**5 Whys** — when the failure has a single causal chain:

1. Why did the bug ship? → (e.g., self-review didn't catch it)
2. Why didn't self-review catch it? → (e.g., the test verified the assumption, not reality)
3. Why did the test verify the assumption? → (e.g., no investigation was done)
4. Why was investigation skipped? → (e.g., batch execution treated it as overhead)
5. Why did batch execution skip investigation? → (e.g., standing instruction interpreted as permission to skip gates)

**Causal Tree** — when multiple independent factors contributed:

```
Failure: <description>
├── Contributing: <factor A>
│   ├── <sub-cause>
│   └── <sub-cause>
├── Contributing: <factor B>
│   └── <sub-cause>
└── Contributing: <factor C>
    └── <sub-cause>
```

### Phase 3: Skill pipeline trace-back

For each contributing factor, trace backward:

| Gate | Should have caught? | Did it run? | Why it missed (or was skipped) |
|---|---|---|---|
| think | Would Step 1 (Context) have surfaced this? | Yes/No/Skipped | <reason> |
| investigate | Would data shape verification have caught this? Were knowledge loci identified? | Yes/No/Skipped | <reason> |
| pre-mortem | Would this have been classified as a Tiger? | Yes/No/Skipped | <reason> |
| self-review | Did the Junior or Lead check this? Did Lead question 4 (knowledge loci updates) fire? | Yes/No | <reason> |
| post-error-revision | Were knowledge loci updated with the correction? | Yes/No/N/A | <reason> |
| survey-context | Would entity doc consultation have helped? | Yes/No/N/A | <reason> |

The trace-back identifies the earliest point where the failure could have been caught. That's where the systemic fix belongs. The trace-back also identifies whether the correction was routed to the designated knowledge loci — if it wasn't, a future agent will repeat the same false assumption.

### Phase 4: Action items

Each action item must have:

- **What:** Specific change (not "be more careful")
- **Where:** Which skill, gate, rule, or code to modify
- **Acceptance criteria:** Testable condition that proves the action was completed
- **Owner:** Who does this (operator or future task)
- **Type:** Skill update | Gate addition | Code fix | Test addition | Process change

**The Allspaw test for action items:**

- Bad: "Be more thorough when reviewing regex patterns" (wish)
- Good: "Add to investigation Phase 2: for any string normalization, verify character set of actual input data with a sample grep. Record the character set in the Fact Sheet." (specific, testable, located in a skill)

- Bad: "Remember to check non-ASCII input" (wish)
- Good: "Add `unicodedata.normalize('NFKD', text)` before ASCII filtering in `_normalize_name`. Add test case: 'Cañón' → 'canon'." (specific code fix with test)

### Phase 5: Verify action items close the class

For each action item, ask: "If this action had been in place when the work started, would it have prevented this specific failure AND the class of failures it represents?"

- "This specific failure but not the class" → too narrow. Widen it.
- "The class but I can't verify it would have caught this specific failure" → too abstract. Narrow it.

## Post-Mortem artifact format

```
## Post-Mortem
Failure: <one-sentence description>
Ticket: <reference>
Severity: HIGH | MEDIUM | LOW
Discovered by: <who/what found the failure>
Date: <when discovered>

### Timeline
<Phase 1 output>

### Root Cause Analysis
Method: 5 Whys | Causal Tree
<Phase 2 output>
Root cause: <one-sentence summary>

### Skill Pipeline Trace-Back
<Phase 3 table>
Earliest catch point: <which gate, with explanation>

### Contributing Factors
For each factor:
1. **<Factor>** — <description>
   - Type: Process | Technical | Environmental
   - Severity of contribution: Primary | Contributing | Contextual

### Action Items
For each action:
- [ ] **<What>**
  - Where: <skill/gate/code/test>
  - Type: Skill update | Gate addition | Code fix | Test addition | Process change
  - Acceptance criteria: <testable condition>
  - Closes the class: <yes/no — if no, what's the residual risk?>

### Codebase sweep

Pattern grep'd: `<exact bad string or regex>`
Scope: `<directories or repo root>`
Hits found:
  - <file>:<line> — <disposition: fixed in this PR / flagged separately as #NNN / annotated as stale / false positive>

If zero hits: state the grep command and "0 hits confirmed."
If hits exist: every hit must have a disposition. "Fixed in this PR" means the fix is in the same changeset. "Flagged separately" means a ticket number. No hit may be left undispositioned.

### What Went Well
<What worked correctly or limited the blast radius>

### Lessons
<1-3 sentences: what structural change prevents recurrence?>
```

## Composition with other skills

- **investigate** produces the facts the post-mortem evaluates against. "The Fact Sheet said X; reality turned out to be Y" is the core finding shape.
- **pre-mortem** is evaluated: was this failure a Tiger that was missed? A Paper Tiger misclassified?
- **think** is evaluated: did the approach selection consider this failure mode?
- **self-review** is evaluated: did the Junior or Lead catch this?
- **Skills themselves are the primary action target.** If a post-mortem's action items only fix code and add tests, it missed the systemic layer.
- **post-error-revision** handles the immediate correction (ticket Assumptions + knowledge loci). Post-mortem handles the systemic response (why was the wrong assumption possible, what gate failed). Both are required when a shipped failure contradicts a documented Assumption.
- **Knowledge loci** identified in the Fact Sheet must be checked during the post-mortem. If a locus (docstring, CLAUDE.md section, notebook) still describes the falsified behavior, updating it is an action item.

## Hard rules

1. **Blameless means systemic.** "I should have checked" is not a finding. "The investigation skill doesn't require character-set verification for string normalization" is a finding.
2. **Action items are testable.** Every action item has acceptance criteria. "Improve review quality" is not testable.
3. **The Allspaw test applies.** Would the operator find this fair, accurate, and useful?
4. **Post-mortems update skills, not just code.** The code fix is necessary but not sufficient.
5. **If the work has a ticket, the post-mortem goes on the ticket. This is not optional.** Post the post-mortem artifact (or a structured summary) as a comment on the ticket. If the artifact is too long for a comment, commit it to the repo and link from the ticket. A post-mortem that only exists in a session plans folder is a post-mortem that doesn't exist.
6. **Action items update knowledge loci, not just code.** If the Fact Sheet identified designated knowledge loci for the entities involved in the failure, and the post-mortem finds those loci describe the falsified behavior, updating them is an action item. The code fix alone is insufficient if the docstring, CLAUDE.md section, or notebook still describes the old (wrong) behavior.
7. **"What went well" is required.** Prevents the post-mortem from being purely punitive.
8. **Codebase sweep is required.** The post-mortem artifact is rejected if the `### Codebase sweep` section is missing or empty. The sweep grep must cover the entire scope where the bad pattern could recur, not just the file where the failure was discovered. A post-mortem that fixes one instance without grepping for siblings is incomplete — the next instance will produce the same post-mortem.
