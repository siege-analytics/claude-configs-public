---
description: Always-on Definition of Done. Applied to every behavior change. Five hard criteria plus two opt-in -- review, edge cases, tests, ticket update, ticket existence, KB delta, multi-layer decomposition. No soft carve-outs on (a)-(e).
---

# Definition of Done

Code is not finished until **all five** of the following are true. This is a gate, not a recommendation. PRs that fail any criterion don't merge; sessions that fail any criterion don't end.

## The five criteria

### a. Code-reviewed

Every behavior change goes through code review at **two transitions**: pre-commit (against the staged diff, by [`code-review`](code-review/SKILL.md)) and pre-merge (against the cumulative PR diff, by CodeRabbit + human reviewer for non-trivial changes). The pre-commit pass catches findings while context is fresh and the diff is small; the pre-merge pass catches findings that only emerge across multiple commits.

**Operationalized by:** [`code-review`](code-review/SKILL.md) (slash-invokable as `/code-review`); [`commit`](commit/SKILL.md) step 3 (pre-commit gate); [`create-pr`](create-pr/SKILL.md) (pre-PR cumulative review).

### b. Edge cases explored

Every behavior change has been tested mentally -- and where appropriate, in tests -- against:

- Empty input (`[]`, `""`, `None`, missing key)
- Boundary values (zero, one, max, min, off-by-one neighbors)
- Duplicates
- Out-of-order input
- Very small (1 element) and very large (1M+ elements)
- Mixed types where the contract claims homogeneity
- Partial failure (network timeout mid-batch, write succeeded but ack failed, half the rows valid)
- Null / NaN / NULL in tabular inputs
- Identifier collisions (two different sources, same key)

**Operationalized by:** [`code-review`](code-review/SKILL.md) §1 ("Correctness") -- explicit edge-case checklist.

### c. Tests written

**Tests are mandatory for all behavior changes.**

- Every new function, method, or behavior change has at least one test.
- Every `raise` path has a negative test.
- Bug fixes ship with a regression test that fails on the previous commit.
- If the project has no test infrastructure yet, **the first contribution adds the infrastructure** (test framework, runner, sample test) before any behavior change. "We don't have tests yet" is not an exception; it's the first ticket.
- PRs without tests must justify the omission in the PR description, and the justification is subject to review. Acceptance is not assumed.

**Operationalized by:** [`python`](python/SKILL.md) "Tests and Documentation -- non-negotiable" section (Python); [`coding`](coding/SKILL.md) Rule 6 (language-agnostic).

### d. Non-trivial updates → update the ticket

Non-trivial work updates the ticket as it progresses. The ticket reflects the current state of the work, not the state when it was written.

What counts as a ticket update:
- Status transitions (Todo → In Progress → In Review → Done)
- Comments on substantive changes (scope expansion, blocker discovery, design pivots)
- Links to commits and PRs (bidirectional -- commit references ticket, ticket links commit)
- Final summary at close (what shipped, what was deferred, validation status)

**Operationalized by:** [`update-ticket`](update-ticket/SKILL.md) (slash-invokable as `/update-ticket`); [`close-ticket`](close-ticket/SKILL.md).

### e. Work has a ticket

Every behavior change starts from a ticket. Tickets exist to:
- Establish *why* the work is being done (problem statement)
- Track scope and acceptance criteria
- Surface dependency relations (what blocks this; what this unblocks)
- Provide an audit trail tying code changes to motivating problems

**Operationalized by:** [`pre-work-check`](pre-work-check/SKILL.md) (slash-invokable as `/pre-work-check`) -- runs before the first commit; verifies ticket exists, belongs to a project, has no open blockers.

If you find yourself coding without a ticket, stop and write one (or invoke [`create-ticket`](create-ticket/SKILL.md)). The ticket can be a one-liner; what matters is that it exists and is reachable from the commit.

### f. Knowledge-base delta validated (opt-in)

When a project declares `knowledge_base:` in PROJECT.md, any `kb-contradicted` finding during investigation must have a filed delta before Done. A delta is a KB update PR, docs/ edit, wiki page change, or ticket for deferred update. The delta does not have to be merged -- a filed PR or ticket referencing the contradiction is sufficient. What matters is that the correction entered the work-tracking system.

`kb-silent` findings that investigation resolved should produce a KB addition or a ticket for the addition. Gaps are debt, not lies -- lower urgency than contradictions, but tracked.

This criterion is opt-in: projects without `knowledge_base:` in PROJECT.md are unaffected. Once declared, criterion (f) becomes part of the gate alongside (a)-(e).

**Operationalized by:** [`knowledge-base`](knowledge-base/SKILL.md) (read-tag-update protocol); `[`knowledge-base`](_knowledge-base-rules.md)` knowledge-base:3 (update on contradiction); think-gate-guard.sh Level 3 (advisory warning).

