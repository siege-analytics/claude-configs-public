---
name: close-ticket
description: Close a ticket with a summary comment documenting the solution, linked commits, and verification status
---

# Instructions

1. Identify the ticket to close
   1. The user may provide a ticket number, URL, or description
   2. If ambiguous, search recent tickets and confirm with the user
2. Detect the ticketing platform from repo context
   1. If `.git/config` has a `github.com` remote, use `gh` CLI
   2. If `.git/config` has a `gitlab.com` or self-hosted GitLab remote, use `glab` CLI or the GitLab API
   3. If the project uses Jira, Linear, or another system, ask the user which CLI or API to use
   4. Use existing authenticated CLI tools. Never store credentials in plaintext.
3. Review the ticket's full history before closing
   1. Read all comments to understand the arc of work
   2. Check that acceptance criteria are satisfied
   3. Identify all commits related to this ticket
4. Write a closing comment (see Closing comment below)
5. Close the ticket
6. Handle cross-platform sync if the ticket is dual-tracked

# Gathering commits

Before writing the closing comment, collect all commits related to the ticket.

```bash
# Search for commits mentioning the ticket number
git log --oneline --grep="#42"

# If the ticket spans a date range
git log --oneline --after="2026-03-01" --before="2026-03-31" --author="dheeraj"

# If work was on a feature branch
git log --oneline main..feature/fix-committee-ids
```

If commits span multiple repositories, gather from each:

```bash
git -C ~/git/electinfo/enterprise log --oneline --grep="#42"
git -C ~/git/siege-analytics/siege_utilities log --oneline --grep="#42"
```

# Closing comment

The closing comment is the most important comment on a ticket. It is the summary someone reads when they find this ticket six months from now trying to understand what happened. Write it well.

## Template

```markdown
## Resolution

One to three sentences: what was the problem, what was the fix, and why this
approach was chosen over alternatives (if non-obvious).

## Commits

| SHA | Repo | Description |
|-----|------|-------------|
| `abc1234` | enterprise | Preserved string type for committee_id in silver transform |
| `def5678` | enterprise | Added round-trip test for zero-padded FEC identifiers |
| `ghi9012` | siege_utilities | Updated census join to handle string committee IDs |

## Acceptance criteria

- [x] `committee_id` remains a zero-padded string through the full pipeline
- [x] Round-trip test: bronze -> silver -> re-read matches original FEC file
- [x] No regression in row counts (silver still has >= 6.8M records)

## Verification

How the fix was verified: which tests were run, on what environment, with what
data. Include commands or test output references where useful.

## Notes

(Optional) Anything a future reader should know: related tickets opened as
follow-up, known limitations, things that were explicitly descoped.
```

## Principles

1. **The closing comment should stand alone** -- A reader should understand the full story from this one comment without reading the thread. Summarise, don't say "see above"
2. **Link every commit** -- The closing comment is the authoritative mapping from ticket to code changes. Missing a commit here means it becomes invisible to future archaeology
3. **Check off acceptance criteria explicitly** -- Use `[x]` for met criteria. If a criterion was descoped or changed, note that with a brief explanation rather than silently removing it
4. **Describe verification concretely** -- "Tested locally" is weak. "Ran `pytest tests/test_silver.py -k committee_id` -- 3/3 passed. Verified on cluster via Rundeck job FecLoad (run #847)" is strong
5. **Name follow-up work** -- If the fix revealed adjacent issues, link the new tickets. Don't close with known loose ends undocumented

# Closing on each platform

## GitHub

```bash
# Add closing comment
gh issue comment 42 --repo electinfo/enterprise --body "$(cat <<'EOF'
## Resolution
...closing comment body...
EOF
)"

# Close the issue
gh issue close 42 --repo electinfo/enterprise --reason completed
```

## GitLab

```bash
# Add closing comment via API
glab issue note 42 --message "## Resolution ..."

# Close the issue
glab issue close 42
```

## Cross-platform sync

If the ticket is dual-tracked (e.g., GitHub `electinfo/enterprise` and GitLab `siege-analytics/fec/pure-translation`):

1. Write the closing comment on the primary platform
2. Copy the same closing comment to the mirror platform
3. Close on both platforms
4. Verify both show as closed

# Close vs. move to In Review

Some projects distinguish between "close" (done, verified) and "move to In Review" (done, awaiting human review). Check the project's workflow:

- If the project has an In Review status and the operator has not explicitly asked to close, move to In Review instead of closing. Add the closing comment either way.
- If the operator explicitly says to close, close it.
- Never move tickets to Done autonomously -- that is the operator's call.

# Attribution policy

**NEVER** include AI or agent attribution in closing comments, summaries, or ticket metadata. This includes:
- No "Generated with Claude Code", "Made with Cursor", "Built with Codex", or any AI tool mentions
- No `🤖`, `[bot]`, or other markers that signal AI involvement
- No attribution to any AI assistant, code generation tool, or agent framework
- This applies to closing comments, summary text, and any linked content

# Checklist

- [ ] Read the full ticket history (all comments, linked PRs, related tickets)
- [ ] Gathered all related commits across all relevant repositories
- [ ] Closing comment stands alone as a complete summary
- [ ] Every commit is linked with SHA, repo, and description
- [ ] Acceptance criteria are explicitly checked off or annotated
- [ ] Verification is described concretely (environment, commands, results)
- [ ] Follow-up tickets are linked if any were created
- [ ] Cross-platform sync: closed on all tracked platforms
- [ ] No AI/agent attribution anywhere in the closing content (no "Generated with", no "Made with", no tool mentions)
- [ ] Status set appropriately (In Review vs. Done per project workflow)
