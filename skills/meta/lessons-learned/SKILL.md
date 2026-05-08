---
name: lessons-learned
description: "Capture recurring code-review findings, bot comments, and incident lessons into a per-repo LESSONS.md ledger (Tier 1 of the rules pipeline). Other skills call this when they detect a pattern worth recording."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write
---

# Lessons Learned (Tier 1 Ledger)

This skill owns the **Tier 1** raw-observations layer of the rules pipeline. Findings from CodeRabbit, human reviewers, production incidents, and self-review get appended here as evidence. They later get promoted to Tier 2 (project rules) by [skill:distill-lessons], and from there to Tier 3 (org-wide `_*-rules.md` in claude-configs-public) by human PR.

## The three tiers

| Tier | Lives in | Owns | Promotion gate |
|---|---|---|---|
| **1 — Ledger** | `<repo>/LESSONS.md` | This skill | recurrence ≥ 3, or 1 production incident, or explicit reviewer flag → Tier 2 |
| **2 — Project rules** | `<repo>/.claude/rules/<topic>.md` | [skill:distill-lessons] | appears in 2+ projects, or is language/framework-level → Tier 3 |
| **3 — Org rules** | `claude-configs-public/skills/_*-rules.md` | Human PR with cited evidence | (top of pipeline) |

## When to use

Call this skill when a finding is **a recurring pattern**, not a one-off. Other skills invoke it as a final step:

- [skill:code-review] — when reviewing surfaces a finding that "we keep getting this"
- [skill:coderabbit-response] — when a CodeRabbit thread maps to an existing or new pattern
- [skill:pr-comments] — when a human reviewer flags a recurring concern
- [skill:wrap-up] — at session end, sweep for findings worth logging

Do **not** call this skill for:
- One-off bugs with no pattern (use the commit message + ticket)
- Style preferences with no underlying invariant (use `.editorconfig`, lint rules)
- Things already covered by an existing rule (just bump the recurrence counter)

## The discipline rules

Three non-negotiables for every entry:

### 1. Every entry has a link

PR comment URL, CodeRabbit thread ID, incident ticket, commit SHA, or production alert ID. **No link = opinion, not lesson.** The link is the evidence trail.

### 2. Phrased as a rule, not advice

| ❌ Advice (rejected) | ✅ Rule (accepted) |
|---|---|
| "Be careful with FEC identifiers" | "Cast FEC identifiers as StringType, never IntegerType" |
| "Watch out for null handling" | "Never call `.dropna()` without first logging the row count being dropped" |
| "Consider idempotency" | "Use `merge` (not `append`) for any Delta write that might be retried" |

If you can't write the rule as "do X" or "don't do X", it's not a rule yet — leave it in the commit message or ticket comment until the pattern crystallizes.

### 3. Recurrence counter, not duplicate entries

When the same pattern hits again, **bump the counter and add the new link** to the existing entry. Do not create a second entry. This is what surfaces recurring patterns for promotion.

## Entry format

Append entries to `LESSONS.md` at the repo root (create the file from the template if missing). Each entry follows this shape:

```markdown
## YYYY-MM-DD — <one-line title in rule form>

- **Source:** <link or reference> (`<source type>: <url-or-id>`)
- **Rule (draft):** <imperative one-liner — "do X" / "don't do X">
- **Why:** <one or two sentences — the underlying invariant or incident>
- **Recurrence:** 1
```

When the same pattern recurs:

```markdown
- **Recurrence:** 3
- **Recurrences logged:**
  - 2026-05-08: <link>
  - 2026-06-12: <link>
  - 2026-07-03: <link>
```

When promoted to Tier 2:

```markdown
- **Promoted:** `.claude/rules/<topic>.md` on YYYY-MM-DD by [skill:distill-lessons]
```

Promoted entries stay in `LESSONS.md` (do not delete) — they are the audit trail showing why the Tier-2 rule exists.

## Workflow

### A. Adding a new entry

1. **Read** the most recent ~30 entries in `LESSONS.md` (or the whole file if small) to check for an existing entry on the same pattern.
2. **If a matching entry exists:** bump `Recurrence` and append the new link under `Recurrences logged`. Stop.
3. **If no match:** apply the discipline rules.
   - Confirm there is a link.
   - Rewrite the finding as a rule (imperative, falsifiable).
   - Confirm a `Why` exists in one or two sentences.
4. **Append** the entry to `LESSONS.md`. Do not edit the file's header (timestamps, audit cadence) — that's owned by [skill:rules-audit].
5. **Tell the user:** brief one-liner — "Logged: `<title>` (recurrence N). Will be eligible for Tier-2 promotion at recurrence ≥ 3."

### B. Bootstrapping `LESSONS.md`

If `LESSONS.md` doesn't exist in the repo:

1. Copy `template/LESSONS.md` from this skill to the repo root.
2. Fill in the repo name in the header.
3. Initialize the audit timestamp with today's date.
4. Commit it as a separate commit before adding the first entry: `task: Initialize lessons-learned ledger`.

## Promotion eligibility (informational)

Entries become eligible for Tier-2 promotion when **any** of the following are true:

- Recurrence ≥ 3 (default threshold, configurable per repo)
- Recurrence ≥ 2 if the pattern caused any production incident
- Recurrence ≥ 1 if the original finding was Critical (security, data loss)
- Explicit reviewer flag: any entry tagged `**Promotion-requested:** <reviewer-handle>`

This skill does not perform the promotion — that's [skill:distill-lessons]. This skill only logs and surfaces eligibility.

## Conflict with existing entries

If a new finding contradicts an existing entry (e.g., the new lesson says "do X," the old one said "don't do X"):

1. **Do not silently coexist.** Flag the conflict in the new entry under a `**Conflicts-with:**` line referencing the old entry.
2. **Surface to the user immediately.** A contradiction means one of the entries is wrong — either the context changed (note when) or one was misphrased (fix it).
3. **Resolve before bumping counters on either.** Conflicting entries left in place erode the ledger's authority.

## Anti-patterns

- **Logging every CodeRabbit nit.** Recurrence threshold matters — if you log every 🔵 comment, the ledger becomes noise and real patterns disappear.
- **Logging without a link.** Opinions are not lessons. The link is the evidence.
- **Phrasing as advice.** "Be careful" entries don't fire because they're not falsifiable. Rewrite as rules or drop.
- **Creating duplicate entries.** Always check for an existing entry first; bump the counter rather than re-logging.
- **Editing the audit-timestamp header.** That's [skill:rules-audit]'s territory.

## Attribution

Defers to [rule:output]. No AI / agent attribution in `LESSONS.md` entries, commits, or comments.
