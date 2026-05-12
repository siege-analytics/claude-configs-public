---
name: commit
description: Create git commits with descriptive messages that link to tickets and explain the why. Enforces ticket references.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash
---

# Instructions

0. **Verify-before-execute** — emit the verification block from [rule:verify-before-execute] for the commit you are about to make. The Standards line must include `[skill:commit]` and the relevant project/language rules; the Intent line must summarize what the commit accomplishes; the Evidence line (if this is a fix) must reference same-turn tool calls demonstrating the bug. Skipping requires `[verify-skip: <reason>]` — and `[verify-skip]` does NOT exempt the commit from any later step in this skill.

0.5. **Branch guard — verify you are NOT on a protected branch**
   1. Run `git branch --show-current` to get the current branch name
   2. If the branch is `main`, `master`, `develop`, `dev`, `development`, `staging`, `next`, or `integration` → **STOP**
   3. Inform the user: "You are on `{branch}`. Commits should go on a feature branch, not directly on a protected branch."
   4. Offer to create a feature branch (use the branch skill) before proceeding
   5. Only proceed if the user explicitly overrides: "Commit directly to {branch}"
   6. If the user overrides, add `[direct-commit]` to the commit body as an audit trail
1. Review what has changed
   1. Run `git status` to see all modified, added, and untracked files
   2. Run `git diff` to review the actual changes (staged and unstaged)
   3. Read recent commit history (`git log --oneline -10`) to match the repository's existing style
2. Stage changes thoughtfully
   1. Group related changes into a single commit
   2. Separate unrelated changes into distinct commits
   3. Stage specific files by name -- avoid `git add -A` or `git add .` which can accidentally include secrets, build artifacts, or large binaries
   4. Never commit `.env`, credentials, tokens, or other sensitive files
3. **Run code review on the staged diff** (see Pre-review gate below)
   1. Invoke [skill:code-review] against `git diff --cached`
   2. Resolve every Blocker; resolve Majors or document why they're being deferred
   3. If the user explicitly overrides, mark the commit with `[review-skip]`
4. **Check for a ticket reference** (see Ticket enforcement below)
   1. If no ticket exists for this work, stop and create one first
   2. If the user explicitly overrides, mark the commit with `[no-ticket]`
5. Write the commit message (see Message structure below)
6. **Verify ticket reference is in the footer**
7. Verify after committing
   1. Run `git log -1` to confirm the message looks correct
   2. Run `git status` to confirm nothing was missed or accidentally included

# Commit philosophy

A commit is a unit of meaning, not a unit of time. Each commit should represent one coherent change that can be understood, reviewed, and if necessary reverted on its own.

**One commit should do one thing.** If you find yourself writing "and" in the subject line, consider whether it should be two commits.

**Commit the why, not the what.** The diff shows what changed. The message explains why it changed. Code that is obvious from the diff does not need narration. Decisions, tradeoffs, and constraints do.

**Commit often.** Small, frequent commits are easier to review, bisect, and revert than large, infrequent ones. When in doubt, commit more granularly.

# Pre-review gate

**Every commit gets a code-review pass before it lands.** This is the operationalization of criterion (a) of [rule:definition-of-done] at the pre-commit transition — not just at PR-open.

## What runs

After staging and before writing the message, invoke [skill:code-review] with the staged diff as input:

```bash
git diff --cached
```

The code-review skill walks its standard six layers (correctness, security, data integrity, performance, error handling, readability) and reports findings with severity.

## Decision tree

```
Code-review finished?
├── No Blockers, no unresolved Majors? → Proceed to ticket check
├── Blockers exist? → STOP. Fix and re-stage. Do not commit.
├── Majors exist?
│   ├── Fix in this commit? → Re-stage, re-review
│   ├── Defer to a follow-up ticket? → Create the ticket NOW, link in commit body, then commit
│   └── User explicitly overrides? → Add [review-skip] to commit body with rationale
└── Only Minors / Nits? → Proceed; address inline in the same commit if cheap
```

## Override syntax

Override is for cases where the review surfaced a real finding but the right place to fix it is somewhere else (different commit, different repo, different sprint) — not for skipping the review itself. The review still runs; the override only acknowledges deferred Majors.

```
[review-skip] Performance finding in legacy module deferred to ELE-512 — out of scope for this commit.
```

