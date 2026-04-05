---
name: think
description: "MANDATORY design-first gate. AUTO-TRIGGER: before implementing any feature, refactor, or architecture change. Enforces structured design before any code is written. Do NOT skip this skill."
allowed-tools: Read Grep Glob
---

# Think First

Do NOT write any code, scaffold any project, create any files, or take any implementation action until you have completed the design workflow below and the user has approved the design.

This is not a suggestion. It is a hard gate.

## Why

Code written without a design is a draft disguised as a solution. It commits you to an approach before you've considered alternatives, understood constraints, or identified risks. The cost of designing first is minutes. The cost of redesigning after implementation is hours or days.

## Design Workflow

### Step 1: Context

Understand what exists and what's changing.

- What code, systems, or data are involved?
- What works today that must keep working?
- What prompted this change? (Bug, feature request, tech debt, new requirement)
- What is the scope boundary? (What is explicitly NOT part of this work)

Read the relevant files. Don't guess about the current state.

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

## Attribution Policy

NEVER include AI or agent attribution in designs, documentation, or any output.
