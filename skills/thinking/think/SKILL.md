---
name: think
description: "MANDATORY design-first gate. Enforces structured design before any code is written for a feature, refactor, or architecture change. Slash-invokable as /think; also enforced via the resolver before any non-trivial implementation. Do NOT skip this skill."
disable-model-invocation: true
allowed-tools: Read Grep Glob
---

# Think First

Do NOT write any code, scaffold any project, create any files, or take any implementation action until you have completed the design workflow below and the user has approved the design.

This is not a suggestion. It is a hard gate.

## Why

Code written without a design is a draft disguised as a solution. It commits you to an approach before you've considered alternatives, understood constraints, or identified risks. The cost of designing first is minutes. The cost of redesigning after implementation is hours or days.

## Design Workflow

### Step 0: Verify the ticket is fit

Before producing the design note, verify the ticket the work cites is structurally fit for execution:

```bash
bash <scripts>/discipline/evaluate-ticket.sh <ticket-ref>
```

(Path: `scripts/discipline/evaluate-ticket.sh` in the `claude-configs-public` repo; the skill that documents the rubric is `evaluate-ticket/SKILL.md`.)

**PASS** → proceed to Step 1.

**BLOCK** → two acceptable responses:

1. **Fix the ticket** to address the listed gaps. This is the default. Edit the ticket body to add the missing sections (Context / Goal / Acceptance / Assumptions / `/think` link / falsification for behavior-change tickets) and re-run `evaluate-ticket`.
2. **Paste an exemption block** in your eventual self-review artifact per `_writing-rules-rules.md` writing-rules:4. The exemption requires Reason / Evidence / Falsification fields; the self-review hook validates via `scripts/discipline/check-trivial-claim.sh`.

"Just ignore the BLOCK" is not acceptable. The self-review hook re-runs `evaluate-ticket` against the cited Goal source and refuses the push if it BLOCKs and no exemption block is present.

**Trivial-change exception:** if the work is genuinely too small to warrant a full ticket (typo fix, doc-only edit, single-character revert), you may skip Step 0 by including a `## Trivial-change declaration` block in your self-review artifact per the format in `self-review/SKILL.md`. The declaration itself requires evidence; "this is trivial" without a falsifiable basis is not an acceptable declaration.

### Step 1: Context

Understand what exists and what's changing.

- What code, systems, or data are involved?
- What works today that must keep working?
- What prompted this change? (Bug, feature request, tech debt, new requirement)
- What is the scope boundary? (What is explicitly NOT part of this work)

Read the relevant files. Don't guess about the current state.

#### Sibling-grep gate (mandatory when designing a fix)

When the task is designing a fix — not designing a new feature — Step 1 MUST include a sibling-grep before any proposal in Step 3. Grep the codebase for siblings of the symptom we're fixing, using at least the following queries:

- **Same import path:** grep for other call sites of the failing function / class / module.
- **Same decorator or fixture:** grep for the decorator (`@dp.materialized_view`, `@retry`, `@cached_property`) across the repo; list every site.
- **Same filter / call shape:** grep for the syntactic pattern that bracketed the failure (`filter(...).partition_cols=(...)`, `except SpecificClass:`, `if config.get('x')`).
- **Same failure signature:** if the failure has a known exception class or error string, grep for other handlers that catch the same shape.

Paste the sibling-set in Step 1's Context block. If the sibling-set is N≥2, the bug is a class — design the fix at the class level, not per-instance. Per writing-rules:7, N≥3 in one session is a hard gate: produce the audit matrix or revert to investigation.

Bug class is the unit; per-instance design is fragile. The Spark Connect guard sequence that motivated this gate had five same-shape PRs over hours because nobody grep'd for siblings before designing the second fix. One PR with an audit matrix would have replaced all five.

### Step 2: Questions

Identify what's unclear or ambiguous before proposing anything.

- What decisions haven't been made yet?
- What information is missing?
- What assumptions are you making? State them explicitly.
- Are there stakeholders or downstream systems affected?

If you have questions for the user, ask them now. Do not proceed with unresolved ambiguity.

### Step 3: Proposals

Present 2-3 approaches with tradeoffs. Not 1 (no comparison). Not 5 (decision paralysis).

For each approach:
- **What:** One-sentence summary
- **How:** Key implementation steps (not code — describe the approach)
- **Tradeoffs:** What you gain and what you give up
- **Risk:** What could go wrong

Format as a comparison table when the approaches share common dimensions.

### Step 4: Design

After the user selects an approach (or you recommend one with justification), write the design:

- **Architecture:** How the pieces fit together. Diagrams if helpful.
- **Interface:** What goes in, what comes out. Function signatures, API contracts, data shapes.
- **Data flow:** How data moves through the system. Where it is read, transformed, written.
- **Edge cases:** What happens with empty input, null values, concurrent access, partial failure.
- **Dependencies:** What this change depends on. What depends on this change.

The design should be detailed enough that someone else could implement it without asking you questions.

### Step 5: Documentation Plan

Before writing code, decide what documentation will need updating:

- Which files need docstring/comment updates?
- Does the README or CLAUDE.md need changes?
- Are there tickets to create or update?
- Will this affect downstream documentation (API docs, wiki, knowledge base)?

This prevents the common failure mode of "we'll document it later" (which means never).

### Step 6: Implementation Gate

Present the design to the user. Wait for explicit approval before writing any code.

**Acceptable signals to proceed:**
- "Looks good, go ahead"
- "Approved"
- "Let's do option 2"
- Any clear affirmative

**NOT acceptable signals:**
- Silence (do not assume approval)
- "Interesting" (that's not approval)
- "Maybe" (that's a question, not approval)

If the user suggests changes, revise the design and present again.

### Step 7: Downstream Routing (hard gate)

After user approval of the design, before implementation begins:

- [ ] **investigate:** Fact Sheet required? (YES for any entity-touching work)
- [ ] **pre-mortem:** Risk classification required? (YES for non-trivial work)
- [ ] **survey-context:** Entity doc consultation required? (YES if project has doc layer)

Investigation runs first. Pre-mortem runs after investigation completes. Implementation begins only after all required downstream skills have produced their artifacts.

**This is a hard gate, not a checklist.** Checking "YES" and proceeding
to code without producing the artifact is a self-review violation. The
`self-review` artifact's `Investigate-artifact:` and
`Pre-mortem-artifact:` fields (v1.3) enforce artifact existence at push
time. If you answer YES here but have no artifact to cite in
self-review, the push is blocked.

**Escape hatch:** If the work is genuinely trivial enough to skip
investigation (single-line fix, doc-only, config-only), answer NO and
include a `## Trivial-investigation declaration` in the self-review
artifact with falsifiable evidence for why investigation was unnecessary.

### Investigation Dependencies

The design note must include a section naming what `investigate` must verify before implementation can proceed:

```
### Investigation Dependencies
For each entity or assumption the design depends on:
- <Entity/assumption>: requires investigation verification of <what>
- If investigation falsifies: design must be revised (specifically: <which part>)
```

This makes the design's dependence on investigated facts explicit and traceable. If investigation finds something unexpected, the design note tells you which part of the design is affected.

## When This Skill Applies

This skill is **MANDATORY**. It auto-triggers whenever you are about to:
- Add a new feature or capability
- Refactor existing code
- Make architectural decisions
- Change data models or schemas
- Touch more than 3 files
- Do anything where the approach isn't obvious

You MUST complete the full design workflow and receive user approval before writing any code. Skipping this skill is not an option.

**Exemptions** (the ONLY cases where you may skip this skill):
- Single-line fixes (typos, obvious bugs with a clear one-line fix)
- Tasks where the user has given detailed, specific, step-by-step instructions
- Pure research or exploration (use the Explore agent instead)
- Git operations, documentation-only edits, and other non-code tasks

## Iron Laws

1. **No code before design.** Not even "just a quick prototype." Prototypes become production code.
2. **No implementation during design.** Reading code to understand the system is fine. Writing code is not.
3. **2-3 proposals, not 1.** If there's only one way to do it, you haven't thought hard enough. If there are more than 3, you're overthinking it.
4. **State your assumptions.** Every unstated assumption is a future bug.
5. **The user decides.** Present options with tradeoffs. Don't make the decision for them unless they ask you to.

## Artifact destination

The design note is a working document during the conversation, but the ticket is its durable home.

1. **Write the design note locally** (session plans folder or repo `plans/` directory) as a working copy.
2. **Post the design note to the ticket** as a comment before proceeding to investigation or implementation. The ticket comment is the canonical copy; the local file is the draft.
3. **If the design note is too long for a comment** (rare), commit it to the repo (e.g., `docs/design-notes/<ticket>.md`) and link from the ticket.
4. **If there is no ticket** (exploratory work), the local file is sufficient. Mark it `propagation-deferred: no ticket, exploratory` in frontmatter.

The next agent who touches this code must be able to find the design note from the ticket without re-deriving it. If the design note only exists in a session plans folder, it disappears when the session ends.

## Attribution Policy

NEVER include AI or agent attribution in designs, documentation, or any output.
