---
name: self-review
description: "MANDATORY pre-push / pre-PR-open / pre-PR-merge gate. Produce a structured artifact with Assumptions (including roles + Goal source verification via evaluate-ticket + Pre-author-inventory link + Evidence-predates-work block), Peer review against the shelves, and Lead review naming affirmative standards. The pre-push hook enforces trailer presence, structural completeness, artifact-predates-work, and the writing-rules:4 evidence-chain on any Trivial-change / Exemption blocks. Do NOT skip this skill; the form is checkable but the discipline is what binds."
disable-model-invocation: true
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
Goal source verification: <paste the PASS line from `bash <scripts>/discipline/evaluate-ticket.sh <ticket-ref>`>
Plan reference: <path-or-link to the design note this diff implements>
Pre-author-inventory: <ticket-link#pre-author-inventory | plans/path.md#pre-author-inventory | NONE>

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

## Evidence-predates-work
Artifact: <path to this artifact>
First-added commit: <paste output of `git log -1 --diff-filter=A --follow --format=%H -- <artifact-path>`>
Work commit: <paste `git rev-parse HEAD`>
Verification: <paste output of `git merge-base --is-ancestor <first-added> <work-commit>; echo $?` — must be 0>
```

## Pre-author-inventory field

The `Pre-author-inventory:` field in the Assumptions section is a **required
composability link** between this skill and
[`_authoring-against-state-rules.md`](_authoring-against-state-rules.md):6.

Before authoring any runtime artifact whose contact points trigger rules 1-5 of
that shelf, the agent must complete a pre-author investigation and record its
findings in the ticket (a `## Pre-author inventory` section per the template in
the shelf). The self-review artifact must then point at that record:

```
Pre-author-inventory: enterprise#2094#pre-author-inventory
```

or for session-local plan files:

```
Pre-author-inventory: plans/2094-silver-exp/pre-author-inventory.md
```

This makes the omission structurally visible: an agent that skipped the
pre-investigation cannot populate this field without fabricating a link, and a
fabricated link fails the first spot check.

**When NONE is acceptable:** if the change does not trigger any of the five
authoring-against-state contact categories (data-shape, config-state, topology,
plan-shape, version-resolution), the field may be `NONE` — but only when a
`Trivial-against-state:` declaration is also present in the artifact. The
hook checks for the declaration; absence of the declaration with a NONE value
is a block.

**The field is NOT a quality gate on the inventory itself.** The hook checks
structural presence (field exists, value non-empty or NONE+declaration). Content
quality — whether the inventory actually covered the relevant surfaces, whether
the hypothesis was falsifiable, whether the seven steps were followed — remains
operator-auditable. The field's purpose is to make the composability explicit
and to block the pattern where a structurally-complete self-review was written
without any pre-investigation at all.

## Trivial-change declaration (when no ticket cited)

If the work is genuinely too small to warrant a ticket — typo fix,
doc-only edit, single-character revert — the artifact may include
this block in place of `Goal source verification`. The block itself
requires the same evidence chain as any "this doesn't apply" claim
(`_writing-rules-rules.md` writing-rules:4):

```
## Trivial-change declaration

Category: <token from the writing-rules:5 controlled vocabulary —
           prose-only-docs | comments-only | whitespace-only |
           commit-msg-only | private-rename |
           descriptive-docstring-fix | fixed-string-correction>
Cannot produce error: <one sentence stating the claim that this change
                       cannot generate empirical evidence contradicting
                       the agent's model of the system — falsifiable>
Evidence: <command output proving the Category's Evidence-shape
          requirement per writing-rules:5 — e.g. for `prose-only-docs`,
          the grep showing no behavior tokens in changed regions; for
          `private-rename`, the grep showing only-the-rename-site>
Falsification: <observable that would prove the Cannot-produce-error
                claim wrong; if this observable later surfaces, this
                block is the post-error revision trigger>
```

The local hook (`hooks/git/self-review.sh`) and the canonical script
(`scripts/discipline/check-trivial-claim.sh`) validate that all three
fields are present and that the Evidence field contains a verifiable
observation token (command output, file path with extension, fenced
code block, stat/count, or URL). Free-text assertions like "obviously
trivial" or "minor cleanup" fail.

### When the Falsification observable surfaces

The Falsification field is the writing-rules:6 trigger. If the observable named there later surfaces — an `AttributeError` matching the renamed symbol, a behavior claim acted on from prose-only-docs, a non-comment line changed by what was claimed comments-only — the Trivial-change declaration was wrong, and the response is **not** to just fix the bug.

Per writing-rules:6 (and [skill:post-error-revision]):

1. File a ticket retroactively, citing the failed Trivial-change block as Goal source.
2. Append a `## Post-error revision` block to the new ticket with the five required fields (Triggered by / Observed / Falsified assumption / Revised model / Implication).
3. THEN draft the fix PR with a `Refs:` + `Post-error-revision:` trailer pair.

Skipping this and just pushing the fix re-runs the same Assumption on the next change. The Trivial-change Falsification field exists to make the trigger explicit; ignoring it when it fires defeats the whole writing-rules:5 -> writing-rules:6 loop.

## Exemption blocks

