---
name: distill-lessons
description: "Promote eligible Tier-1 lessons (from LESSONS.md) into Tier-2 project rules at <repo>/.claude/rules/<topic>.md. Single-rule-at-a-time, with conflict gate and human wording confirmation."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write
argument-hint: "[--all | --entry <date-or-title>]"
---

# Distill Lessons (Tier 1 → Tier 2 promotion)

This skill promotes a single eligible Tier-1 entry from `LESSONS.md` into a Tier-2 project rule at `<repo>/.claude/rules/<topic>.md`. It is intentionally **one rule at a time** — distillation is a high-stakes act that benefits from focused attention, not batch processing.

For the source ledger spec, see [`lessons-learned`](../lessons-learned/SKILL.md). For cross-tier hygiene and finding what to promote, see [`rules-audit`](../rules-audit/SKILL.md).

## When to use

Run after [`rules-audit`](../rules-audit/SKILL.md) surfaces a "promotion overdue" worklist, or directly when you know a specific entry is ready (e.g., a 🔴 Critical finding logged once that needs immediate codification).

Do **not** use this skill for:
- Promoting from Tier 2 → Tier 3 — that's always a human PR with cited evidence
- Capturing a new lesson — that's [`lessons-learned`](../lessons-learned/SKILL.md)
- Auditing the system as a whole — that's [`rules-audit`](../rules-audit/SKILL.md)

## Eligibility

An entry is eligible when **any** of:

| Trigger | Threshold |
|---|---|
| Default recurrence | ≥ 3 |
| Production incident in the entry's history | ≥ 2 |
| Critical-severity finding (security, data loss) | ≥ 1 |
| Explicit reviewer flag (`**Promotion-requested:**`) | always |

Eligibility is informational on the Tier-1 entry itself — this skill verifies it before proceeding.

## Workflow

### 1. Identify the entry

If invoked with `--entry <date-or-title>`, jump to step 2.
If invoked with `--all`, iterate over every eligible entry one at a time (do not batch-promote).
If invoked with no args, ask the user which entry to promote.

### 2. Verify eligibility

Read the entry from `LESSONS.md`. Confirm the trigger threshold is met and the entry is not already marked `**Promoted:**`. If the entry is ineligible, stop and explain why.

### 3. Choose the target file

Determine the appropriate `<topic>.md` under `<repo>/.claude/rules/`:

- Read the entry's content and identify the topic (e.g., "data-types", "idempotency", "auth", "spark-write-modes").
- If a matching file exists, that's the target.
- If no matching file exists, propose a name to the user before creating it. **Do not invent a topic file silently** — topic taxonomy is a long-lived design choice.
- The `.claude/rules/` directory is created if missing.

### 4. Conflict gate (mandatory)

Read the existing rules in the target file (and adjacent `.claude/rules/*.md` files if they're related). If the new rule contradicts an existing rule:

1. **Stop. Do not write.**
2. Surface both rules to the user side-by-side with their evidence.
3. Ask the user to resolve: amend one, retire one, or merge them. Soft coexistence is rejected.
4. Only proceed once the conflict is explicitly resolved.

This gate exists because contradictory rule files are worse than missing rules — they make every review a judgment call rather than a check.

### 5. Draft the rule (with user confirmation)

Distill the Tier-1 entry into a Tier-2 rule entry:

```markdown
## <imperative-one-liner>

**Why:** <one paragraph — the underlying invariant; cite the original incident if any>

**How to apply:** <when this rule fires; what the violating pattern looks like; what the compliant pattern looks like>

**Code-checkable?** <yes / no — and if yes, name the lint rule, pre-commit check, or CI test that would enforce it (or note "not yet — TODO")>

**Evidence:** [LESSONS.md entry: `<date> — <title>`](../../LESSONS.md#<anchor>)
```

**Show the draft to the user before writing.** Distillation is the moment when phrasing matters most — the rule will be read by every future reviewer in this repo. Iterate on wording with the user before committing.

### 6. Write the rule

Once the user confirms wording:

1. Append the rule to the chosen `<topic>.md` (or create the file with a header if new).
2. Update the Tier-1 entry in `LESSONS.md` with a `**Promoted:**` line referencing the target file and today's date.
3. Do **not** delete the Tier-1 entry. Promoted entries stay in the ledger as the audit trail.

### 7. Suggest enforcement

If the rule is code-checkable, propose the enforcement mechanism (lint rule config, pre-commit hook, CI test) as a follow-up ticket. **Do not write the enforcement here** — that's a separate piece of work with its own review.

If the rule is not code-checkable, ensure it's wired into [`code-review`](../code-review/SKILL.md) by updating the project's `.claude/rules/<topic>.md` (which `code-review` reads at the top of every review).

### 8. Commit

One commit per promotion:

```
task: Promote LESSONS.md entry "<title>" to .claude/rules/<topic>.md

Refs: <ticket-from-original-incident-if-any>
```

If the original entry references a ticket, link it. If not, the promotion itself is exempt from ticket creation (it's a meta-action on existing tracked work).

## Topic file structure

A `.claude/rules/<topic>.md` file:

```markdown
# <Topic> Rules

Project-local Tier-2 rules for `<topic>`. Distilled from `LESSONS.md` entries by [`distill-lessons`](../distill-lessons/SKILL.md). Loaded by [`code-review`](../code-review/SKILL.md) at the start of every review.

For the promotion process, see [`distill-lessons`](../distill-lessons/SKILL.md). For the source ledger, see [`lessons-learned`](../lessons-learned/SKILL.md).

---

## <rule 1>

(rule body — see step 5 format)

## <rule 2>

(...)
```

## Anti-patterns

- **Batch promotion.** Promoting 5 entries in one pass produces sloppy phrasing on at least 2 of them. One at a time.
- **Inventing topic files.** Topic taxonomy is a project-design choice. Always confirm the topic name with the user before creating a new file.
- **Skipping the conflict gate.** "I'll resolve it later" turns into "we have two contradictory rules now" within a quarter.
- **Deleting the Tier-1 entry after promotion.** The Tier-1 entry is the evidence; without it, the Tier-2 rule has no audit trail.
- **Promoting an entry that's only ever appeared in one repo when the rule is generic.** That entry should keep accumulating evidence (or get promoted directly to Tier 3 via human PR with `claude-configs-public` as the destination).

## Attribution

Defers to [`output`](../_output-rules.md). No AI / agent attribution in commits, ledger updates, or rule entries.
