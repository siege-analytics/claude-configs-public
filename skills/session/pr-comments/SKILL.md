---
name: pr-comments
description: Read, triage, and respond to PR comments. Reviews automated feedback, detects handoff signals, and writes structured replies.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash
argument-hint: "[PR-number]"
---

# Instructions

1. Determine the context
   1. Identify the PR number and repository
   2. Read the PR description and diff to understand the change
   3. Fetch existing comments to understand the conversation so far
   4. Identify the audience: human reviewer, automated tool, bot, or CI system
2. Read and triage all existing comments
   1. Separate human comments from automated comments (linters, CI bots, review tools)
   2. Flag actionable items vs informational noise
   3. Identify any "agent ready", "ready for review", or similar handoff signals
   4. Surface blocking feedback (requested changes, failing checks, merge conflicts)
3. Respond or act based on what was found (see workflows below)
4. After acting, re-check the PR state to confirm the response landed correctly

# Comment philosophy

PR comments are a conversation, not a monologue. Every comment should either **move the PR closer to merge** or **document a decision** for future readers. Comments that restate the diff, add noise, or bikeshed formatting waste the reviewer's time.

**Match the register of the commenter.** A terse reviewer gets terse replies. A detailed reviewer gets detailed replies. A bot gets no reply unless action is needed.

**Never argue in comments.** If you disagree with a review, state your reasoning once with evidence (a link, a test result, a design doc reference). If the reviewer pushes back again, escalate to the user — don't engage in a back-and-forth in the comment thread.

**Comments are permanent.** They appear in notification emails, search results, and audit trails. Write as if a stranger will read this comment six months from now trying to understand why a decision was made.

# Fetching PR comments

## GitHub

```bash
# All comments (issue-level)
gh api repos/{owner}/{repo}/issues/{number}/comments

# Review comments (inline on diff)
gh api repos/{owner}/{repo}/pulls/{number}/comments

# Reviews (approve/request changes/comment)
gh api repos/{owner}/{repo}/pulls/{number}/reviews

# PR checks and status
gh pr checks {number} --repo {owner}/{repo}

# Combined: full PR conversation
gh pr view {number} --repo {owner}/{repo} --comments
```

## GitLab

```bash
# MR notes (all comments)
glab api projects/{id}/merge_requests/{iid}/notes

# MR discussions (threaded)
glab api projects/{id}/merge_requests/{iid}/discussions
```

# Watching for signals

## Automated review tools

Automated reviewers (CodeRabbit, Copilot, SonarQube, Danger, custom bots) leave comments that fall into categories:

| Category | Action |
|----------|--------|
| **Blocking** — security vulnerability, failing test, lint error marked as error | Must fix before merge. Create a commit or respond with justification. |
| **Suggestion** — code improvement, style nit, refactor idea | Evaluate. Apply if it genuinely improves the code. Dismiss with reason if not. |
| **Informational** — coverage report, bundle size delta, dependency audit | Read and note. No response needed unless a threshold is breached. |
| **False positive** — tool misunderstands the code | Dismiss with a brief explanation so future readers know it was evaluated. |

### Identifying automated comments

Look for these markers:
- Username contains `bot`, `[bot]`, `app/`, or is a known tool (e.g., `github-actions`, `codecov`, `sonarcloud`, `coderabbitai`)
- Comment body contains badges, status icons, or structured reports
- Comment was posted within seconds of the PR being opened or a push event

### Responding to automated reviews

- **Do not reply to bots conversationally.** Bots don't read replies.
- **Do apply valid suggestions** by committing the fix and noting what was addressed.
- **Do dismiss invalid suggestions** using the platform's dismiss mechanism (resolve conversation, thumbs-down reaction, or a brief reply explaining why).

## Agent-ready and handoff signals

Watch for comments that signal a human is handing off to an agent or vice versa:

| Signal | Meaning |
|--------|---------|
| "agent ready", "ready for agent", "@agent" | Human is asking an agent to pick up work on this PR |
| "ready for review", "PTAL" (please take a look) | Author is asking for human review |
| "LGTM", "approved", ":shipit:" | Reviewer approves the change |
| "needs work", "request changes" | Reviewer wants modifications before merge |
| "blocked on X", "waiting for Y" | PR is stalled on a dependency |
| "WIP", "draft", "do not merge" | PR is not ready — do not act on it |

When an agent-ready signal is detected:
1. Read the full PR diff and description
2. Read all prior comments to understand what was requested
3. Determine what work the signal is requesting (fix review feedback, add tests, resolve conflicts, etc.)
4. Report findings to the user before acting

# Writing comments

## Replying to a human review

Structure your reply to make it easy for the reviewer to verify the fix:

```markdown
Fixed in {sha}. {Brief explanation of what changed and why this approach.}
```

If the reviewer's comment was a question rather than a request:

```markdown
{Direct answer to the question.}

{Supporting evidence: link to docs, test output, or code reference.}
```

