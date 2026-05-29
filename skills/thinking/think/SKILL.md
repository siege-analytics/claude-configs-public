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

## Accumulated Knowledge

The purpose of accumulating knowledge of facts and failures on a ticket is to provide a framework for what we know, what we've tried, what has failed and why it's failed, to produce better outcomes.

Every ticket accumulates knowledge over its lifetime: design notes, investigation findings, what was tried, what failed and why. This accumulated knowledge exists to be consumed. Your first act on any ticket is reading that history — not re-deriving understanding from source code. The ticket is the briefing document. Code reading verifies the ticket's claims; it does not replace them.

This principle governs the entire workflow below. Steps that gather context (Step 1) start from accumulated knowledge. Steps that produce knowledge (Steps 7, 8) write for the next consumer. An agent that satisfies every structural gate while ignoring accumulated knowledge has defeated the purpose of the pipeline.

## Design Workflow

### Step 0: Verify the ticket is fit

Before producing the design note, verify the ticket the work cites is structurally fit for execution:

```bash
bash <scripts>/discipline/evaluate-ticket.sh <ticket-ref>
```

(Path: `scripts/discipline/evaluate-ticket.sh` in the `claude-configs-public` repo; the skill that documents the rubric is `evaluate-ticket/SKILL.md`.)

**PASS** → proceed to Step 1.

