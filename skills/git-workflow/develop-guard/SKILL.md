---
name: develop-guard
description: Enforce the curation invariant — main-role (main, master, prod, production, trunk, stable, release) is the project's best, ready-to-use work; develop-role (develop, dev, development, next, integration, staging, develop-next) is the origin where experiments compete for main. Detect repo mode (Gitflow vs GitHub Flow). Prevent direct feature-PRs to main-role when develop-role is the workflow.
disable-model-invocation: true
allowed-tools: Bash
---

# Core invariant

> **`main` (or its synonym) is the subset of work the project believes is its best, ready for downstream consumers. `develop` (or its synonym) is the origin where experiments converge and compete for promotion to main.**
>
> Both names are roles, not literal strings. Many repos use synonyms; the role each branch plays is what matters.
>
> - **Main-role** ("best work, ready to use"): `main`, `master`, `prod`, `production`, `trunk` (when used as the release line), `stable`, `release`.
> - **Develop-role** ("origin of experiments competing for main"): `develop`, `dev`, `development`, `next`, `integration`, `staging`, `develop-next`, `trunk` (when used as the integration line — context-dependent).
>
> Whatever the integration surface is in this repository, the main-role branch is downstream of work that has been *blessed*. The main-role branch is never upstream of unblessed work, and is never bypassed by work that hasn't passed the bar.
>
> Two repo modes both satisfy this:
>
> | Mode | Integration surface | What "main-role is the curated best" means here |
> |---|---|---|
> | **Gitflow** (a develop-role branch exists; recent merged PRs target it) | the develop-role branch | Feature/task/bugfix branches merge to the develop-role branch; the main-role branch only receives commits via promotion from develop-role or back-merged hotfix. `main-role` ⊆ `develop-role`. |
> | **GitHub Flow / Trunk-based** (no develop-role branch, or it is decorative; recent merged PRs target main-role) | the main-role branch itself | Feature/task/bugfix branches merge to main-role via PR; the PR review is the curation gate. Only blessed work lands; half-baked work stays on its feature branch. |
>
> **Don't fight the repo's actual workflow.** Detect which mode the repo is in (next section); apply the rule's substantive shape (curate, don't bypass), not its surface (literal branch name).

# Instructions

This skill is a guardrail that runs before branching or merging. It enforces the curation invariant above per the repo's actual workflow mode.

1. **Detect the repo's workflow mode** (see Mode detection below). Sample the last ~10 merged PRs on `main`'s history: if most/all had `base=main`, the repo is **GitHub Flow / Trunk-based**; if most/all had `base=develop` (or synonym), the repo is **Gitflow**.
2. **Apply the mode's branching rule:**
   - *Gitflow*: branch from `develop`; PR base is `develop`; merges to main are promotion events that require explicit user approval.
   - *GitHub Flow*: branch from `main`; PR base is `main`; the PR review IS the curation gate. Don't insist on a develop layer the repo doesn't use.
3. **If Gitflow but `develop` is missing or stale relative to main** — STOP. Ask the user before creating develop OR before doing a sync. Do not silently create the branch or silently fall through to main. The recurring stale-develop pattern is itself a signal that the repo may actually be GitHub Flow with an aspirational develop; surface that observation.
4. **Before any merge to main, verify the user intended it** (Gitflow: this is a release event; GitHub Flow: this is the standard PR merge — still confirm scope on first PR open per session).

# Develop-role branch detection

Check for the develop-role branch by scanning both local and remote branches:

```bash
# Check local branches
git branch | grep -iE '^\*?\s*(develop|dev|development|staging|next|integration|develop-next)$'

# Check remote branches
git branch -r | grep -iE '(develop|dev|development|staging|next|integration|develop-next)$'
```

## Synonym table

| Role | Synonyms |
|-----------|----------|
| **main-role** ("best work, ready to use") | `main`, `master`, `prod`, `production`, `trunk` (when used as the release line), `stable`, `release` |
| **develop-role** ("origin of experiments competing for main") | `develop`, `dev`, `development`, `next`, `integration`, `staging`, `develop-next`, `trunk` (when used as the integration line — context-dependent) |

`trunk` is ambiguous: in trunk-based-development repos it plays the main-role; in some legacy-Subversion-influenced repos it plays the develop-role. Detect by which of develop-role / main-role is missing — `trunk` is whichever role isn't otherwise filled.

If any synonym is found, use it as the integration branch. Do not rename it — adopt the repository's existing convention.

If multiple develop-role synonyms exist (e.g., both `dev` and `staging`), ask the user which is the primary integration branch.

## Stale-develop detection (Gitflow repos only)

This check applies only when Mode detection has identified the repo as Gitflow. If recent merged PRs target main (GitHub Flow), staleness of a decorative develop branch is not a blocking concern — that's the workflow.

For Gitflow repos:

```bash
# Commits on main but not on develop (this set must be empty for develop to be a true superset)
git log --oneline origin/develop..origin/main | head
```

If that command returns ANY commits in a confirmed-Gitflow repo, develop is stale relative to main. **Stop branching** and surface to the user:

