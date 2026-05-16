---
name: self-review
description: "Always-on. Self code-review before any push / PR-open / PR-merge. Produce a structured artifact with assumptions (including roles), peer review against the shelves, and lead review naming affirmative standards from outside the shelves. The pre-push hook enforces presence of the trailers and structural completeness; quality of content remains operator-auditable."
user-invocable: true
---

# Self Code-Review

Run this skill before any action that pushes work outward: `git push`,
`gh pr create`, `gh pr merge` (including admin-merge). The artifact
this skill produces is the durable thing; the diff inspection is
ephemeral. CodeRabbit, GitGuardian, and sibling-session validation
compensate but do not substitute.

## Why a written artifact

A "look at the diff" reminder is a habit, not a rule -- under context
pressure it gets skipped. A structured artifact with required sections
makes the questions impossible to skip without producing visible
absence. The artifact also exposes content to operator scrutiny in a
way that a mental gesture cannot.

## When self-review applies

Required before:
- `git push` on any branch (including feature branches pushing to
  their own PR).
- `gh pr create`.
- `gh pr merge` (including `--admin`).

Trivial-change escape: review is still required, but a no-findings
review on a genuinely trivial change is one valid output of the
artifact. The artifact-existence floor is non-negotiable; the
artifact's content scales with the work's scope.

## Artifact format

Required sections:

```
## Assumptions
Working as: <role(s)>
Peer review needed from: <role(s)>
Lead review needed from: <role(s)>
Goal source: <ticket #N | design-note path | quoted user-request paragraph>
Plan reference: <path-or-link to the design note this diff implements>

## Peer review (mechanics, correctness, craft floor)
For each applicable shelf: what was checked, what was found.
Grep / test-output / file-read evidence inline per `_writing-claims-rules.md`.
Empty sections allowed only when the diff genuinely doesn't engage
that shelf; the omission itself is auditable.

## Lead review (approach-fit, blast radius, sequencing)
Role-tagged. Affirmative standards from outside the shelves named
explicitly, with the role-context.
  E.g.: "As data engineer: the load is idempotent because <evidence>."
Approach-fit verdict. Blast radius declared. Sequencing assumption
that has to hold for this to be the right move.
```

## Roles

The role declaration in the Assumptions section names the lens
through which the work was done and the lens(es) the review needs to
come from. Roles include:

- **Software engineer** -- implementing features, fixing bugs, writing
  tests. Shelves cover this role nearly completely.
- **Tech lead** (loose: anyone reviewing for fit-and-direction) --
  architectural decisions, sequencing, blast-radius reasoning. Shelves
  cover partially (`_writing-releases-rules.md` 1/2/5, writing-claims:4).
- **Data engineer** -- pipelines, schemas, ETL. Shelves cover partially
  (writing-code:5, writing-tests:1, writing-claims:1-3). Most
  affirmative standards (idempotence, replayability, schema evolution,
  partitioning, watermarking, lineage) live in domain expertise.
- **Data analyst** -- analysis, statistical rigor, defensible findings.
  Shelves cover mostly via `_writing-claims-rules.md`. Most affirmative
  standards (sample-size adequacy, confounder controls, observed-vs-
  inferred, falsifiability, MAUP / ecological fallacy / scale effects)
  live in domain expertise.
- **Geospatial expertise + delight** -- cross-cutting. Not shelved.
  Affirmative standards: CRS appropriateness per operation (4326 for
  storage, equal-area for buffer/area, web-mercator for tiles),
  spatial-index hygiene before any `ST_*` predicate, modern format
  choice (GeoParquet > Shapefile; COG / Zarr where they fit), semantic
  naming of geographic concepts (vintage / plan / district / GEOID),
  elegant temporal-spatial intersections. **Delight as audit signal**:
  "would I point at this work?"

The Lead review section must NAME the affirmative standard being
checked, role-tagged. Format: "As <role>: <standard> holds because
<evidence>" or "As <role>: <standard> not yet shelved, applied
judgment per <argument>." Both are honest and auditable; what is NOT
acceptable is omitting the role tag when no shelf exists, which
hides the gap.

## Peer review uses the shelves

Run each applicable shelf against the diff at review time:

- `_writing-code-rules.md` -- docstring discipline, no speculative
  abstractions, verify symbols exist, no hypothetical code, doc-edit
  symmetry, no silent processes.
- `_writing-tests-rules.md` -- tests must fail on revert and import the
  module they test, no cargo-cult patterns, skips name remediation.
- `_writing-claims-rules.md` -- grep before declaring complete, countable
  claims grounded in same-turn evidence, unquantified completeness
  claims grounded too, invented framework signals require existing
  artifact backing.
- `_writing-prose-rules.md` -- no AI-typographic Unicode, no "Why:" /
  "How to apply:" structured blocks in code comments or commit
  messages, no header stacking in commit bodies.
- `_writing-releases-rules.md` -- BREAKING discipline, skip-count trend,
  Verified-by trailer on countable claims, verify in consumer
  environment.

Peer section format per shelf: name the rule checked, state what was
checked, cite the evidence (grep output, file path read, test result).
For shelves the diff doesn't engage, omit the section -- the omission
itself is auditable.

## Lead review uses domain affirmative standards

