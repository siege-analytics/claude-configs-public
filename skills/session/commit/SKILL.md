---
name: commit
description: Create well-structured git commits with descriptive messages that link to tickets and explain the why
---

# Instructions

1. Review what has changed
   1. Run `git status` to see all modified, added, and untracked files
   2. Run `git diff` to review the actual changes (staged and unstaged)
   3. Read recent commit history (`git log --oneline -10`) to match the repository's existing style
2. Stage changes thoughtfully
   1. Group related changes into a single commit
   2. Separate unrelated changes into distinct commits
   3. Stage specific files by name -- avoid `git add -A` or `git add .` which can accidentally include secrets, build artifacts, or large binaries
   4. Never commit `.env`, credentials, tokens, or other sensitive files
3. Write the commit message (see Message structure below)
4. Verify after committing
   1. Run `git log -1` to confirm the message looks correct
   2. Run `git status` to confirm nothing was missed or accidentally included

# Commit philosophy

A commit is a unit of meaning, not a unit of time. Each commit should represent one coherent change that can be understood, reviewed, and if necessary reverted on its own.

**One commit should do one thing.** If you find yourself writing "and" in the subject line, consider whether it should be two commits.

**Commit the why, not the what.** The diff shows what changed. The message explains why it changed. Code that is obvious from the diff does not need narration. Decisions, tradeoffs, and constraints do.

**Commit often.** Small, frequent commits are easier to review, bisect, and revert than large, infrequent ones. When in doubt, commit more granularly.

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

1. **Lead with a type prefix** matching the ticket taxonomy:
   - `bugfix:` -- correcting behaviour that deviates from intent
   - `feature:` -- adding new behaviour
   - `task:` -- refactoring, cleanup, infrastructure, docs, tests, CI
2. **Use imperative mood** -- "Add validation" not "Added validation" or "Adds validation"
3. **Keep it under 72 characters** -- this is the display width of most git tools
4. **Be specific** -- "bugfix: Fix crash" is useless. "bugfix: Handle None committee_id in silver transform" is useful
5. **No trailing period**

### Examples

```
bugfix: Preserve leading zeros in committee_id during silver transform
feature: Add geographic crosswalk time series to platinum tier
task: Split census module into census/ subpackage
task: Add round-trip test for zero-padded FEC identifiers
bugfix: Use string type for all FEC identifier columns in Delta schema
feature: Allow Rundeck jobs to specify S3 output prefix
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

The footer links the commit to tickets and related context.

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
git commit -m "bugfix: Preserve leading zeros in committee_id during silver transform"

git add src/census/api.py src/census/__init__.py
git commit -m "task: Split census module into census/ subpackage"
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

- [ ] Changes are grouped into logical, single-purpose commits
- [ ] Files are staged by name, not with `git add -A`
- [ ] No sensitive files (secrets, credentials, keys) are staged
- [ ] Subject line: type prefix, imperative mood, under 72 chars, specific
- [ ] Body explains the why (if the change is non-trivial)
- [ ] Footer references the relevant ticket(s)
- [ ] No AI/agent attribution anywhere in the commit message (no Co-Authored-By, no "Made with", no tool mentions)
- [ ] Verified with `git log -1` and `git status` after committing