> `develop` is behind `main` by N commits. Per the curation invariant for this Gitflow repo, `main` ⊆ `develop`. I can either (a) open a sync PR to merge `main` into `develop` before opening the feature branch, or (b) target `main` for this single piece of work and file a sync ticket for later, or (c) reconsider whether this repo is actually Gitflow given the pattern of main-direct PRs that produced the staleness. Which?

Do not silently choose any option — it's a judgement call the user should make. The "(c) reconsider mode" option is on the menu precisely because recurring stale-develop is itself a signal that the repo may be operating as GitHub Flow despite the branch existing.

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

# Mode detection

Don't assume which mode a repo is in from the branch list alone — `develop` can exist and still be decorative. Sample recent merged PRs and look at their base branches:

```bash
gh pr list --repo "$OWNER/$REPO" --state merged --limit 10 \
  --json baseRefName --jq '.[] | .baseRefName' | sort | uniq -c
```

Decision rule:
- **All / nearly-all merged PRs based on `main`** → repo is **GitHub Flow** (or trunk-based). The PR review is the curation gate. Branch from main; PR to main. If `develop` exists, it's decorative — flag this to the user as a possible cleanup but do not insist on using it.
- **All / nearly-all merged PRs based on `develop` (or synonym)** → repo is **Gitflow**. Branch from develop; PR to develop. Merges to main are release events.
- **Mixed** → ASK the user which mode the repo should be in. A mixed history is itself a smell (workflow drift); don't pick on the agent's behalf.

A `develop` branch that exists but receives no PRs is NOT evidence of Gitflow — it's evidence of a workflow that aspires to Gitflow but operates as GitHub Flow. Treat the repo by its actual workflow (PR-base history), not its branch-list pretensions.

# Repository setup patterns

| Pattern | Branches | Detection |
|---------|----------|---------------|
| **Gitflow** | main + develop + feature/* | `develop` exists AND recent merged PRs target develop |
| **GitHub Flow** | main + feature/* | Recent merged PRs target main; `develop` is absent OR decorative |
| **Trunk-based** | main only, short-lived branches | Same as GitHub Flow with even shorter branch lifetimes |

**Aspirational-Gitflow gotcha:** if `develop` exists but recent merged PRs all target main, this repo is operating as GitHub Flow despite the branch existing. Don't force a Gitflow merge sequence on it — that's the rule fighting the workflow. Surface the observation; let the user decide whether to (a) accept GitHub Flow and document it, (b) migrate the repo to Gitflow via a one-time sync, or (c) something else.

**Onboarding a new repo to Gitflow:** if the user explicitly tells you a repo SHOULD be Gitflow but isn't yet (no develop, or develop stale), don't silently create / sync. Ask first — onboarding has migration cost and the user should own that decision.

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

# Pair with automated enforcement

This skill is the prose layer. Per `writing-rules:1`, prose alone reaches only the agent that reads it; tool defaults (`gh pr create` / `glab mr create` default to the repo's default branch, often main-role) reach every actor. Every Gitflow repo that depends on this skill should also ship a CI workflow that fails feature-PRs/MRs whose base is main-role.

Reference implementations:

- **GitHub Actions**: [siege-analytics/socialwarehouse `.github/workflows/pr-base-guard.yml`](https://github.com/siege-analytics/socialwarehouse/blob/develop/.github/workflows/pr-base-guard.yml).
- **GitLab CI**: `templates/gitlab-pr-base-guard.yml` in this repo. Include via `.gitlab-ci.yml`'s `include:` mechanism.

Both honor the synonym tables above, allow `develop`/`dev`/`next`/`integration`/`staging`/`develop-next` as heads, allow `promote/*` / `release/*` / `hotfix/*` branch naming, and accept an explicit `hotfix-direct-to-main` bypass label for emergency cases.

The **local** pre-tool-use enforcement is `hooks/git/pr-base-guard.sh` — it catches both `gh pr create` (GitHub) and `glab mr create` (GitLab) before the command reaches the remote.

When this skill fires on a Gitflow repo missing the guard, propose adding it — that's how the rule binds actors who don't share the agent's memory.

# Attribution policy

**NEVER** include AI or agent attribution in branch creation, merge commits, or related comments.

# Checklist

- [ ] Detected the repo's **workflow mode** (Gitflow vs GitHub Flow) by sampling recent merged PR bases
- [ ] Picked branch / PR-base per the detected mode (develop for Gitflow; main for GitHub Flow)
- [ ] *Gitflow only*: checked that develop is a superset of main; if not, surfaced sync decision to user with the "reconsider mode" option on the menu
- [ ] *Gitflow only*: if develop missing or stale, **asked the user** before creating / syncing (no silent action)
- [ ] *GitHub Flow*: did not insist on a develop layer the repo doesn't use
- [ ] Merges to main verified intended (release event in Gitflow; standard PR-merge in GitHub Flow)
- [ ] Direct commits to main are blocked (redirected through branches) in both modes
- [ ] Existing repo conventions (branch names, synonyms, PR-review gates) are respected
