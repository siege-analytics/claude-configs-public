---
name: investigate
description: "Non-discretionary evidentiary gate. Required before any artifact is created, modified, or deleted. Verify the ticket's claims against reality by reading actual code, schemas, and data shapes. Produces a Fact Sheet artifact with file:line citations, impact chain, knowledge loci, and environmental readiness. The Fact Sheet is the single source of truth referenced by design, self-review, and post-mortem. Do NOT skip this skill; assumptions that bypass investigation are the #1 cause of shipped bugs."
disable-model-invocation: true
user-invocable: true
allowed-tools: Read Grep Glob Bash
---

# Investigate

Evidentiary fact-finding. Before any artifact is created, modified, or deleted, verify the ticket's claims against reality by reading actual code, schemas, and data shapes. Produces a Fact Sheet artifact with file:line citations, knowledge loci, and an impact chain tracing upstream → task → downstream.

## Why

The recurring failure shape: the agent knows what it wants to build, skips straight to code, and discovers at review time (or never) that the entities it referenced don't have the shape it assumed. Investigation is the evidentiary counterpart to think's strategic framing. Think asks "what approach?" — investigate asks "what are the actual facts?"

Grounding incidents (SU#632-636 batch, N=5):

- `codification_summary.py` mapped `self.urbanicity.category_distribution` — the field is `distribution`, not `category_distribution`. Never read the dataclass.
- `precinct_vtd.py` used `[^a-z0-9\s]` to normalize names — deletes accented characters. Never considered non-ASCII input data.
- `precinct_vtd.py` keyed merge by `(precinct_id, vtd_geoid)` pairs — official and spatial can both appear for the same precinct. Never traced the downstream consumer's expectation.
- `plan_lifecycle.py` created a `by_id` dict in `build_lineage()` that is dead code. Never traced callers.
- Test `test_urbanicity_section` masks the field-mapping bug by asserting the wrong expectation. Test verified the assumption, not reality.

All five are the same class: **the agent assumed a data shape instead of reading it**.

## When to investigate

Investigation is required before any artifact is created, modified, or deleted. This is non-discretionary — the default is YES. The only artifacts exempt from this gate are the investigation artifact itself and its supporting reads (Phase 0–5 outputs).

Think of investigation as flashing an ID to get into a bar. You do not get to create, modify, or delete anything — code, config, skills, hooks, docs, anything — until you have shown evidence of knowledge gathering.

**Trivial-change escape (the ONLY exemptions):** Pure typo fixes, doc-only edits with no behavioral change, and single-line literal changes. Each requires a Trivial-investigation declaration in the self-review artifact with falsifiable evidence for why investigation was unnecessary. "This is simple" is not falsifiable evidence.

**The recursive case — pipeline editing itself:** Edits to skills (`skills/**/SKILL.md`), hooks (`hooks/**/*.sh`), and rule files (`_*-rules.md`) are never trivial. They change the behavior of the pipeline that governs all future work. A broken skill silently degrades every task that invokes it. Investigation for pipeline edits must trace: (1) which other skills consume this skill's output, (2) which hooks enforce this skill's requirements, (3) what changes for downstream tasks if this edit ships. The "doc-only edit" exemption does not apply to skills, hooks, or rules — these are behavioral artifacts, not documentation.

## Relationship to other skills

```
think (strategic: "what approach?")
  │
  │  think produces: approach selection, scope boundary
  │  think does NOT produce: verified facts about existing code
  │
  ▼
investigate (evidentiary: "what are the actual facts?")
  │
  │  investigate produces: Fact Sheet with file:line evidence
  │  investigate updates: ticket with impact chain, hypothesis, falsification
  │
  ▼
pre-mortem (adversarial: "if this ships and fails, why?")
  │
  │  pre-mortem consumes: investigated facts (Tigers must cite Fact Sheet)
  │
  ▼
implementation (grounded in verified facts)
```

Investigation consumes the approach from think and produces the evidentiary basis for pre-mortem and implementation. It is not a planning skill — it does not decide what to build. It determines what is true.

## Phase 0: Read existing knowledge

Before investigating code, read what already exists about the entities you're about to touch. The most common investigation failure is re-deriving context that was already documented — by a prior investigation, a ticket, a doc page, or a prior session's design note.

**Required reads (check each; record "N/A" or "read at <location>" for every item):**

| Source | What to look for | How to find it |
|---|---|---|
| **Ticket body** | Prior investigation links, referenced issues, acceptance criteria, assumptions | Read the ticket you're working on — don't just rely on the task prompt's summary |
| **Linked/related tickets** | Prior Fact Sheets, sibling-grep results, post-mortem findings about the same code | `gh issue list` with label/search filters; check the epic's issue list |
| **Existing documentation** | Module-level docstrings, CLAUDE.md sections, README, architecture docs, notebooks that demo the function | `Read` the file's module docstring; grep for the module name in docs/ and notebooks/ |
| **Git blame / recent commits** | Recent changes to the files you'll touch, especially reverts or fix-ups | `git log --oneline -10 <file>` for each file in scope |
| **Prior investigation artifacts** | Fact Sheets from earlier sessions that touched the same code | Check the ticket for linked Fact Sheets; grep PR bodies for "Investigation Fact Sheet" |
| **Post-error revisions** | Revised models from prior errors in the same code area — what was wrong and what the corrected understanding is | Search tickets and linked tickets for `## Post-error revision` sections; check git log for commits with `Post-error-revision:` trailers touching the same files |
| **Knowledge locus for each entity** | Where the canonical understanding of this entity lives — the place someone would go to learn how it works | For each entity touched: identify whether the locus is a ticket, doc page, CLAUDE.md section, module docstring, wiki article, or notebook. Record it — this is where corrections go when errors surface. The Fact Sheet is NOT a valid knowledge locus — it is an investigation artifact, not a canonical knowledge source. |

**Hard rule:** If a prior investigation exists for the same code entity and is less than 30 days old, start from its findings — don't re-derive from scratch. Cite it in your Fact Sheet's "Prior art" section. If it's stale, note what changed.

**Post-error revision rule:** If Phase 0 finds a post-error revision for code this task touches, the Fact Sheet's Prior Knowledge section MUST incorporate the revised model. An investigation that repeats a falsified assumption from a prior post-error revision is a Phase 0 failure — the learning was recorded and you ignored it.

**Knowledge locus rule:** For each entity the task touches, identify where the canonical knowledge about that entity lives. Record each locus in the Fact Sheet's "Knowledge Loci" section. This serves two purposes: (1) if this task will invalidate what the locus says, updating the locus is a required deliverable (feeds think Step 5); (2) if a future error falsifies what this investigation found, the correction goes to the designated locus, not to a fixed artifact type.

Record Phase 0 results at the top of the Fact Sheet under `### Prior Knowledge`.

## The investigation loop

### Phase 1: Impact Chain

Before reading any code, map the impact chain for the task:

```
## Impact Chain
Task: <one-line description>
Ticket: <reference>

### Upstream (what feeds into the code this task touches)
For each upstream entity:
- Entity: <name> (<type>)
- Location: <file:line>
- What it provides: <data shape, contract, or behavior>
- How I verified: <Read/Grep command and result>

### This Task (what changes)
- Files touched: <list with line ranges>
- Entities modified: <list>
- New entities created: <list>
- Contracts changed: <before → after, with evidence>

### Downstream (what consumes the output of this code)
For each downstream consumer:
- Entity: <name> (<type>)
- Location: <file:line>
- What it expects: <data shape, contract, or behavior>
- How I verified: <Read/Grep command and result>
- Impact of this task's changes: <what changes for this consumer>
```

The impact chain is documented in the ticket. It is not optional. The chain is what makes the investigation traceable — without it, the Fact Sheet is a collection of disconnected observations.

### Phase 2: Data Shape Verification

For every entity the task touches or references, read the actual definition and record its shape:

| What to verify | How to verify | What to record |
|---|---|---|
| Dataclass/model fields | Read the source file; `_meta.get_fields()` for Django | Field names, types, defaults — verbatim from source |
| Function signatures | Read the source file; `inspect.signature` if needed | Parameters, types, defaults, return type |
| Database columns | `\d+` (psql) or INFORMATION_SCHEMA | Column names, types, constraints, indexes |
| API response shapes | Curl/WebFetch a real endpoint or read the schema | Field names, types, nesting, optional vs required |
| Import paths | `python -c "import X; print(X.__file__)"` or grep | Exact module path, verify symbol exists in `__all__` or module scope |
| Env vars / config | Read config files, `.env.example`, deployment manifests | Variable names, expected types, default values |
| Existing tests | Read the test file; check what's mocked vs. what's live | What's asserted, what's mocked, mock-layer validity |

**Absence verification rule:** Before claiming an entity does not exist, run ≥2 distinct searches using different strategies (e.g., grep for the class name, grep for a unique method, search `__init__.py` exports, check the target branch with `git show origin/develop:path/to/file`). A single grep returning no results is not sufficient evidence of absence — the entity may exist under a different name, in a recently-merged file, or in a module you didn't search. Record each search attempt and its result. "Not found" requires evidence of a thorough search, not evidence of a single failed lookup.

**Tests as verified shapes:** Existing tests for the entities this task touches are first-class investigation targets. For each relevant test file:
- Read the test and record what it actually asserts (not what you assume it tests)
- Verify the mock/fixture layer: does the test mock at the right boundary, or does it mock away the behavior the task is changing?
- Record: test file:line, what it asserts, what it mocks, whether the mock is still valid after this task's changes
A test that mocks the layer you're changing is a test that will pass regardless of whether your change is correct. Flag it in the Fact Sheet as a verification gap.

**Hard rule:** Do not write a field name, function parameter, or import path from memory. Read it from the source file and record the file:line where you found it. If you cannot read it (e.g., external API with no local schema), record UNVERIFIED and flag it as a risk.

### Phase 3: Logic Tracing

For non-trivial logic the task modifies or depends on:

1. **Read the actual code path.** Follow the execution from entry point to output. Record what happens, not what you think happens.
2. **Identify branch conditions.** What values cause which branches? Are there edge cases the task's approach doesn't handle?
3. **Record concrete values.** Not "the function filters by state" — instead: "line 47 filters `assignments` where `a.state == state_fips`, so if `state_fips` is None, no filtering occurs and all states are returned."
4. **Trace error paths.** What exceptions can be raised? What happens on empty input? What happens on None?

### Phase 4: Environmental Readiness

Before implementation can begin, verify:

- [ ] All imports resolve (grep for the symbol in the source module).
- [ ] Test infrastructure is available (pytest runs, fixtures exist).
- [ ] If the task uses external data: sample data exists or can be constructed.
- [ ] If the task uses credentials: they are available in the target environment.
- [ ] If the task creates new files: the target directory exists and naming follows conventions.

Record each check with evidence. "Imports resolve" is not evidence. "`PostGISConnector` exists at `siege_utilities/geo/connectors.py:14`" is evidence.

### Phase 5: Coherence Check, Hypothesis, and Falsification

Before stating the hypothesis, check the Fact Sheet's own internal coherence. The findings from Phases 1–4 are a set of claims — do they agree with each other?

**Internal coherence questions:**
- Does the impact chain's "upstream provides X" match the verified shape of X in Phase 2?
- Does "this task changes Y" produce output that matches what "downstream expects Z" needs?
- Do the knowledge loci's "current state" descriptions match the verified shapes?
- If Phase 3 traced a logic path, does it use the field names and types from Phase 2 — or different ones?
- Are there assumptions in one phase that contradict findings in another?

An internally incoherent Fact Sheet means one of the phases got something wrong. Resolve the contradiction before proceeding — the hypothesis cannot be sound if the evidence it rests on contradicts itself.

**Then** state the hypothesis, grounded in the now-coherent findings:

```
## Coherence
<One sentence: are the findings from Phases 1-4 internally consistent?
 If a contradiction was found and resolved, state what it was and how.>

## Hypothesis
<What this implementation will achieve, stated as a testable claim>

## Falsification criteria
<What evidence would prove the hypothesis wrong>
<Specific test cases that, if they fail, indicate the implementation is wrong>
```

The coherence statement, hypothesis, and falsification criteria are documented in the ticket. They are not optional. They are what the self-review and post-mortem evaluate against.

## Fact Sheet artifact format

```
## Investigation Fact Sheet
Task: <one-line description>
Ticket: <reference>
Investigated: <timestamp>
Approach: <reference to think design note>

### Prior Knowledge (Phase 0)
- Ticket body read: YES/NO — <key findings from ticket>
- Related tickets consulted: <list with numbers, or "none found">
- Prior investigations for this code: <link/citation, or "none found">
- Recent git history for touched files: <notable commits, or "no recent changes">
- Existing documentation: <module docstrings, docs/ pages, or "none">
- Post-error revisions found: <ticket#, date, revised model — or "none found">

### Knowledge Loci
For each entity this task touches:
- **<Entity>**: knowledge locus is <location> (ticket / doc page / docstring / CLAUDE.md / wiki / notebook / etc.)
  - Current state: <what the locus says now>
  - Will this task invalidate it: YES / NO
  - If YES: update is a required deliverable (feeds think Step 5)

### Revised Facts (from post-error revisions)
For each post-error revision found in Phase 0:
- **Revision source:** <ticket#, date>
- **Falsified assumption:** <what was wrong>
- **Revised model:** <what's actually true>
- **Impact on this task:** <how this changes our approach>
(If none found, record "No post-error revisions found for this code area.")

### Impact Chain
<Phase 1 output — full upstream/task/downstream chain>

### Verified Shapes
For each entity:
- **<Entity name>** (<type>, <file:line>)
  - Fields/signature: <verbatim from source>
  - Verified at: <file:line>
  - Assumptions my task makes: <named explicitly>
  - Verification status: VERIFIED | UNVERIFIED (with reason)

### Logic Trace
<Phase 3 output — concrete execution paths with values>

### Environmental Readiness
<Phase 4 checklist with evidence>

### Coherence
<Phase 5 coherence statement — are Phases 1-4 internally consistent?>

### Hypothesis and Falsification
<Phase 5 hypothesis and falsification criteria>

### Open Questions
<Anything that could not be verified, with why and what the risk is>

### Findings
For each issue discovered during investigation:
- **Finding <N>:** <description>
  - Severity: HIGH | MEDIUM | LOW
  - Evidence: <file:line, concrete values>
  - Impact: <what breaks, who is affected>
  - Recommendation: <fix, defer with justification, or accept with rationale>
```

## Scaled Fact Sheet for low-impact tasks

The full Fact Sheet format has 10+ sections because high-impact tasks need them. But a single-function bug fix that touches one file and has no downstream consumers doesn't need an impact chain with upstream/downstream mapping — that's compliance overhead that incentivizes skipping investigation entirely.

**Two tiers:**

| Tier | When | Required sections |
|---|---|---|
| **Full** | Touches 3+ files, modifies shared interfaces, changes data shapes, or crosses module boundaries | All sections (Prior Knowledge through Findings) |
| **Focused** | Touches 1-2 files, modifies internal logic only, no interface changes, no downstream impact beyond the file | Prior Knowledge, Knowledge Loci, Verified Shapes, Hypothesis and Falsification |

The Focused tier is NOT a lower standard — it still requires file:line citations, shape verification, and a falsifiable hypothesis. It drops the sections that genuinely have nothing to say: impact chain (nothing upstream/downstream), logic trace (the change is the logic), environmental readiness (no new dependencies).

**Focused Fact Sheet format:**

```
## Investigation Fact Sheet (Focused)
Task: <one-line description>
Ticket: <reference>
Investigated: <timestamp>
Scope justification: <why Focused tier — must name: files touched (1-2),
                      no interface changes, no downstream consumers beyond
                      this file. If any of these don't hold, use Full.>

### Prior Knowledge (Phase 0)
- Ticket body read: YES/NO — <key findings>
- Post-error revisions found: <citation or "none found">
- Recent git history: <notable commits or "no recent changes">

### Knowledge Loci
- **<Entity>**: knowledge locus is <location>
  - Will this task invalidate it: YES / NO

### Verified Shapes
- **<Entity name>** (<type>, <file:line>)
  - Fields/signature: <verbatim from source>
  - Verification status: VERIFIED | UNVERIFIED

### Coherence
<Do the prior knowledge, loci, and verified shapes agree with each other?>

### Hypothesis and Falsification
<testable claim and what would prove it wrong>
```

**Escalation rule:** If at any point during a Focused investigation you discover a downstream consumer, an interface change, or a cross-module dependency, escalate to Full. If the coherence check reveals contradictions between sections, that is also an escalation signal — contradictions in a Focused investigation often indicate the task has more surface area than the Focused tier assumed.

## Post to ticket and continue (hard gate)

When the Fact Sheet is complete, post it to the ticket NOW. Use `gh issue comment <number> --body "..."` or equivalent. The session copy is a working draft; the ticket comment is the canonical copy.

Do not proceed past investigation until the Fact Sheet is on the ticket. An investigation that stays in the session is an investigation that doesn't exist.

**Then continue autonomously to the next pipeline gate** (pre-mortem, per the RESOLVER). Do not wait for parent approval or operator acknowledgement to proceed. The pipeline is self-driving: produce the artifact, post it, advance.

## Composition with existing skills

- **survey-context** already verifies entity shapes against doc pages. Investigation extends this to: (a) entities without doc pages, (b) logic tracing beyond shape, (c) impact chain mapping, (d) environmental readiness. When survey-context exists for the project, investigation consults its entity docs as a starting point but does not trust them without live verification.
- **think Step 1 (Context)** currently says "Read the relevant files. Don't guess about the current state." Investigation systematizes this: instead of a reminder, it produces a checkable artifact with file:line evidence.
- **self-review** references the Fact Sheet in its `Goal source` and `Pre-author-inventory` fields. The Lead's adversarial pass checks whether the implementation matches the investigated facts.
- **pre-mortem** requires Tigers to cite the Fact Sheet. A Tiger that isn't grounded in investigated facts is a Paper Tiger (speculation, not evidence).

## Hard rules

1. **No artifact CRUD before investigation.** Investigation is required before any artifact is created, modified, or deleted — not just implementation files. The Fact Sheet's existence is the floor.
2. **File:line or it didn't happen.** Every claim about existing code must cite the source location. "The model has a `name` field" is not evidence. "`name: str` at `models.py:42`" is evidence.
3. **Read, don't recall.** Do not write entity shapes from memory or from a previous conversation. Read the current source file. Every time.
4. **Impact chain is mandatory.** Upstream and downstream must be traced for every task that modifies shared entities. "I don't think anything depends on this" is not acceptable without a grep to prove it.
5. **Findings are not optional.** If investigation discovers issues, they are recorded. Suppressing findings to avoid scope creep is a self-review violation.
6. **The ticket gets the chain.** Impact chain, hypothesis, and falsification are documented in the ticket — not just in the Fact Sheet. The ticket is the spine; the Fact Sheet is the evidence appendix.
7. **If the work has a ticket, the Fact Sheet goes on the ticket. This is not optional.** Post the Fact Sheet (or a link to it) as a comment on the ticket when the investigation is complete. Session-scoped plan files are working drafts — they disappear when the session ends. If the Fact Sheet is too long for a comment, commit it to the repo (e.g., `docs/investigations/<module>-<ticket>.md`) and link from the ticket. A Fact Sheet that only exists in a session plans folder is a Fact Sheet that doesn't exist.
8. **Phase 0 is not optional.** Reading existing knowledge before investigating is as mandatory as reading code before writing code. An investigation that re-derives facts already documented in a prior Fact Sheet or ticket is wasted work and a signal that the agent skipped Phase 0.

## What investigation is NOT

- **Not a design skill.** Investigation does not decide what to build. It determines what is true. The approach comes from think; investigation verifies whether the approach is grounded.
- **Not a planning skill.** Investigation does not break work into tasks. It produces facts that inform task breakdown.
- **Not exhaustive.** Investigation traces the entities and logic the task actually touches. It does not audit the entire codebase. Depth heuristics from survey-context apply: DEEP for touched entities, SHALLOW for referenced entities, SKIP for transitive dependencies the diff doesn't engage.
- **Not a substitute for tests.** Investigation verifies pre-conditions. Tests verify post-conditions. Both are required.