**If evaluate-ticket.sh is unavailable** (e.g., running outside claude-configs-public, in Craft Agent, or in a spawned session without access to the scripts/ directory): apply the rubric manually. The ticket must have: Context (what exists), Goal (what changes), Acceptance criteria (how to verify), and Assumptions (what you're taking on faith). If any are missing, fix the ticket or note the gap. Do not skip structural verification because the script isn't available.

**BLOCK** → two acceptable responses:

1. **Fix the ticket** to address the listed gaps. This is the default. Edit the ticket body to add the missing sections (Context / Goal / Acceptance / Assumptions / `/think` link / falsification for behavior-change tickets) and re-run `evaluate-ticket`.
2. **Paste an exemption block** in your eventual self-review artifact per `_writing-rules-rules.md` writing-rules:4. The exemption requires Reason / Evidence / Falsification fields; the self-review hook validates via `scripts/discipline/check-trivial-claim.sh`.

"Just ignore the BLOCK" is not acceptable. The self-review hook re-runs `evaluate-ticket` against the cited Goal source and refuses the push if it BLOCKs and no exemption block is present.

**Trivial-change exception:** if the work is genuinely too small to warrant a full ticket (typo fix, doc-only edit, single-character revert), you may skip Step 0 by including a `## Trivial-change declaration` block in your self-review artifact per the format in `self-review/SKILL.md`. The declaration itself requires evidence; "this is trivial" without a falsifiable basis is not an acceptable declaration.

### Step 1: Context

Understand what exists and what's changing. Start from the ticket's accumulated knowledge, not from code.

- **Read the ticket first** — the body is the specification (context, goal, acceptance criteria). The comments are the accumulated knowledge (design notes, investigation findings, what was tried, what failed and why). Read both before reading any code. The ticket is the briefing document; code reading verifies the ticket's claims, it does not replace them.
- What code, systems, or data are involved?
- What works today that must keep working?
- What prompted this change? (Bug, feature request, tech debt, new requirement)
- What is the scope boundary? (What is explicitly NOT part of this work)
- **Public API blast radius:** does this change a return type, add/remove a parameter, or change the contract of a public function? If yes, note who calls it and what breaks.

Read the relevant files. Don't guess about the current state.

#### Ticket-vs-target reality check (mandatory)

Before designing a solution, verify that the ticket's description of the current state matches what's actually on **the PR target branch** (usually `develop`), not your current feature branch. Run `git fetch origin develop` (or whatever the target is) and check against `origin/develop`, not local HEAD.

Why the target branch, not your current branch: your feature branch may be days or weeks behind. PRs that landed since you branched change the code the ticket describes. A Fact Sheet built against a stale feature branch produces confidently wrong findings — and if you post that to the ticket (per the post-to-ticket gate), you've published misinformation. This happened in dogfood session 260528-proud-birch: the agent verified claims against its stale branch, concluded the ticket was wrong, posted that conclusion, and only discovered the ticket was right when it fetched develop to create a new branch.

For each factual claim the ticket makes about the current code (e.g., "function X returns None," "class Y doesn't exist," "PR #NNN added a try/except wrapper"):
- Grep or read the actual code on `origin/<target-branch>` (e.g., `git show origin/develop:path/to/file.py`)
- If the claim matches: note "verified against origin/develop at <commit>" and move on
- If the claim doesn't match: STOP. Note the discrepancy in Step 2 (Questions). The design must be based on what the target branch actually looks like, not what the ticket says OR what your stale local branch says.

A design based on a stale branch is a design based on fiction. This check takes 30 seconds and prevents hours of rework — or worse, a wrong Fact Sheet posted to the ticket.

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

**Precedent exception:** If a prior ticket in the same repo established a pattern for this exact class of fix (e.g., "ticket #801 already introduced `GeocodingError` for this shape of SU-1 violation"), you may present 1 proposal that follows the precedent plus a brief note explaining why alternatives would diverge from the established pattern. The point of multiple proposals is to ensure you've considered the space — when the space has already been explored and a convention chosen, re-exploring it is ceremony.

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

If the design changes documented behavior, the documentation update is part of the deliverable — not a follow-up. "We'll document it later" means never.

For each of these, state what changes and where the update goes:

- **Docstrings and comments:** which functions or classes have docstrings that describe the behavior you're changing?
- **README or CLAUDE.md:** does the project's top-level documentation describe the feature or convention you're modifying?
- **Notebooks:** does any notebook demonstrate the function or workflow you're changing? (See the notebook coverage invariant in CLAUDE.md for siege_utilities.)
- **Tickets:** which tickets need updating with the new design, findings, or status?
- **External docs:** API docs, wiki pages, knowledge base articles, guide.md files — anything outside the repo that describes the behavior.

These are the **designated knowledge loci** for the entities this task touches. Investigation Phase 0 identifies them in the Fact Sheet's "Knowledge Loci" section. If investigation found loci that describe behavior this task will change, updating those loci is a required deliverable — not a follow-up. A PR that changes behavior without updating the knowledge loci that describe it ships a lie.

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

### Step 7: Post to ticket and continue (hard gate)

If this work has a ticket, post the design note to the ticket NOW. Use `gh issue comment <number> --body "..."` or equivalent. The session copy is a working draft; the ticket comment is the canonical copy. Do not proceed to Step 8 until the design note is on the ticket.

Knowledge you produce here will be consumed by the next agent working this ticket. Write for that reader. The test: would a technical worker reading this quickly understand what you are describing and find it useful, or would they call it muddy prose overlaying nothing of substance? A design note that only records the decision without recording the reasoning is half a design note.

If no ticket exists (exempt per pre-action check 5), skip the post.

**Then continue autonomously to Step 8.** Do not wait for parent approval, operator acknowledgement, or external signal to proceed. The pipeline is self-driving: each gate produces an artifact, posts it, and advances to the next gate. Stopping between gates to ask "should I continue?" defeats the purpose of having a pipeline — it turns autonomous execution into supervised step-by-step work.

### Step 8: Downstream Routing (hard gate)

After user approval of the design, before implementation begins:

- [ ] **investigate:** Fact Sheet required? (Default: **YES**. NO requires a Trivial-investigation declaration with falsifiable evidence in the self-review artifact.)
- [ ] **pre-mortem:** Risk classification required? (YES for non-trivial work)
- [ ] **survey-context:** Entity doc consultation required? (YES if project has doc layer)

Investigation is non-discretionary. It runs first. Pre-mortem runs after investigation completes. Implementation begins only after all required downstream skills have produced their artifacts and posted them to the designated knowledge locus (ticket, doc page, etc.).

Investigation and pre-mortem artifacts posted to tickets become part of the accumulated knowledge. They exist to be read and built upon by the next agent, not to satisfy a checkbox. Apply the same quality test: would a technical worker find this useful, or is it muddy prose overlaying nothing of substance?

**This is a hard gate, not a checklist.** Checking "YES" and proceeding
to code without producing the artifact is a self-review violation. The
`self-review` artifact's `Investigate-artifact:` and
`Pre-mortem-artifact:` fields (v1.3) enforce artifact existence at push
time. If you answer YES here but have no artifact to cite in
self-review, the push is blocked.

**Escape hatch (the ONLY acceptable NO):** If the work is genuinely trivial
enough to skip investigation (single-line fix, doc-only with no behavioral
change, single-line literal change), answer NO and include a
`## Trivial-investigation declaration` in the self-review artifact with
falsifiable evidence for why investigation was unnecessary. "This is
simple" is not falsifiable evidence.

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
- Git operations and other non-code tasks that do not change behavior

**Not exempt — highest-stakes edits that require the full pipeline:**
- Skill files (`skills/**/SKILL.md`) — these change the behavior of every future task
- Hook scripts (`hooks/**/*.sh`) — these change what the pipeline enforces
- Rule files (`_*-rules.md`) — these change the standards the pipeline evaluates against
- CLAUDE.md and project conventions — these change how agents interpret the codebase

"Documentation-only edit" does NOT include skill/hook/rule edits. Changing a skill is changing the pipeline's behavior — it requires think, investigate, and pre-mortem like any behavioral change. The recursive case (the pipeline editing itself) is the highest-stakes change because a broken skill silently degrades all future work.

## Iron Laws

1. **No code before design.** Not even "just a quick prototype." Prototypes become production code.
2. **No implementation during design.** Reading code to understand the system is fine. Writing code is not.
3. **2-3 proposals, not 1.** If there's only one way to do it, you haven't thought hard enough. If there are more than 3, you're overthinking it.
4. **State your assumptions.** Every unstated assumption is a future bug.
5. **The user decides.** Present options with tradeoffs. Don't make the decision for them unless they ask you to.

## Artifact destination

**If the work has a ticket, the design note goes on the ticket. This is not optional.**

Post the design note as a comment on the ticket before proceeding to investigation or implementation. The local file (session plans folder or repo `plans/` directory) is a working draft. The ticket comment is the canonical copy. If the design note is too long for a comment, commit it to the repo and link from the ticket.

If there is no ticket (exploratory work only), mark the local file `propagation-deferred: no ticket, exploratory` in frontmatter.

The same rule applies to every artifact this skill produces: if a ticket exists, the artifact goes there. A design note that only exists in a session plans folder is a design note that doesn't exist — it disappears when the session ends, and the next agent re-derives it from scratch.

## Attribution Policy

NEVER include AI or agent attribution in designs, documentation, or any output.
