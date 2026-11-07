# Design procedure

Read this procedure before preparing a design. Return to [Think](SKILL.md) for applicability and authorization navigation. All required preparation remains applicable; the pre-edit tier table describes mechanical minima, not exemptions.

## Why

Code written without a design is a draft disguised as a solution. It commits you to an approach before you've considered alternatives, understood constraints, or identified risks. The cost of designing first is minutes. The cost of redesigning after implementation is hours or days.

## Accumulated Knowledge

The purpose of accumulating knowledge of facts and failures on a ticket is to provide a framework for what we know, what we've tried, what has failed and why it's failed, to produce better outcomes.

Every ticket accumulates knowledge over its lifetime: design notes, investigation findings, what was tried, what failed and why. This accumulated knowledge exists to be consumed. Your first act on any ticket is reading that history -- not re-deriving understanding from source code. The ticket is the briefing document. Code reading verifies the ticket's claims; it does not replace them.

This principle governs the entire workflow below. Steps that gather context (Step 1) start from accumulated knowledge. Steps that produce knowledge (Steps 7, 8) write for the next consumer. An agent that satisfies every structural gate while ignoring accumulated knowledge has defeated the purpose of the pipeline.

## Design Workflow

### Step 0: Verify the ticket is fit

Before producing the design note, verify the ticket the work cites is structurally fit for execution:

```bash
bash <scripts>/discipline/evaluate-ticket.sh <ticket-ref>
```

(Path: `scripts/discipline/evaluate-ticket.sh` in the `claude-configs-public` repo; the skill that documents the rubric is `evaluate-ticket/SKILL.md`.)

**PASS** then proceed to Step 1.

