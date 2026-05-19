---
name: rules-audit
description: "Cross-tier hygiene pass over the lessons-learned pipeline. Surfaces promotion-overdue Tier-1 entries, conflicts between Tier-2 rules, upstream-promotion candidates, and stale rules across all three tiers. Worklist output, never auto-acts."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write
argument-hint: "[--phase 1|2|3|4|all] [--repo <path>]"
---

# Rules Audit

This skill is the **meta-curation** layer of the rules pipeline. The per-tier skills ([skill:lessons-learned] for Tier 1 capture, [skill:distill-lessons] for Tier 1 → Tier 2 promotion) each handle a single transition. This skill owns the **health of the system as a whole**: what's overdue, what's stale, what conflicts, what's ready to promote upstream.

It produces **worklists for human review** — never auto-acts. Every output is a decision the user makes, not an action the skill takes.

## When to run

Two triggers:

1. **On-demand** — `/rules-audit` (or via [skill:wrap-up]'s 60-day nudge).
2. **Project events** — after a significant LESSONS.md import, before a quarterly retrospective, when starting work on a long-untouched repo.

The audit is read-mostly and idempotent. Re-running it does no harm.

## What the audit covers

The audit runs four phases in order. Each phase produces a section of the final worklist; phases are independent and can be invoked individually with `--phase`.

### Phase 1 — Tier 1 hygiene (`<repo>/LESSONS.md`)

Read every entry in `LESSONS.md`. For each, check:

| Check | Worklist label | Action |
|---|---|---|
| Entry has no link | **Evidence missing** | Find the link or remove the entry |
| Phrased as advice ("be careful", "consider") | **Phrasing weak** | Rewrite as imperative rule, or drop |
| Recurrence = 1 AND >6 months old | **Stale candidate** | Archive (move to `LESSONS-archive.md`) or justify keeping |
| Eligible for promotion (per [skill:distill-lessons] thresholds) but not yet promoted | **Promotion overdue** | Run [skill:distill-lessons] for this entry |
| Marked `**Conflicts-with:**` and not resolved | **Unresolved conflict** | Resolve before any further updates to either entry |

### Phase 2 — Tier 2 hygiene (`<repo>/.claude/rules/*.md`)

Read every `.claude/rules/<topic>.md` file. For each rule:

| Check | Worklist label | Action |
|---|---|---|
| Two rules in the same topic file contradict | **Cross-rule conflict** | Resolve one wins (no soft coexistence) |
| Rule has no Tier-1 entries referencing it in 6+ months | **Possibly load-bearing? Possibly stale?** | Verify: is it still being violated, or has the codebase moved past it? |
| Rule is marked code-checkable but no enforcement (lint, pre-commit, CI test) exists | **Hardening overdue** | Add the enforcement, or downgrade to "human-checkable only" |
| Rule has no `**Evidence:**` link back to a Tier-1 entry | **Provenance broken** | Add the link or recreate the entry |

### Phase 3 — Cross-tier audit (the unique value)

This phase is what justifies a single audit skill instead of three per-tier skills.

| Check | Worklist label | Action |
|---|---|---|
| Tier-2 rule appears in 2+ projects (compare `.claude/rules/` across known repos) | **Ready for upstream PR** | Cite both repos' evidence; open PR against `claude-configs-public` `_<topic>-rules.md` |
| Tier-3 (org) rule conflicts with newer Tier-2 evidence | **Upstream needs updating** | Open PR against `claude-configs-public` to amend the org rule |
| Tier-3 rule has no Tier-1/Tier-2 evidence anywhere across known repos | **Stale upstream rule** | Surface for review; org rule may have outlived its evidence |

For Phase 3 to work, the audit needs a list of "known repos" to scan. Default behavior: run only on the current repo's Tier 1+2; flag Phase 3 as "manual cross-repo step required" with a printable checklist of repos to check. If the user supplies `--repos <path1>,<path2>,...`, scan those too.

### Phase 4 — Coverage

| Check | Worklist label | Action |
|---|---|---|
| Topic with ≥5 Tier-1 entries but no Tier-2 rule file yet | **Missing topic file** | Create `.claude/rules/<topic>.md` and start promoting the eligible entries |
| Tier-2 rule not loaded by [skill:code-review] (no path-form reference under `.claude/rules/`) | **Wiring gap** | Verify [skill:code-review]'s glob covers the file location |
| LESSONS.md hasn't been touched in 90+ days but the repo has had commits in that window | **Capture gap** | Likely indicates [skill:lessons-learned] isn't being invoked — flag for retrospective |

## Output format

A single Markdown report, written to `<repo>/RULES-AUDIT-YYYY-MM-DD.md`. The report has one section per phase, with each finding numbered for traceability:

```markdown
# Rules Audit — <repo-name> — YYYY-MM-DD

**Tier 1 entries scanned:** N
**Tier 2 rule files scanned:** M
**Cross-repo scope:** <current repo only | repos: a, b, c>

## Phase 1 — Tier 1 Hygiene

### 1.1 Promotion overdue (3 findings)

- **2026-03-15 — Cast FEC IDs as StringType**
  Recurrence: 4. Eligible since 2026-04-22. Run: `distill-lessons --entry "2026-03-15"`

(...)

## Phase 2 — Tier 2 Hygiene

(...)

## Phase 3 — Cross-Tier

(...)

## Phase 4 — Coverage

(...)

## Suggested order of action

1. Resolve conflicts (1.5, 2.1) — they block other promotions
2. Promote overdue Tier-1 entries (1.1) — the main backlog
3. Scan cross-repo for Tier-3 candidates (3.1) — quarterly cadence
4. (...)
```

After writing the report, **update the audit timestamp** in `LESSONS.md`'s header:

```markdown
- **Last audit:** YYYY-MM-DD (report: `RULES-AUDIT-YYYY-MM-DD.md`)
```

## Cadence and the wrap-up nudge

[skill:wrap-up] reads the `**Last audit:**` line in `LESSONS.md`. If the date is more than 60 days ago, it prints a single-line nudge:

> Heads up: rules-audit hasn't run in N days. Consider `/rules-audit` before the next session.

The nudge is **not a blocker**. Hygiene-as-theater is worse than no hygiene. The user decides whether to run the audit; the nudge just ensures the question gets asked.

## What this skill does NOT do

- **It doesn't promote entries.** That's [skill:distill-lessons], invoked one entry at a time.
- **It doesn't capture new lessons.** That's [skill:lessons-learned].
- **It doesn't open upstream PRs.** Phase 3 surfaces candidates; the human opens the PR with cited evidence.
- **It doesn't enforce hardening.** Phase 2 surfaces "code-checkable rule with no enforcement"; the human writes the lint rule / pre-commit / CI test as a follow-up ticket.
- **It doesn't auto-archive stale entries.** Phase 1 surfaces stale candidates; the human decides whether to archive.

The discipline is: surface, never auto-act. Decisions about what stays, what goes, and what gets promoted are judgment calls — the skill's job is to make sure the question gets asked.

## Anti-patterns

- **Running the audit and not acting on it.** The report is worthless if it accumulates. If the worklist is consistently ignored, raise the frequency or shrink the scope.
- **Treating worklist items as automation candidates.** They're judgment calls, not mechanical tasks. Auto-archiving stale entries silently is exactly the failure mode that killed the previous attempt at rule curation.
- **Skipping Phase 3 because it's manual.** Cross-repo promotion is the highest-leverage output of this whole pipeline — that's where org-wide standards actually evolve. If you're not doing Phase 3, you're not getting the value.
- **Editing entries during the audit.** The audit is read-only with respect to rules. Findings get written to the audit report; rule edits happen via [skill:lessons-learned] or [skill:distill-lessons] in a separate pass.

## Attribution

Defers to [rule:output]. No AI / agent attribution in audit reports, commits, or comments.
