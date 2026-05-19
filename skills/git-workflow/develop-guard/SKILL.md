---
name: develop-guard
description: Ensure a develop branch exists before feature branches. Create from main if missing. Prevent direct merges to main.
disable-model-invocation: true
allowed-tools: Bash
---

# Core invariant

> **`main` should always be a subset of `develop`.**
>
> Feature, task, bugfix, and chore branches are built **from `develop`** and merged **back into `develop`**. `develop` is the integration branch. `main` only receives commits via promotion from `develop` (or a hotfix back-merged into develop).
>
> If `develop` is behind `main` (e.g. recent PRs landed directly on `main`), **stop and surface a sync ticket** before opening new feature branches. New feature branches built from a stale `develop` miss those PRs and the subsequent merges will be painful.

# Instructions

This skill is a guardrail that runs before branching or merging. It enforces the develop-first workflow above.

1. **Check for a develop branch (or synonym).** Do NOT assume "main is the integration branch because that's what the repo's default branch is" — that conflates GitHub's default-branch concept with the integration-branch role.
2. **If none exists (and no synonym either)** — STOP. Ask the user before creating one. Do not silently create a develop branch in a repository the user hasn't onboarded to this workflow.
3. **If develop exists but is behind main** — STOP. File / surface a sync ticket and ask the user before continuing. Branches built from a stale develop carry their own divergence forward.
4. **Before any merge to main, verify the user intended it.**

The base-branch choice for a PR is per-repo, but the order of preference is fixed: prefer `develop` (or its synonym) every time it is current; fall back to `main` only when the rule above has been satisfied or the user has explicitly chosen otherwise for this repo.

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
| `develop` | `dev`, `development`, `staging`, `next`, `integration`, `trunk` (when used as integration, not as main-equivalent) |

If any synonym is found, use it as the integration branch. Do not rename it -- adopt the repository's existing convention.

If multiple synonyms exist (e.g., both `dev` and `staging`), ask the user which is the primary integration branch.

## Stale-develop detection

A develop branch that exists but trails main is worse than no develop branch — agents will branch from it and silently inherit the divergence. Detect this case before creating new branches:

```bash
# Commits on main but not on develop (this set must be empty for develop to be a true superset)
git log --oneline origin/develop..origin/main | head
```

If that command returns ANY commits, develop is stale relative to main. **Stop branching** and surface to the user:

> `develop` is behind `main` by N commits. Per the develop-first workflow, `main` should be a subset of `develop`. I can either (a) open a sync PR to merge `main` into `develop` before opening the feature branch, or (b) target `main` for this single piece of work and file a sync ticket for later. Which?

Do not silently choose option (b) — it's the right answer sometimes, but it's a judgement call the user should make.

# Creating develop when missing

If no integration branch exists (no `develop`, no synonym):

1. **ASK FIRST.** Do not silently create the branch. Phrase it explicitly:

   > This repository has no `develop` branch (and no synonym — `dev`, `development`, `staging`, `next`, `integration`, `trunk`). The develop-first workflow needs an integration branch. Should I create one from `main` for this repository going forward, or target `main` directly for this single piece of work?

   The "create develop" answer is the workflow default, but the user owns the decision to onboard a repository to the workflow.

2. After explicit user approval, **create and push**:

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

- [ ] Checked for develop branch (or synonym — `dev`, `development`, `staging`, `next`, `integration`, `trunk`) on local and remote
- [ ] If missing, **asked the user** before creating develop from main (no silent creation)
- [ ] Checked that develop is **a superset of main** (`git log origin/develop..origin/main` is empty); if not, surfaced sync decision to user
- [ ] Feature/task/bugfix branches are created from develop, not main
- [ ] PR base branch is develop, not main (unless user explicitly chose main for this piece of work)
- [ ] Merges to main require explicit user approval
- [ ] Direct commits to main are blocked (redirected through branches)
- [ ] If repository had no develop, user was informed before creating one
- [ ] Existing repo conventions (branch names, synonyms) are respected