**If evaluate-ticket.sh is unavailable** (e.g., running outside claude-configs-public, in Craft Agent, or in a spawned session without access to the scripts/ directory): apply the rubric manually. The ticket must have: Context (what exists), Goal (what changes), Acceptance criteria (how to verify), and Assumptions (what you're taking on faith). If any are missing, fix the ticket or note the gap. Do not skip structural verification because the script isn't available.

**BLOCK** then two acceptable responses:

1. **Fix the ticket** to address the listed gaps. This is the default. Edit the ticket body to add the missing sections (Context / Goal / Acceptance / Assumptions / `/think` link / falsification for behavior-change tickets) and re-run `evaluate-ticket`.
2. **Paste an exemption block** in your eventual self-review artifact per `_writing-rules-rules.md` writing-rules:4. The exemption requires Reason / Evidence / Falsification fields; the self-review hook validates via `scripts/discipline/check-trivial-claim.sh`.

"Just ignore the BLOCK" is not acceptable. The self-review hook re-runs `evaluate-ticket` against the cited Goal source and refuses the push if it BLOCKs and no exemption block is present.

**Trivial-change exception:** if the work is genuinely too small to warrant a full ticket (typo fix, doc-only edit, single-character revert), you may skip Step 0 by including a `## Trivial-change declaration` block in your self-review artifact per the format in `self-review/SKILL.md`. The declaration itself requires evidence; "this is trivial" without a falsifiable basis is not an acceptable declaration.

### Step 1: Context

Understand what exists and what's changing. Start from the ticket's accumulated knowledge, not from code.

- **Read the ticket first** -- the body is the specification (context, goal, acceptance criteria). The comments are the accumulated knowledge (design notes, investigation findings, what was tried, what failed and why). Read both before reading any code. The ticket is the briefing document; code reading verifies the ticket's claims, it does not replace them.
- What code, systems, or data are involved?
- What works today that must keep working?
- What prompted this change? (Bug, feature request, tech debt, new requirement)
- What is the scope boundary? (What is NOT part of this work)
- **Public API blast radius:** does this change a return type, add/remove a parameter, or change the contract of a public function? If yes, score the blast radius (see below) and note who calls it and what breaks.

#### Blast radius scoring

For every entity the design modifies (function, class, module, config
key, schema), run `grep -rn <entity-name>` across the codebase and
count distinct call sites. The call-site count drives the tier:

| Tier | Call sites | Definition |
|---|---|---|
| CRITICAL | 5+ | Wide fan-out: breakage propagates across multiple modules or repos |
| HIGH | 3-4 | Cross-module impact: callers in more than one package or layer |
| MEDIUM | 1-2 | Single-module impact: internal callers only |
| LOW | 0 | Isolated change: no external callers affected |

Record the blast radius in the design note:

```
### Blast radius
- <entity>: <TIER> (<N> call sites: <brief list>)
```

The tier informs proposal selection in Step 3: a CRITICAL entity
favors backward-compatible approaches (add new function, deprecate
old) over breaking changes. A LOW entity permits aggressive
refactoring.

Read the relevant files. Don't guess about the current state.

#### Ticket-vs-target reality check (mandatory)

Before designing a solution, verify that the ticket's description of the current state matches what's actually on **the PR target branch** (usually `develop`), not your current feature branch. Run `git fetch origin develop` (or whatever the target is) and check against `origin/develop`, not local HEAD.

Why the target branch, not your current branch: your feature branch may be days or weeks behind. PRs that landed since you branched change the code the ticket describes. A Fact Sheet built against a stale feature branch produces confidently wrong findings -- and if you post that to the ticket (per the post-to-ticket gate), you've published misinformation. This happened in dogfood session 260528-proud-birch: the agent verified claims against its stale branch, concluded the ticket was wrong, posted that conclusion, and only discovered the ticket was right when it fetched develop to create a new branch.

For each factual claim the ticket makes about the current code (e.g., "function X returns None," "class Y doesn't exist," "PR #NNN added a try/except wrapper"):
- Grep or read the actual code on `origin/<target-branch>` (e.g., `git show origin/develop:path/to/file.py`)
- If the claim matches: note "verified against origin/develop at <commit>" and move on
- If the claim doesn't match: STOP. Note the discrepancy in Step 2 (Questions). The design must be based on what the target branch actually looks like, not what the ticket says OR what your stale local branch says.

A design based on a stale branch is a design based on fiction. This check takes 30 seconds and prevents hours of rework -- or worse, a wrong Fact Sheet posted to the ticket.

#### Sibling-grep gate (mandatory when designing a fix)

When the task is designing a fix -- not designing a new feature -- Step 1 MUST include a sibling-grep before any proposal in Step 3. Grep the codebase for siblings of the symptom we're fixing, using at least the following queries:

- **Same import path:** grep for other call sites of the failing function / class / module.
- **Same decorator or fixture:** grep for the decorator (`@dp.materialized_view`, `@retry`, `@cached_property`) across the repo; list every site.
- **Same filter / call shape:** grep for the syntactic pattern that bracketed the failure (`filter(...).partition_cols=(...)`, `except SpecificClass:`, `if config.get('x')`).
- **Same failure signature:** if the failure has a known exception class or error string, grep for other handlers that catch the same shape.

Paste the sibling-set in Step 1's Context block. If the sibling-set is N≥2, the bug is a class -- design the fix at the class level, not per-instance. Per writing-rules:7, N≥3 in one session is a hard gate: produce the audit matrix or revert to investigation.

Bug class is the unit; per-instance design is fragile. The Spark Connect guard sequence that motivated this gate had five same-shape PRs over hours because nobody grep'd for siblings before designing the second fix. One PR with an audit matrix would have replaced all five.

### Step 2: Questions

Identify what's unclear or ambiguous before proposing anything.

- What decisions haven't been made yet?
- What information is missing?
- What assumptions are you making? State them.
- Are there stakeholders or downstream systems affected?

Resolve factual and routine-method uncertainty from context and available evidence. Ask the responsible owner for materially unresolved scope, authority or consequences; hold only dependent implementation while independent authorized work continues.

### Step 3: Proposals

Compare viable approaches and record the chosen approach with its tradeoffs. If constraints or established precedent make one method clearly suitable, state why and proceed within authority rather than inventing alternatives. When a material owner decision remains, present a small set of real options with a recommendation.

**Precedent exception:** If a prior ticket in the same repo established a pattern for this exact class of fix (e.g., "ticket #801 already introduced `GeocodingError` for this shape of SU-1 violation"), you may present 1 proposal that follows the precedent plus a brief note explaining why alternatives would diverge from the established pattern. The point of multiple proposals is to ensure you've considered the space -- when the space has already been explored and a convention chosen, re-exploring it is ceremony.

For each approach:
- **What:** One-sentence summary
- **How:** Key implementation steps (not code -- describe the approach)
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

If the design changes documented behavior, the documentation update is part of the deliverable -- not a follow-up. "We'll document it later" means never.

For each of these, state what changes and where the update goes:

- **Docstrings and comments:** which functions or classes have docstrings that describe the behavior you're changing?
- **README or CLAUDE.md:** does the project's top-level documentation describe the feature or convention you're modifying?
- **Notebooks:** does any notebook demonstrate the function or workflow you're changing? (See the notebook coverage invariant in CLAUDE.md for siege_utilities.)
- **Tickets:** which tickets need updating with the new design, findings, or status?
- **External docs:** API docs, wiki pages, knowledge base articles, guide.md files -- anything outside the repo that describes the behavior.

These are the **designated knowledge loci** for the entities this task touches. Investigation Phase 0 identifies them in the Fact Sheet's "Knowledge Loci" section. If investigation found loci that describe behavior this task will change, updating those loci is a required deliverable -- not a follow-up. A PR that changes behavior without updating the knowledge loci that describe it ships a lie.

### Step 5b: Mission Alignment (required when PROJECT.md has a ## Mission section)

If the project's `PROJECT.md` has a `## Mission` section, the design note must include a `## Mission alignment` section that connects this work to the project's stated purpose. This section is enforced by the self-review hook via the `Project-contribution:` field.

Include:
1. **Mission quote**: the project mission from PROJECT.md (one sentence)
2. **Project-level outcome**: what this ticket produces beyond itself (not "completed the ticket" or restating the ticket title)
3. **Falsifiable claim**: a claim the think-gate can verify that proves this work advances the mission

```
## Mission alignment

Mission: "<quote from PROJECT.md ## Mission>"

Project-level outcome: <concrete deliverable proving advancement>

Falsifiable claim: <what would prove this work doesn't serve the mission>
```

If the project has no `## Mission` section in PROJECT.md, skip this step.

### Step 6: Implementation Gate

Record the design, the existing instruction or standing approval that covers its outcome, and any unresolved owner decisions. Use the task, prior decisions and available evidence to choose routine methods within your role. If the design stays within that authority and all required prerequisites are satisfied, continue without requesting the same authorization again.

Present a concrete decision to the responsible owner when the design changes the authorized outcome, introduces an unapproved material tradeoff or consequence, or requires a sign-off reserved by the owner. Hold only the dependent implementation and continue independent authorized preparation. A task instruction does not release an explicit design hold or waive a project-specific approval requirement.

For a genuinely missing approval, use a clear affirmative instruction tied to the proposed scope. Silence, interest, a vague acknowledgment or your own suggested default cannot supply it. If the user changes the requirements, revise the design and recheck only the affected authorization and readiness conditions.

### Step 7: Post to ticket and continue (hard gate)

If this work has a ticket, post the design note to the ticket NOW. Use `gh issue comment <number> --body "..."` or equivalent. The session copy is a working draft; the ticket comment is the canonical copy. Do not proceed to Step 8 until the design note is on the ticket.

Knowledge you produce here will be consumed by the next agent working this ticket. Write for that reader. The test: would a technical worker reading this quickly understand what you are describing and find it useful, or would they call it muddy prose overlaying nothing of substance? A design note that only records the decision without recording the reasoning is half a design note.

If no ticket exists (exempt per pre-action check 5), skip the post.

**Then continue autonomously to Step 8.** Do not wait for parent approval, operator acknowledgement, or external signal to proceed. The pipeline is self-driving: each gate produces an artifact, posts it, and advances to the next gate. Stopping between gates to ask "should I continue?" defeats the purpose of having a pipeline -- it turns autonomous execution into supervised step-by-step work.

### Step 8: Downstream Routing (hard gate)

After design authorization and any required sign-off are verified, before implementation begins:

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

## Artifact destination

**If the work has a ticket, the design note goes on the ticket. This is not optional.**

Post the design note as a comment on the ticket before proceeding to investigation or implementation. The local file (session plans folder or repo `plans/` directory) is a working draft. The ticket comment is the canonical copy. If the design note is too long for a comment, commit it to the repo and link from the ticket.

If there is no ticket (exploratory work only), mark the local file `propagation-deferred: no ticket, exploratory` in frontmatter.

The same rule applies to every artifact this skill produces: if a ticket exists, the artifact goes there. A design note that only exists in a session plans folder is a design note that doesn't exist -- it disappears when the session ends, and the next agent re-derives it from scratch.