### g. Multi-layer work is decomposed (opt-in)

When a project declares `testing.layers` in PROJECT.md (see `[`testing-frameworks`](_testing-frameworks-rules.md)`), work touching more than one declared layer must be decomposed into per-layer tickets under a parent epic before implementation begins. Each per-layer ticket names its test framework, test directory, and assertion classification.

Single-layer work is exempt -- one ticket suffices when only one declared layer is touched. The decomposition table posted on the parent epic is the auditable artifact.

This criterion is opt-in: projects without `testing.layers` in PROJECT.md are unaffected.

**Operationalized by:** [`ticket-decomposition`](ticket-decomposition/SKILL.md) (authoring + consumer protocols).

## What "done" means at each transition

| Transition | Done check |
|---|---|
| Pre-commit | [`code-review`](code-review/SKILL.md) runs on the staged diff (Blockers resolved, Majors fixed-or-deferred); tests added/updated; docstrings on new public APIs; commit message references the ticket |
| Pre-PR | All five criteria; PR description summarizes scope, links the ticket, lists what was tested |
| Pre-merge | CodeRabbit + GitGuardian + (when relevant) human review pass; ticket is In Review status |
| Session-end | All five criteria across all changes in the session; ticket status reflects current state; no orphan commits without ticket links |

## Operationalization map

| Criterion | Skill / file that runs it |
|---|---|
| (a) Code-reviewed | [`code-review`](code-review/SKILL.md) |
| (b) Edge cases | [`code-review`](code-review/SKILL.md) §1 |
| (c) Tests | [`python`](python/SKILL.md) "Tests and Documentation" section; [`coding`](coding/SKILL.md) Rule 6 |
| (d) Ticket update | [`update-ticket`](update-ticket/SKILL.md), [`close-ticket`](close-ticket/SKILL.md) |
| (e) Ticket exists | [`pre-work-check`](pre-work-check/SKILL.md), [`create-ticket`](create-ticket/SKILL.md) |
| (f) KB delta (opt-in) | [`knowledge-base`](knowledge-base/SKILL.md), `[`knowledge-base`](_knowledge-base-rules.md)` knowledge-base:3 |
| (g) Multi-layer decomposition (opt-in) | [`ticket-decomposition`](ticket-decomposition/SKILL.md) |

The PR-creation gate ([`create-pr`](create-pr/SKILL.md)) checks all five before opening.

The session-end check ([`wrap-up`](wrap-up/SKILL.md)) verifies all five before declaring the session complete.

## Exceptions

The following categories are exempt from criteria (a)–(d) but **not** from (e) (ticket existence):

- **Typo fixes** with no functional effect (the same word, spelled correctly)
- **Doc-only changes** that don't reframe API contracts
- **Tooling / CI / build chores** that don't change runtime behavior

Per `_writing-rules-rules.md` writing-rules:4, claiming the exemption is itself a "this doesn't apply" claim and requires the evidence chain. The exemption goes in the self-review artifact (or the commit body if no artifact) as:

```
## Trivial-change declaration

Category: <token from the writing-rules:5 controlled vocabulary --
           e.g. `prose-only-docs` for a doc-only edit;
           `commit-msg-only` for an --amend>
Cannot produce error: <one sentence stating the falsifiable claim that
                       this change cannot generate empirical evidence
                       contradicting the agent's model>
Evidence: <command output supporting the claim -- e.g. `git diff --stat`
          showing 1 file changed in docs/ only; `grep -l "def\|class" $(git diff --name-only)`
          returning empty for non-code change>
Falsification: <observable that would make this exemption wrong --
               e.g. "NOT exempt if any non-docs/ file changes" or
               "NOT exempt if test count changes">
```

Validated by `scripts/discipline/check-trivial-claim.sh` when the artifact is parsed by the self-review hook. Free-text assertions ("obviously a typo," "minor cleanup") fail.

If in doubt, apply the full Definition of Done. The cost of unnecessary diligence is low; the cost of skipping diligence on a behavior change that looked trivial is high.

Even exempt changes still need a ticket -- the tracking serves the audit trail, not just the work-discipline.

## Why hard enforcement

Soft rules erode. "We should have tests" becomes "we'll add tests later" becomes "we don't have tests for this codebase, sorry." The same drift applies to review, ticket updates, and ticket existence. Each of the five criteria has a documented Siege incident in its origin: missing tests masked a regression that shipped to production; missing reviews let an architectural mistake compound; missing ticket updates left another team blocked on what they thought was unblocked; ticketless work derailed roadmap planning twice in 2025.

The Definition of Done is the documented response to those incidents. Treat it as such.

## Attribution

Defers to [`output`](_output-rules.md). No AI / agent attribution in commits, PRs, or comments.
