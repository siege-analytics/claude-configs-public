---
name: merge
description: Merge branches following a develop-first workflow. Feature branches merge to develop; develop merges to main under explicit or applicable standing authorization.
allowed-tools: Bash
---

# Instructions

1. Determine the merge direction
   1. Feature/task/bugfix branches merge into `develop`
   2. `develop` merges into `main` when the operator has authorized that release or an applicable standing approval covers it and its conditions are met
   3. `hotfix/` branches are the only exception -- they may merge directly into `main` (and then back-merge into `develop`)
2. Verify the branch is ready to merge
   1. All commits pushed to remote
   2. Tests pass on the branch
   3. Ticket is in a complete state (acceptance criteria met)
   4. PR exists and has been reviewed (if the project uses PRs)
   5. **Self-review artifact exists** (see Self-review gate below)
3. Perform the merge (see Merge procedures below)
4. Update tickets and clean up branches
5. If merging to `main`, verify existing authorization and its readiness conditions; ask only if release authority is missing

# Self-review gate

A "merge" instruction authorizes the **destination**, not the **method**. The merge process includes review, not replaces it.

Before executing any merge (`gh pr merge`, `git merge`, `glab mr merge`), verify:

1. A self-review artifact exists -- posted to the ticket as a comment or committed to the repo
2. The latest commit on the branch carries `Self-Review:` and `Self-Review-Source:` trailers
3. The artifact has the required sections: `## Assumptions`, `## Peer review`, `## Lead review`

**If required evidence is missing**, inspect the ticket, PR and source-bound artifacts before treating it as absent. Produce missing self-review material within your authorized role and request any required independent review from its owner. Keep the merge blocked until its prerequisites are satisfied, while continuing independent authorized preparation. Do not ask for a review waiver as the default response to missing paperwork.

A merge instruction does not waive required review or CI. `--admin`, disabling a guard or labeling an unreviewed artifact as reviewed does not satisfy a missing review. An exception is valid only under an applicable explicit project/operator exception process; do not infer one from urgency or existing merge authority. If completing a prerequisite needs authority outside your role, identify that exact action and ask the responsible owner for the missing scope. Follow [rule:standing-approval] for conditional authorization.

# Merge philosophy

The `develop` branch is the integration branch. It is where all work lands first, where integration issues are caught, and where the next release takes shape. The `main` branch is the release branch. It should always reflect a deployable, verified state.

**Merge to develop freely.** When a feature branch is done and tested, merge it into develop without ceremony. This is the normal flow.

**Merge to main carefully.** A merge to main is a release event. It should be deliberate, not accidental. Use an existing explicit request or applicable standing approval, verify its conditions, and proceed without asking again. If that release is not authorized, obtain authorization before merging.

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

# Optional cleanup: only if authorized, fully merged, unused and not retained
git branch -d feature/geographic_enrichment_phase1
git push origin --delete feature/geographic_enrichment_phase1
```

The `--no-ff` flag creates a merge commit even if fast-forward is possible. This preserves the branch history in the graph, making it clear what work was done in which branch.

## Release flow: develop → main

**Verify release authorization before doing this.** An explicit request or applicable standing approval is sufficient once its conditions are met; request approval only when it is missing.

```bash
# Verify existing release authorization and required review/CI; ask only if authority is missing

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

# Merge to main after verifying applicable release authorization and readiness
git checkout main
git merge --no-ff hotfix/restore_spark_connect
git push origin main

# Back-merge into develop
git checkout develop
git merge main
git push origin develop

# Optional cleanup: only if authorized, fully merged, unused and not retained
git branch -d hotfix/restore_spark_connect
git push origin --delete hotfix/restore_spark_connect
```

# When to merge to main

Merge develop into main when the release is authorized by the operator's explicit request or an applicable standing approval, and all required review, CI and release conditions are satisfied. Authorization remains valid across turns until completed, changed or revoked; the passage of time or a new substep does not require asking again.

A completed feature, milestone, green CI run or available release tag does not create release authority on its own. Ordinary feature work still targets develop. Check the existing instructions before escalating; if release authority is genuinely absent, ask for that specific decision once and continue authorized preparation.

# Handling merge conflicts

When an authorized merge has conflicts, inspect both changes, the intended behavior, prior decisions and relevant tests. Resolve routine conflicts within your implementation role, preserve both intended changes where compatible, and validate the result. Explain material resolutions in the review artifact; changed source must receive the review and checks it requires.

Ask only when the conflict exposes an unresolved product choice, incompatible requirements or missing authority. Name the decision and hold the dependent merge, rather than asking for confirmation of every technical resolution. A review-only role still requires explicit implementation authorization before editing.

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

# Post-merge: success compounding

After the merge completes and tickets are updated, run the compound
step before cleaning up the branch. See `[skill:compound]` for the
full framework.

The compound step asks three questions:
1. What worked that wasn't obvious?
2. Would a future session find this solution without re-deriving it?
3. Does any existing skill or rule need updating?

It produces one of: a solutions catalog entry, a skill-update ticket,
or a "nothing novel" declaration posted as a PR comment.

This step is advisory — it does not block branch cleanup or any
downstream action. Skipping it produces a visible absence (no
compound comment on the PR) but is not a process violation.

# Branch cleanup

After a merge, clean up a fully merged source branch only within your authority and when it is no longer needed by another worker or retained for audit. Keep `develop`, `main`, branches designated for retention and branches still in use. Cleanup is not a prerequisite to declaring a verified merge complete:

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
gh pr merge 123 --merge

# Merge PR via CLI (GitLab)
glab mr merge 123
```

The `--merge` flag creates a merge commit (equivalent to `--no-ff`). Avoid `--squash` unless the project specifically uses squash-and-merge workflow.

# Attribution policy

**NEVER** include AI or agent attribution in merge commit messages, PR merge descriptions, or related comments. This includes:
- No "Generated with Claude Code", "Made with Cursor", or any AI tool mentions
- No `Co-Authored-By` lines referencing AI tools
- This applies to merge commit messages, tag annotations, and release notes

# Checklist

- [ ] Self-review artifact exists and is posted to ticket (or explicitly waived by user)
- [ ] Latest commit carries `Self-Review:` and `Self-Review-Source:` trailers
- [ ] Merge direction is correct (feature → develop, develop → main, hotfix → main + develop)
- [ ] Source branch is up to date and pushed
- [ ] Tests pass on the source branch
- [ ] Using `--no-ff` to preserve branch history
- [ ] If merging to main: existing explicit request or applicable standing approval covers this release and its conditions are met
- [ ] Routine conflicts resolved from source intent and verified; unresolved material choices escalated and changed source reviewed
- [ ] Tickets updated with merge status and commit links
- [ ] Advisory post-merge compound step considered; it does not block an otherwise-ready merge
- [ ] Source branch cleanup handled within authority; preserve branches still in use or designated for retention
- [ ] If merged to main: back-merged into develop
- [ ] No AI/agent attribution in merge commits, tags, or release notes
