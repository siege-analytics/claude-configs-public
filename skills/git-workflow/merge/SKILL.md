---
name: merge
description: Merge branches following a develop-first workflow. Feature branches merge to develop; develop merges to main only with explicit approval.
disable-model-invocation: true
allowed-tools: Bash
argument-hint: "[source-branch] [target-branch]"
---

# Instructions

1. Determine the merge direction
   1. Feature/task/bugfix branches merge into `develop`
   2. `develop` merges into `main` only when explicitly requested or when cutting a release
   3. `hotfix/` branches are the only exception -- they may merge directly into `main` (and then back-merge into `develop`)
2. Verify the branch is ready to merge
   1. All commits pushed to remote
   2. Tests pass on the branch
   3. Ticket is in a complete state (acceptance criteria met)
   4. PR exists and has been reviewed (if the project uses PRs)
3. Perform the merge (see Merge procedures below)
4. Update tickets and clean up branches
5. If merging to `main`, ask the user first unless they already requested it

# Merge philosophy

The `develop` branch is the integration branch. It is where all work lands first, where integration issues are caught, and where the next release takes shape. The `main` branch is the release branch. It should always reflect a deployable, verified state.

**Merge to develop freely.** When a feature branch is done and tested, merge it into develop without ceremony. This is the normal flow.

**Merge to main carefully.** A merge to main is a release event. It should be deliberate, not accidental. Always ask the user before merging to main unless they have explicitly requested it in this conversation.

**Never push directly to main.** All changes reach main through either develop (normal) or a hotfix branch (emergency). Direct commits to main skip integration testing and review.

# Merge flow

```
feature/xyz ──┐
               ├──▶ develop ──────▶ main
bugfix/abc  ──┘         ▲              ▲
                        │              │
task/cleanup ───────────┘   hotfix/critical (exception)
```

## Normal flow: branch → develop

```bash
# Ensure develop is up to date
git checkout develop
git pull origin develop

# Merge the feature branch
git merge --no-ff feature/geographic_enrichment_phase1

# Push develop
git push origin develop

# Delete the feature branch
git branch -d feature/geographic_enrichment_phase1
git push origin --delete feature/geographic_enrichment_phase1
```

The `--no-ff` flag creates a merge commit even if fast-forward is possible. This preserves the branch history in the graph, making it clear what work was done in which branch.

## Release flow: develop → main

**Always ask the user before doing this.** A merge to main is a release.

```bash
# Confirm with user: "Ready to merge develop into main?"

# Ensure both branches are up to date
git checkout main
git pull origin main
git checkout develop
git pull origin develop

# Merge develop into main
git checkout main
git merge --no-ff develop -m "release: Merge develop into main

Contains: [brief summary of what's in this release]"

# Tag if appropriate
git tag -a v1.2.0 -m "Release v1.2.0: [summary]"

# Push main and tags
git push origin main
git push origin --tags

# Back-merge main into develop (to pick up any tag commits)
git checkout develop
git merge main
git push origin develop
```

## Hotfix flow: hotfix → main → develop

Hotfixes are the only branches that merge directly to main. After merging to main, always back-merge into develop so the fix is present in both branches.

```bash
# Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/restore_spark_connect

# ... make the fix, commit ...

# Merge to main (ask user first)
git checkout main
git merge --no-ff hotfix/restore_spark_connect
git push origin main

# Back-merge into develop
git checkout develop
git merge main
git push origin develop

# Clean up
git branch -d hotfix/restore_spark_connect
git push origin --delete hotfix/restore_spark_connect
```

# When to merge to main

Merge develop into main when:

1. **The user explicitly asks** -- "merge to main", "release", "deploy to production"
2. **A release is being cut** -- versioned releases, tagged deployments
3. **A milestone is complete** -- all tickets in a milestone are closed

Do NOT merge to main when:

1. **A single feature is done** -- merge to develop, not main
2. **You think it's ready** -- ask the user first
3. **CI passes on develop** -- passing CI is necessary but not sufficient

If you are uncertain whether to merge to main, **ask the user**. The cost of asking is low. The cost of an unwanted merge to main is high.

# Handling merge conflicts

When a merge has conflicts:

1. **Do not resolve conflicts silently** -- Inform the user what files conflict and what the competing changes are
2. **Show the conflict markers** -- Let the user see the `<<<<<<<` / `>>>>>>>` context
3. **Propose a resolution** -- Explain which side should win and why, based on your understanding of the code
4. **Wait for confirmation** before resolving, unless the resolution is trivially obvious (e.g., a purely additive change)

```bash
# If merge conflicts occur
git merge --abort  # if the user wants to reconsider

# Or resolve and continue
# ... edit conflicting files ...
git add resolved_file.py
git commit  # uses the merge commit message
```

# Updating tickets after merge

After merging a branch into develop:

1. **Add a comment on the ticket** noting the merge:
   ```
   Merged feature/geographic_enrichment_phase1 into develop.
   PR: #123 (if applicable)
   Commits: abc1234, def5678, ghi9012
   ```
2. **Update ticket status** to "In Review" (or equivalent)
3. **Link the PR** if one was used

After merging develop into main:

1. **Close related tickets** that are fully resolved in this release (per close-ticket skill)
2. **Update milestone** if applicable
3. **Notify the team** if the project has a release communication channel

# Branch cleanup

After every merge, delete the source branch (unless it's `develop` or `main`):

```bash
# Local
git branch -d feature/geographic_enrichment_phase1

# Remote
git push origin --delete feature/geographic_enrichment_phase1
```

Never delete a branch that hasn't been merged. If `git branch -d` refuses (unmerged changes), investigate before using `-D`.

# PR-based merges

When the project uses pull requests, the merge happens through the PR rather than locally:

```bash
# Merge PR via CLI (GitHub)
gh pr merge 123 --merge --delete-branch

# Merge PR via CLI (GitLab)
glab mr merge 123 --remove-source-branch
```

The `--merge` flag creates a merge commit (equivalent to `--no-ff`). Avoid `--squash` unless the project specifically uses squash-and-merge workflow.

# Attribution policy

**NEVER** include AI or agent attribution in merge commit messages, PR merge descriptions, or related comments. This includes:
- No "Generated with Claude Code", "Made with Cursor", or any AI tool mentions
- No `Co-Authored-By` lines referencing AI tools
- This applies to merge commit messages, tag annotations, and release notes

# Checklist

- [ ] Merge direction is correct (feature → develop, develop → main, hotfix → main + develop)
- [ ] Source branch is up to date and pushed
- [ ] Tests pass on the source branch
- [ ] Using `--no-ff` to preserve branch history
- [ ] If merging to main: user has explicitly approved
- [ ] Merge conflicts resolved with user awareness (not silently)
- [ ] Tickets updated with merge status and commit links
- [ ] Source branch deleted after merge (local and remote)
- [ ] If merged to main: back-merged into develop
- [ ] No AI/agent attribution in merge commits, tags, or release notes