When a specific `evaluate-ticket` criterion doesn't apply to your
work (e.g., a docs-only ticket can't state a falsification criterion
in the writing-tests:1 shape), paste an exemption block per criterion:

```
## Exemption: <criterion-name>

Reason: <why this criterion doesn't apply>
Evidence: <command output or verifiable observation supporting the
          exemption — e.g. `git diff --stat | grep -v '\.md$'` returns
          no rows, proving no non-doc files changed>
Falsification: <observable that would make this exemption wrong>
```

Same validation as Trivial-change declaration. Same enforcement path.

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
- **v1.1**: If `Goal source:` value is itself a file path, its mtime
  must not be newer than the review artifact's mtime (catches goal-
  source-written-after-the-work post-hoc-justification pattern).
- **v1.2 (this PR)**: `Pre-author-inventory:` field present and non-empty
  in the Assumptions section. `NONE` accepted only when a
  `Trivial-against-state:` declaration is also present.
- **v2 (claude-configs-public#146)**: If the artifact file lives in a
  git repo, the artifact's first-added commit must be an ancestor of
  the work commit being pushed (`git log --diff-filter=A --follow` +
  `git merge-base --is-ancestor`). Closes the retroactive-trailer
  loophole that lets agents push first, write the artifact later, and
  satisfy the form check while bypassing the discipline. Defense in
  depth alongside v1.1's mtime check; this one is touch-resistant.
- **v2 (claude-configs-public#146)**: If the artifact contains a
  `## Trivial-change declaration` or `## Exemption:` block, each block
  must have all three fields (Reason / Evidence / Falsification) AND
  the Evidence field must contain a verifiable observation token
  (fenced code block, file path with extension, git command, stat/
  count, or URL). Free-text assertions fail. Delegated to
  `scripts/discipline/check-trivial-claim.sh`.
- Assumptions section names at least one role from the canonical
  set (software engineer / tech lead / data engineer / data analyst /
  geospatial).
- Peer review section cites at least one shelf
  (writing-code / writing-tests / writing-claims / writing-prose /
  writing-releases / writing-rules).

**v2 follow-up to enforce mechanically:**

- Goal source does NOT point at the commit being pushed AND was filed
  before the commit timestamp. **v1.1 lands the partial mtime-based
  check** for file-path-shaped goal sources (block if goal-source mtime
  > review-artifact mtime -- catches post-hoc-justification patterns).
  Heuristic: `touch` defeats it; stronger check needs git history which
  session-scoped plans/ files don't have. **v2 still owed:** ticket-
  shaped sources (`#NNN`) validated via `gh issue view --json createdAt`
  against the commit timestamp; SHA / commit-subject-quote source
  detection.
- Lead section's role-tagged affirmative-standard format
  (`As <role>: <standard> holds because <evidence>`).
- `detect-ai-fingerprints` scan against the source artifact.
- `Verified-by:` trailers (or grep-output equivalents) for any
  countable / completeness claim made inside the source artifact.
  (Tracked as separate issue — see PR body for link.)
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

## Known limitations (recoverable, document-the-workaround posture)

The hook fires at PreToolUse — BEFORE the bash command runs — and inspects
the latest commit at that moment. This produces several documented false
positives the agent can recover from by adjusting invocation shape:

- **Chained `git commit -m "..." && git push`.** The hook sees `git push`
  in the command and inspects HEAD. At that moment HEAD is the PRE-commit
  HEAD (the in-flight commit hasn't happened yet), so the trailer pair
  from the imminent commit isn't visible. The hook blocks. **Workaround:**
  split into two separate Bash invocations -- first `git commit -m "..."`,
  then `git push origin <branch>` as a separate call. Once the commit
  lands on HEAD, the push's hook check sees the trailers. Issue #107.
- **`echo` / `printf` / heredoc strings containing the literal substrings
  `git push`, `gh pr create`, `gh pr merge`.** The substring matcher
  fires on the text regardless of whether the agent is actually invoking
  the command. **Workaround:** for test scripts that need to demonstrate
  the substring, write them to `/tmp/` (outside any git repo where the
  hook's branch detection applies), or reformulate to avoid the literal
  substring. Same posture as branch-guard's well-documented
  `bash wrapper.sh` limitation (#98).
- **Multi-statement commands with `cd`.** Mirrors branch-guard discipline
  (#101): if the command has more than one `cd` OR contains chained
  statements (newline / `;` / `||`) with at least one `cd`, the hook
  yields rather than risk evaluating the wrong repo. Same workaround:
  split into separate Bash invocations.
- **Craft Agent sessions.** The hook fires via `PreToolUse` wiring in
  Claude Code's `settings.json`. Craft Agent sessions run their own
  tool-call surface and do not share Claude Code's hook mechanism --
  this hook does not fire for Craft Agent push/PR operations. Craft
  Agent sessions must apply self-review discipline manually; the
  artifact requirement and trailer format remain identical but
  enforcement is operator-auditable rather than mechanical. Downstream
  projects using Craft as their primary agent surface should note this
  gap in their workspace `CLAUDE.md` so sessions are aware.

These are conservative-bias trade-offs. The hook prefers a recoverable
false positive over a silent false negative; "split into separate calls"
is the standard recovery pattern across the hook family.

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