The shelves are negative guardrails for software-engineer-shaped work.
For tech-lead, data-engineer, data-analyst, and geospatial work, the
affirmative standards live in domain expertise, not in shelved rules.

Lead section format: for each affirmative standard the work needs to
meet, name the role, name the standard, cite the evidence. If the
standard is not shelved (the common case for non-SWE roles), say so
explicitly and cite the judgment argument.

Example (data-engineering load):
> As data engineer: load is idempotent because INSERT uses
> `ON CONFLICT (id) DO UPDATE`; replayable from raw via partition
> column `extracted_at`. Standards not shelved; applied per usual ETL
> practice.

## Recursion

The artifact makes claims about the diff ("no regressions," "all sites
fixed," "loop closed"). `_writing-claims-rules.md` 1-4 fire on those
claims as they would on any other agent-produced text:

- writing-claims:1 -- grep before declaring fix complete.
- writing-claims:2 -- countable claims need the falsifying grep in the
  same artifact.
- writing-claims:3 -- unquantified completeness claims grounded too.
- writing-claims:4 -- coining new framework names in the review
  requires existing artifact backing.

`_writing-prose-rules.md` applies to the artifact's typography. The
review's language is subject to the same discipline as any other
prose the agent produces.

This recursion prevents the artifact from becoming theater. An empty
"no concerns" verdict is itself a writing-claims violation, visible
to anyone reading the artifact.

## Goal source is load-bearing

If the goal field is sourced from the diff itself (PR title, commit
subject), the artifact can structurally satisfy writing-claims while
substantively reviewing nothing -- "Goal: implement X. Diff implements
X. No concerns." is a tautology dressed as a claim. Sourcing the goal
from a pre-existing artifact (ticket filed before work began, design
note, user-request quote) makes "diff implements goal" a non-trivial
claim instead of a restatement.

The v1 pre-push hook mechanically verifies the goal source field is
present and non-empty. The "filed before the work" and "is not the
diff's own commit message" checks are v2 follow-up work (see the
v1/v2 split in the next section); until v2 ships, those two checks
remain operator-auditable rather than mechanical.

## Trailers and hook enforcement

The latest commit being pushed must carry both trailers:

```
Self-Review: <one-line summary of the review pass>
Self-Review-Source: <path or ticket pointing at the artifact>
```

These match the existing `Verified-by:` trailer idiom that
writing-claims:2 already requires. The pre-push hook greps the latest
commit only (not every commit in a range, to avoid retroactively
blocking fixup pushes). Absence is push-blocking with a stderr message
pointing at this skill.

The hook splits enforcement across two scopes: what v1 enforces
mechanically today, and what v2 follow-up work will add. Split is
explicit because claiming hook enforcement that the hook does not
provide is itself a `_writing-claims-rules.md` writing-claims:4
violation -- the SKILL is making a claim about what the hook does, so
the claim must be grounded.

**v1 enforced mechanically (in the pre-push hook today):**

- Both trailers present in the trailer block of the latest commit
  (parsed via `git interpret-trailers --parse`, not line-anchored
  grep -- rejects trailer keywords that appear in the subject or body).
- Exactly one `Self-Review-Source:` value (multiple = ambiguous,
  blocked).
- If the source value is a file path: file exists, has the three
  required section headers (`## Assumptions`, `## Peer review`,
  `## Lead review`), has a non-empty `Goal source:` line.
- Assumptions section names at least one role from the canonical
  set (software engineer / tech lead / data engineer / data analyst /
  geospatial).
- Peer review section cites at least one shelf
  (writing-code / writing-tests / writing-claims / writing-prose /
  writing-releases).

**v2 follow-up to enforce mechanically:**

- Goal source does NOT point at the commit being pushed (currently
  operator-auditable; mechanizing the "doesn't point at" check is
  non-trivial -- could be a SHA, a commit subject quote, a ticket
  filed before vs after the commit timestamp).
- Lead section's role-tagged affirmative-standard format
  (`As <role>: <standard> holds because <evidence>`).
- `detect-ai-fingerprints` scan against the source artifact.
- `Verified-by:` trailers (or grep-output equivalents) for any
  countable / completeness claim made inside the source artifact.
- Ticket-reference source values (e.g. `#123`) validated against the
  issue tracker (currently passes as-is; only file-path sources are
  structurally checked).
- Merge-time re-verification on `gh pr merge` -- the diff-since-last-
  review can change between push and merge if fixup commits land in
  between, so the merge command should re-check the trailer on the
  PR branch's latest commit at merge time.

**v1 + v2 together** cover the full enforcement surface the rule
needs. v1 is the floor that ships first; v2 follows once real-world
false-positive data from v1 has informed the v2 check shapes.

The hook cannot verify quality of the content; that remains
operator-auditable in both v1 and v2. But absence is enforceable, and
the structural questions are impossible to skip.

## Three-layer separation

- **Hook says WHAT.** The pre-push hook enforces presence of the
  trailers and structural completeness of the artifact.
- **Memory says WHEN.** `feedback_self_code_review.md` is the always-on
  nudge: do self-review before push / PR / merge.
- **Skill says HOW.** This file is canonical. Memory and hook point
  at it.

## Origin

Designed across session 260502-vital-channel on 2026-05-16 with
sibling review from 260502-pure-vista. Operator-promoted from the
session's `plans/self-review-rule-design.md` v2.
