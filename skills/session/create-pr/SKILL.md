---
name: create-pr
description: Create a pull request with a clear title, structured description, linked tickets, and commit narrative
---

# Instructions

1. Understand the full scope of the PR
   1. Run `git log main..HEAD --oneline` (or the appropriate base branch) to see all commits
   2. Run `git diff main..HEAD --stat` to see all files changed
   3. Run `git diff main..HEAD` to review the actual changes if needed
   4. Read the related ticket(s) to understand the intended outcome
2. Determine if the branch is ready
   1. All commits should be pushed to the remote
   2. Tests should pass (run the test suite before opening the PR)
   3. No merge conflicts with the base branch
3. Write the PR title and description (see PR structure below)
4. Create the PR using the platform CLI
5. Link to the relevant ticket(s)
6. Add reviewers, labels, and project board assignment as appropriate

# PR philosophy

A PR is a narrative, not a dump of commits. The reviewer is reading the PR to decide: "Is this change correct, complete, and safe to merge?" Everything in the PR description should serve that question.

**The PR describes the change as a whole.** Individual commits describe individual steps. The PR description synthesises them into a coherent story: what problem was solved, how, and what the reviewer should pay attention to.

**The reviewer's time is expensive.** A well-written PR saves review cycles. A vague PR generates back-and-forth questions that could have been preempted.

**One PR, one purpose.** A PR that fixes a bug, refactors a module, and adds a feature is three PRs. Keep the scope tight so reviewers can evaluate one thing at a time.

# PR structure

## Title

The PR title follows the same conventions as commit subject lines:

1. **Type prefix**: `bugfix:`, `feature:`, `task:`
2. **Imperative mood**: "Add" not "Added"
3. **Under 72 characters**
4. **Specific**: "bugfix: Preserve leading zeros in FEC identifiers" not "Fix bug"

If the PR maps to a single ticket, the title can mirror the ticket name. If it spans multiple tickets, the title should describe the unifying theme.

## Description template

```markdown
## Summary

One to three sentences: what this PR does and why. Not a restatement of
the title -- explain the motivation and approach at a level the reviewer
needs to evaluate the change.

## Tickets

- Fixes #42
- Refs #38
- Part-of #357

## Changes

A structured walkthrough of what changed, organised by concern rather
than by file. The reviewer should be able to read this section and
understand the shape of the change before looking at any code.

### {Concern 1, e.g., "Schema changes"}
- What changed and why

### {Concern 2, e.g., "Test coverage"}
- What was added, what was updated

## Commits

| SHA | Description |
|-----|-------------|
| `abc1234` | Refactored silver transform to preserve string types |
| `def5678` | Added round-trip test for committee_id zero-padding |
| `ghi9012` | Updated Delta schema documentation |

## Testing

How this was tested. Be concrete:
- Which test suite(s) were run and their results
- Manual verification steps taken
- Environment tested on (local, cluster, staging)

## Risks and review guidance

(Optional but valuable) Point the reviewer to the parts that need the
most scrutiny. Call out:
- Areas where you are least confident
- Subtle behavioural changes that the diff doesn't make obvious
- Performance implications
- Migration or backwards-compatibility concerns

## Screenshots / output

(If applicable) Before/after, logs, query results, or other evidence.
```

# Writing the summary

The summary is the most important paragraph in the PR. It should answer three questions:

1. **What was the problem?** -- One sentence describing the deficiency or need
2. **What does this PR do about it?** -- One sentence describing the approach
3. **Why this approach?** -- One sentence (if the approach isn't obvious) explaining the tradeoff or constraint that led to this design

### Good example

> The bronze-to-silver transform was casting FEC identifiers to integer,
> which stripped leading zeros and caused entity collisions downstream.
> This PR changes all FEC identifier columns to StringType in the Delta
> schema, preserving the original zero-padded format from the FEC bulk
> download. StringType was chosen over post-hoc lpad() because identifier
> width varies by type.

### Bad example

> This PR fixes a bug with committee IDs. Updated the schema and added
> tests.

# Writing the changes section

Organise by concern, not by file path. The reviewer thinks in terms of "what problem area is this touching" not "what files were modified."

### Good structure

```markdown
### Schema changes
- Changed `committee_id`, `candidate_id`, and `report_id` from IntegerType
  to StringType in the Delta table definition (`silver_schema.py`)
- Updated the bronze-to-silver transform to skip the integer cast (`silver_transforms.py`)

### Test coverage
- Added round-trip test: write 100 bronze records to silver, read back,
  compare identifiers (`test_silver_identifiers.py`)
- Added data quality assertion: no committee_id with length != 9

### Documentation
- Updated schema docs to reflect string types for FEC identifiers
```

### Bad structure

```markdown
- Updated silver_schema.py
- Updated silver_transforms.py
- Added test_silver_identifiers.py
- Updated docs/schema.md
```

# Commit table

Include a table of all commits in the PR. This gives the reviewer a map of the change at a glance and lets them review commit-by-commit if they prefer.

- List commits in chronological order (oldest first)
- Use short SHAs
- Write a brief description (can differ from the commit subject if a simpler summary helps)
- For large PRs, group commits by concern with subheadings

# Platform-specific commands

## GitHub

```bash
gh pr create \
  --title "bugfix: Preserve leading zeros in FEC identifiers" \
  --body "$(cat <<'EOF'
## Summary
...PR body...

## Tickets
- Fixes #42
EOF
)" \
  --assignee dheerajchand \
  --label "bug,data-quality" \
  --project "electinfo/tasks"
```

### Adding to project board

```bash
# Add PR to project
gh project item-add 1 --owner electinfo --url <pr-url>
```

### Requesting review

```bash
gh pr edit <number> --add-reviewer username
```

## GitLab

```bash
glab mr create \
  --title "bugfix: Preserve leading zeros in FEC identifiers" \
  --description "## Summary ..." \
  --assignee dheerajchand \
  --label "bug,data-quality"
```

## Cross-platform

For dual-tracked repos, create the PR on the primary platform and add a comment on the mirror platform linking to it.

# Draft PRs

Use draft PRs when:
- Work is in progress but you want early feedback on the approach
- CI needs to run before the change is ready for review
- You want to show the scope of a change before it's complete

```bash
gh pr create --draft --title "feature: [WIP] Geographic crosswalk pipeline"
```

Convert to ready when done:

```bash
gh pr ready <number>
```

# PR size guidelines

| Size | Files | Rough LOC | Review approach |
|------|-------|-----------|-----------------|
| Small | 1-5 | < 100 | Single pass, quick review |
| Medium | 5-15 | 100-500 | Review by concern, one session |
| Large | 15-30 | 500-1000 | Review commit-by-commit, may need multiple sessions |
| Too large | 30+ | 1000+ | Consider splitting into multiple PRs |

If a PR is large, explain in the description why it can't be split and suggest a review strategy (e.g., "Review the schema changes first, then the transforms, then tests").

# Checklist

- [ ] All commits pushed to remote
- [ ] Tests pass on the branch
- [ ] No merge conflicts with base branch
- [ ] Title: type prefix, imperative mood, under 72 chars, specific
- [ ] Summary answers: what was the problem, what does this PR do, why this approach
- [ ] Changes section organised by concern, not by file
- [ ] All commits listed in the commit table
- [ ] Tickets linked with appropriate keyword (Fixes, Refs, Part-of)
- [ ] Testing section describes concrete verification
- [ ] Reviewers assigned
- [ ] PR added to project board
- [ ] Cross-platform sync: mirror platform updated if dual-tracked
