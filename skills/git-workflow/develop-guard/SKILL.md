---
name: develop-guard
description: Ensure a develop branch (or synonym) exists before creating feature branches. Create one from main if missing. Prevent direct merges to main.
---

# Instructions

This skill is a guardrail that runs before branching or merging. It ensures the develop-first workflow is in place.

1. Check for a develop branch (or synonym)
2. If none exists, create one from main
3. Before any merge to main, verify the user intended it

# Develop branch detection

Check for the integration branch by scanning both local and remote branches:

```bash
# Check local branches
git branch | grep -iE '^\*?\s*(develop|dev|development|staging|next|integration)$'

# Check remote branches
git branch -r | grep -iE '(develop|dev|development|staging|next|integration)$'
```

## Synonym table

| Canonical | Synonyms |
|-----------|----------|
| `develop` | `dev`, `development`, `staging`, `next`, `integration` |

If any synonym is found, use it as the integration branch. Do not rename it -- adopt the repository's existing convention.

If multiple synonyms exist (e.g., both `dev` and `staging`), ask the user which is the primary integration branch.

# Creating develop when missing

If no integration branch exists:

1. **Inform the user**: "This repository doesn't have a develop branch. I'll create one from main to support the branch workflow."
2. **Create and push**:

```bash
# Create develop from main
git checkout main
git pull origin main
git checkout -b develop
git push -u origin develop

# Return to previous context
git checkout -
```

3. **Verify**: Confirm the branch exists on the remote

```bash
git branch -r | grep develop
```

# Main protection

Before any merge to main, this skill enforces a confirmation step.

## Decision tree

```
Merge target is main?
├── Source is develop?
│   ├── User explicitly requested merge to main? → Proceed
│   └── User did NOT request it? → Ask first
├── Source is a hotfix/ branch?
│   ├── User explicitly requested it? → Proceed (then back-merge to develop)
│   └── User did NOT request it? → Ask first, explain hotfix flow
├── Source is any other branch?
│   └── STOP. Inform user: "Feature branches should merge to develop, not main."
│       ├── User overrides? → Proceed with warning
│       └── User agrees? → Redirect merge to develop
└── Direct commit to main? → STOP. "All changes should go through a branch."
```

## Phrasing the question

When asking the user before merging to main:

> This will merge `develop` into `main`. Merges to main are release events. Proceed?

or

> This branch (`feature/xyz`) targets `main` directly. The standard workflow is to merge into `develop` first. Should I:
> 1. Merge into `develop` instead (recommended)
> 2. Merge into `main` anyway (release/hotfix)

Be clear about what you're doing and why you're asking.

# Repository setup patterns

Different repositories may have different conventions. Detect and adapt:

| Pattern | Branches | How to detect |
|---------|----------|---------------|
| **Gitflow** | main + develop + feature/* | `develop` exists, feature branches merge to develop |
| **GitHub Flow** | main + feature/* | No develop, feature branches merge directly to main |
| **Trunk-based** | main only | No develop, no long-lived feature branches |

**When this skill applies**: If the repository uses GitHub Flow or Trunk-based development, **create a develop branch anyway** per the user's preference. The user has explicitly stated that work should flow through develop before main.

This means even if a repo currently has no develop branch, we create one. The user's workflow preference overrides the repo's existing convention.

# Edge cases

## Newly initialised repository

For a brand new repository with only an initial commit on main:

```bash
git checkout -b develop
git push -u origin develop
```

## Repository with only a main branch and existing feature branches

Some feature branches may already target main. When you encounter this:

1. Create develop from main
2. For new branches going forward, branch from develop
3. Do not retroactively rebase existing branches unless the user asks

## Forked repositories

If working on a fork, develop is local to the fork. Upstream typically only has main. This is fine -- the fork's develop serves as the integration branch before opening a PR to upstream.

# Attribution policy

**NEVER** include AI or agent attribution in branch creation, merge commits, or related comments.

# Checklist

- [ ] Checked for develop branch (or synonym) on local and remote
- [ ] If missing, created develop from main and pushed to remote
- [ ] Feature/task/bugfix branches are created from develop, not main
- [ ] Merges to main require explicit user approval
- [ ] Direct commits to main are blocked (redirected through branches)
- [ ] If repository had no develop, user was informed before creating one
- [ ] Existing repo conventions (branch names, synonyms) are respected