If you find yourself reaching for `[review-skip]` more than once a week, the threshold is wrong somewhere — either the review is flagging too aggressively, or the work is being scoped too broadly. Surface it in retrospective rather than normalizing the override.

## Why pre-commit, not just pre-PR

Catching findings at commit time is cheaper than catching them at PR time:
- The change is fresh in your head — context-switch cost is zero.
- The diff is small — one commit's worth of code, not a PR's worth.
- No collaborators are blocked — no one is waiting on the PR.
- Findings turn into the next commit instead of a force-push.

The pre-PR review (in [skill:create-pr]) still runs — it's a second pass over the cumulative diff and catches things that only emerge across multiple commits (architectural drift, accidental scope creep). The two reviews are complementary, not redundant.

# Ticket enforcement

**Every commit must reference a ticket.** If the work is committable, it is ticketable. This is not optional -- it is the default behaviour.

## Before creating any commit

Scan the planned commit message for ticket patterns. If no ticket reference is found, **stop and ask**.

## If no ticket exists for this work

1. Inform the user: "This work doesn't have a ticket. If it's committable, it's ticketable."
2. Offer to create a ticket first (use the create-ticket skill)
3. Only proceed with the commit after a ticket exists or the user explicitly overrides

## Decision tree

```
Commit ready?
├── Has ticket reference in footer? → Proceed with commit
├── No ticket reference?
│   ├── Ticket exists but not referenced? → Add reference, then commit
│   ├── No ticket exists?
│   │   ├── User wants to create ticket? → Create ticket, then commit
│   │   └── User explicitly overrides? → Commit with [no-ticket] in body
│   └── Trivial change (typo, formatting)? → Ask user if override is appropriate
└── Ambiguous? → Ask user
```

## Override syntax

When the user explicitly says to skip the ticket requirement:

```
User: "Just commit it, no ticket needed"
User: "Override the ticket check"
User: "This is too trivial for a ticket"
```

In these cases, add to the commit body:

```
[no-ticket] Trivial formatting change, per operator override.
```

This should be rare -- the goal is to make ticketless commits uncomfortable, not impossible.

# Message structure

## Format

```
{type}: {subject line}

{body}

{footer}
```

## Subject line

The subject line is the most important part. It appears in `git log --oneline`, blame annotations, PR merge lists, and notification emails.

### Rules

1. **Lead with a type prefix** matching the ticket and branch taxonomy:
   - `bugfix:` -- correcting behaviour that deviates from intent
   - `feature:` -- adding new behaviour
   - `task:` -- refactoring, cleanup, infrastructure, docs, tests, CI
   - `chore:` -- routine maintenance (dependency bumps, config, formatting)
   - `hotfix:` -- urgent production fix
2. **Use imperative mood** -- "Add validation" not "Added validation" or "Adds validation"
3. **Keep it under 72 characters** -- this is the display width of most git tools
4. **Be specific** -- "bugfix: Fix crash" is useless. "bugfix: Handle None committee_id in silver transform" is useful
5. **No trailing period**

### Synonyms

When reading existing commits, recognise these as equivalent:

| Canonical | Synonyms |
|-----------|----------|
| `bugfix:` | `fix:`, `bug:`, `patch:` |
| `feature:` | `feat:`, `enhancement:` |
| `task:` | `refactor:`, `tech:`, `infra:`, `docs:`, `test:` |
| `chore:` | `maintenance:`, `deps:`, `ci:` |
| `hotfix:` | `emergency:`, `critical:` |

When creating new commits, use the canonical type.

### Examples

```
bugfix: Preserve leading zeros in committee_id during silver transform
feature: Add geographic crosswalk time series to platinum tier
task: Split census module into census/ subpackage
task: Add round-trip test for zero-padded FEC identifiers
chore: Bump pyspark to 4.1.0
hotfix: Remove Sedona JAR reference that crashes executor pods
```

## Body

The body is optional for trivial changes but expected for anything non-obvious. Wrap lines at 72 characters.

### What to include

- **Why** this change was made (the motivation, not a restatement of the diff)
- **What tradeoff** was chosen if alternatives existed
- **What is not obvious** from the diff alone (e.g., a subtle side effect, a constraint from an external system)
- **What was intentionally left out** if the scope was deliberately limited

### What to omit

- Play-by-play of the diff ("Changed line 48 from int to str")
- Filler ("This commit updates the code to...")
- Attribution to tools or assistants (see Attribution policy below)