If you disagree:

```markdown
I'd prefer to keep the current approach because {reason}.

{Evidence: link, benchmark, test result, or design doc reference.}

Happy to discuss further — let me know if you'd like to hop on a call or if there's a specific concern I'm not addressing.
```

## Leaving a review comment

When reviewing someone else's PR, structure feedback clearly:

### Severity prefixes

Use a prefix so the author knows what's blocking vs optional:

| Prefix | Meaning |
|--------|---------|
| `blocking:` | Must be resolved before merge |
| `suggestion:` | Would improve the code but not required |
| `question:` | Need clarification to continue review |
| `nit:` | Style/formatting, author's discretion |
| `note:` | Informational, no action needed |

### Example review comment

```markdown
blocking: This query builds the WHERE clause by string concatenation,
which is vulnerable to SQL injection if `district_id` comes from user input.

Use parameterised queries instead:
​```python
cursor.execute("SELECT * FROM districts WHERE id = %s", (district_id,))
​```

Refs: OWASP SQL Injection Prevention Cheat Sheet
```

## Inline vs top-level comments

- **Inline comments** (on specific lines): Use for feedback tied to a specific code location. Keep them focused on that line/block.
- **Top-level comments**: Use for cross-cutting feedback, overall architecture concerns, or summaries of multiple inline comments.

# Summarising PR state

When asked "what's happening on this PR" or when triaging a PR's comments, produce a structured summary:

```markdown
## PR #{number}: {title}

**Status**: {draft | open | approved | changes requested | merged | closed}
**Checks**: {all passing | N failing | pending}
**Last activity**: {date} by {who}

### Human feedback
- {Reviewer}: {summary of their comments and whether addressed}

### Automated feedback
- {Tool}: {N comments — M blocking, K suggestions, J informational}
- {Action needed}: {what still needs to be fixed}

### Signals
- {Any handoff signals detected}

### Next step
{What should happen next to move this PR toward merge}
```

# Platform-specific commands

## GitHub: posting comments

```bash
# Top-level comment
gh pr comment {number} --repo {owner}/{repo} --body "comment text"

# Reply to a review
gh api repos/{owner}/{repo}/pulls/{number}/reviews/{review_id}/comments \
  -f body="reply text"

# Resolve a conversation (dismiss a review thread)
# Note: GitHub doesn't have a CLI for this — use the web UI or GraphQL
```

## GitHub: submitting a review

```bash
# Approve
gh pr review {number} --repo {owner}/{repo} --approve --body "LGTM — clean implementation."

# Request changes
gh pr review {number} --repo {owner}/{repo} --request-changes --body "See inline comments."

# Comment-only review (no approve/reject)
gh pr review {number} --repo {owner}/{repo} --comment --body "A few suggestions, nothing blocking."
```

## GitLab: posting comments

```bash
# Top-level note
glab mr note {iid} --message "comment text"

# Reply to a discussion
glab api projects/{id}/merge_requests/{iid}/discussions/{discussion_id}/notes \
  -f body="reply text"
```

# Workflow: full PR comment triage

When invoked, run this workflow:

1. **Fetch** all comments, reviews, and checks
2. **Classify** each comment: human vs automated, blocking vs suggestion vs informational
3. **Identify** any unaddressed blocking feedback
4. **Detect** handoff signals (agent-ready, PTAL, LGTM, etc.)
5. **Report** the structured summary to the user
6. **Recommend** next action: fix blocking items, respond to questions, merge, or wait
7. **Feed the lessons-learned ledger** — for any human-reviewer comment that flags a recurring pattern (the reviewer says "again," "always," "we keep doing this," or you recognize the pattern from prior PRs), invoke [skill:lessons-learned] to log or bump the entry in `LESSONS.md`. Skip one-off bugs and pure style preferences.

# Attribution policy

**NEVER** include AI or agent attribution in PR comments, review comments, or review summaries. This includes:
- No "Generated with Claude Code", "Made with Cursor", "Built with Codex", or any AI tool mentions
- No `🤖`, `[bot]`, or other markers that signal AI involvement
- No attribution to any AI assistant, code generation tool, or agent framework
- This applies to inline comments, top-level comments, review bodies, and reply threads

# Checklist

- [ ] Read the PR description and diff before engaging with comments
- [ ] Fetched all comment types (issue comments, review comments, reviews, checks)
- [ ] Classified each comment: human vs automated, blocking vs suggestion vs informational
- [ ] Identified and surfaced any handoff or agent-ready signals
- [ ] Responded to blocking feedback with commits or justification
- [ ] Dismissed false positives with brief explanations
- [ ] Used severity prefixes (blocking/suggestion/question/nit/note) in review comments
- [ ] Matched the tone and register of the conversation
- [ ] Verified responses landed correctly (re-checked PR state)
- [ ] No AI/Claude attribution in any comment text