### Example body

```
The bronze-to-silver transform was casting committee_id to integer,
which stripped leading zeros. FEC identifiers use zero-padding to
encode registration era, so C00000547 and C0000547 are distinct
entities.

Changed the Delta schema to use StringType for all FEC identifier
columns (committee_id, candidate_id, report_id). This is consistent
with how the FEC bulk download formats them.

Alternative considered: zero-pad after the fact using lpad(). Rejected
because it assumes a fixed width, which varies by identifier type.
```

## Footer

The footer links the commit to tickets and related context. **This is mandatory** (see Ticket enforcement above).

### Ticket references

Reference tickets so that the ticketing platform can auto-link:

```
Refs: #42
Fixes: #42
Closes: #42
Part-of: #38
```

- `Fixes` / `Closes` -- use when this commit fully resolves the ticket
- `Refs` -- use when this commit is related but does not resolve the ticket
- `Part-of` -- use when this commit is one of several that address a ticket

For cross-repo references:
```
Fixes: electinfo/enterprise#42
Refs: siege-analytics/siege_utilities#335
```

### Ticket reference patterns by platform

| Platform | Patterns |
|----------|----------|
| GitHub | `#42`, `owner/repo#42`, `GH-42` |
| GitLab | `#42`, `group/project#42` |
| Jira | `PROJ-42`, `ELE-42` |
| Linear | `ELE-42`, `SU-42` |

### Breaking changes

If the commit changes a public API, CLI interface, or data format:

```
BREAKING: silver table schema changed -- committee_id is now StringType.
Downstream consumers expecting IntegerType will need to update.
```

# Staging patterns

## One logical change, multiple files

Stage all related files together:

```bash
git add src/transforms/silver.py tests/test_silver.py docs/schema.md
git commit
```

## Multiple logical changes in the working tree

Stage and commit each change separately:

```bash
git add src/transforms/silver.py tests/test_silver.py
git commit -m "bugfix: Preserve leading zeros in committee_id during silver transform

Refs: #42"

git add src/census/api.py src/census/__init__.py
git commit -m "task: Split census module into census/ subpackage

Part-of: #335"
```

## Fixing a mistake in the previous commit

If you need to amend (only if the commit has NOT been pushed):

```bash
git add forgotten_file.py
git commit --amend
```

If the commit has already been pushed, create a new commit instead. Never force-push to shared branches.

# Sensitive files

Never commit these:

- `.env`, `.env.local`, `.env.production`
- `credentials.json`, `service-account.json`
- `*.pem`, `*.key`, private SSH keys
- API tokens, passwords, secrets of any kind
- Large binary files (datasets, images, compiled artifacts) unless the repo is designed for them

If a sensitive file is staged, unstage it:

```bash
git reset HEAD .env
```

If it was already committed, remove it from history and rotate the credential immediately.

# Attribution policy

**NEVER** include AI or agent attribution in commit messages. This includes:
- No `Co-Authored-By: Claude`, `Co-Authored-By: Cursor`, `Co-Authored-By: Copilot`, or similar lines
- No "Generated with Claude Code", "Made with Cursor", "Built with Codex", or any AI tool mentions
- No `🤖`, `[bot]`, or other markers that signal AI involvement
- No attribution to any AI assistant, code generation tool, or agent framework
- This applies to the subject line, body, and footer — every part of the commit message

# Checklist

- [ ] **[rule:verify-before-execute] block emitted** — Standards, Intent, and (for fixes) same-turn Evidence
- [ ] **Not on a protected branch** (main, develop, etc.) — or user explicitly overrode with `[direct-commit]`
- [ ] Changes are grouped into logical, single-purpose commits
- [ ] Files are staged by name, not with `git add -A`
- [ ] No sensitive files (secrets, credentials, keys) are staged
- [ ] **[skill:code-review] ran on the staged diff** — Blockers resolved, Majors addressed or deferred-with-ticket, or `[review-skip]` documented in commit body
- [ ] Subject line: type prefix, imperative mood, under 72 chars, specific
- [ ] Body explains the why (if the change is non-trivial)
- [ ] **Footer references the relevant ticket(s)** — mandatory unless user overrides with `[no-ticket]`
- [ ] Ticket exists for this work (if committable, it's ticketable)
- [ ] No AI/agent attribution anywhere in the commit message
- [ ] Verified with `git log -1` and `git status` after committing
