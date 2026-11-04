---
name: develop-guard
description: Enforce the curation invariant -- main-role (main, master, prod, production, trunk, stable, release) is the project's best, ready-to-use work; develop-role (develop, dev, development, next, integration, staging, develop-next) is the origin where experiments compete for main. Detect repo mode (Gitflow vs GitHub Flow). Prevent direct feature-PRs to main-role when develop-role is the workflow.
allowed-tools: Bash
---

# Core invariant

> **`main` (or its synonym) is the subset of work the project believes is its best, ready for downstream consumers. `develop` (or its synonym) is the origin where experiments converge and compete for promotion to main.**
>
> Both names are roles, not literal strings. Many repos use synonyms; the role each branch plays is what matters.
>
> - **Main-role** ("best work, ready to use"): `main`, `master`, `prod`, `production`, `trunk` (when used as the release line), `stable`, `release`.
> - **Develop-role** ("origin of experiments competing for main"): `develop`, `dev`, `development`, `next`, `integration`, `staging`, `develop-next`, `trunk` (when used as the integration line -- context-dependent).
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
> **Do not override an explicit project topology.** This repository mandates feature/fix → develop → main (K5); observed PR history may reveal drift but cannot authorize main-direct work. In other projects, detect mode and ask when uncertain; never silently create or push an integration branch.

# Instructions

This skill is a guardrail that runs before branching or merging. A declared project topology takes precedence over observed workflow history.

1. **Verify the declared topology, then detect workflow drift** (see Mode detection below). Sample the last ~10 merged PR bases; main-direct history in a declared develop-first repository is drift to surface, not permission to change the PR base.
2. **Apply the declared project topology first (this repository: develop-first), then the verified mode where no project policy exists:**
   - *Gitflow*: branch from `develop`; PR base is `develop`; merges to main are promotion events that require explicit user approval. A `promote/*` branch may target `main` only when it represents an already-merged `develop` tree and the PR body carries `Self-Review-Source: <artifact>` evidence.
   - *GitHub Flow*: branch from `main`; PR base is `main`; the PR review IS the curation gate. Don't insist on a develop layer the repo doesn't use.
3. **If a declared develop-first project has a missing or stale integration branch** -- STOP. Ask the user before creating develop or syncing. Do not silently create the branch or fall through to main. Repeated stale-develop history may signal drift; surface it without changing the declared topology.
4. **Before any merge to main, verify the user intended it** (Gitflow: this is a release event; GitHub Flow: this is the standard PR merge -- still confirm scope on first PR open per session).

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
| **develop-role** ("origin of experiments competing for main") | `develop`, `dev`, `development`, `next`, `integration`, `staging`, `develop-next`, `trunk` (when used as the integration line -- context-dependent) |

`trunk` is ambiguous: in trunk-based-development repos it plays the main-role; in some legacy-Subversion-influenced repos it plays the develop-role. Detect by which of develop-role / main-role is missing -- `trunk` is whichever role isn't otherwise filled.

If any synonym is found, use it as the integration branch. Do not rename it -- adopt the repository's existing convention.

If multiple develop-role synonyms exist (e.g., both `dev` and `staging`), ask the user which is the primary integration branch.

## Stale-develop detection (declared develop-first or verified Gitflow repos)

This check applies when project policy requires develop-first or when an undeclared project's verified mode is Gitflow. If recent merged PRs target main, this may be drift: check the declared project policy before treating develop as decorative. For this repository staleness blocks branching regardless of PR history.

For develop-first repos:

```bash
# Commits on main but not on develop (this set must be empty for develop to be a true superset)
git log --oneline origin/develop..origin/main | head
```

If that command returns ANY commits in a develop-first repo, develop is stale relative to main. **Stop branching** and surface to the user:

> `develop` is behind `main` by N commits. The declared topology requires `main` ⊆ `develop`. Should we open a reviewed sync PR into `develop`, or investigate whether project topology should change? I will not branch or target `main` directly without a separately approved policy change.

Do not silently choose an option; changing declared topology requires an explicit project policy decision, not just a single PR override.

# Creating develop when missing

If no integration branch exists (no `develop`, no synonym):

1. **ASK FIRST.** Do not silently create the branch. Phrase it explicitly:

   > This repository has no `develop` branch (and no synonym -- `dev`, `development`, `staging`, `next`, `integration`, `trunk`). The develop-first workflow needs an integration branch. Should we explicitly approve creation of an integration branch from verified `main`, or stop and decide a different documented topology? I will not target `main` directly under a develop-first project policy.

   The user owns the decision to onboard a repository to the workflow. Never treat creation or push as implicit.

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
├── Source is promote/*?
│   ├── Final tree equals intended develop snapshot AND PR body has Self-Review-Source? → Proceed
│   └── Missing evidence or tree mismatch? → STOP; fix the promotion PR before merge
├── Source is a hotfix/ branch?
│   ├── User explicitly requested it? → Proceed (then back-merge to develop)
│   └── User did NOT request it? → Ask first, explain hotfix flow
├── Source is any other branch?
│   └── STOP. Inform user: "Feature branches should merge to develop, not main."
│       ├── User overrides? → STOP under a develop-first project policy; require a separate policy change
│       └── User agrees? → Redirect merge to develop
└── Direct commit to main? → STOP. "All changes should go through a branch."
```

## Phrasing the question

When asking the user before merging to main:

> This will merge `develop` into `main`. Merges to main are release events. Proceed?

or

> This branch (`feature/xyz`) targets `main` directly. The standard workflow is to merge into `develop` first. Should I:
> 1. Merge into `develop` instead (recommended)
> 2. Stop and request a separate topology/policy decision (no direct feature merge to main)

Be clear about what you're doing and why you're asking.

# Mode detection

Don't assume which mode a repo is in from the branch list alone -- `develop` can exist and still be decorative. Sample recent merged PRs and look at their base branches:

```bash
gh pr list --repo "$OWNER/$REPO" --state merged --limit 10 \
  --json baseRefName --jq '.[] | .baseRefName' | sort | uniq -c
```

Decision rule:
- **All / nearly-all merged PRs based on `main`** → in a project without a declared integration policy this suggests GitHub Flow; branch from main only after verifying topology. In a declared develop-first project, flag drift and retain develop as the base.
- **All / nearly-all merged PRs based on `develop` (or synonym)** → repo is **Gitflow**. Branch from develop; PR to develop. Merges to main are release events.
- **Mixed** → ASK the user which mode the repo should be in. A mixed history is itself a smell (workflow drift); don't pick on the agent's behalf.

A `develop` branch that exists but receives no PRs is NOT evidence of Gitflow -- it's evidence of a workflow that aspires to Gitflow but operates as GitHub Flow. Surface observed workflow and check declared project topology; PR-base history cannot silently override this repository's develop-first policy.

# Repository setup patterns

| Pattern | Branches | Detection |
|---------|----------|---------------|
| **Gitflow** | main + develop + feature/* | `develop` exists AND recent merged PRs target develop |
| **GitHub Flow** | main + feature/* | Recent merged PRs target main; `develop` is absent OR decorative |
| **Trunk-based** | main only, short-lived branches | Same as GitHub Flow with even shorter branch lifetimes |

**Aspirational-Gitflow gotcha:** if `develop` exists but recent merged PRs all target main, this repo is operating as GitHub Flow despite the branch existing. Surface the observation and ask about a policy decision. Under an existing develop-first declaration, do not switch to main-direct work or silently sync/create branches.

**Onboarding a new repo to Gitflow:** if the user explicitly tells you a repo SHOULD be Gitflow but isn't yet (no develop, or develop stale), don't silently create / sync. Ask first -- onboarding has migration cost and the user should own that decision.

# Edge cases

## Newly initialised repository

For a brand new repository with only an initial commit on main, **ask for explicit approval** before the following steps:

```bash
git checkout -b develop
git push -u origin develop
```

## Repository with only a main branch and existing feature branches

Some feature branches may already target main. When you encounter this:

1. Ask and verify topology, then create develop from main only after explicit approval
2. For new branches going forward, branch from develop
3. Do not retroactively rebase existing branches unless the user asks

## Forked repositories

If working on a fork, develop is local to the fork. Upstream typically only has main. This is fine -- the fork's develop serves as the integration branch before opening a PR to upstream.

# Pair with automated enforcement

This skill is the prose layer. Per `writing-rules:1`, prose alone reaches only the agent that reads it; tool defaults (`gh pr create` / `glab mr create` default to the repo's default branch, often main-role) reach every actor. Every Gitflow repo that depends on this skill should also ship a CI workflow that fails feature-PRs/MRs whose base is main-role.

Reference implementations:

- **GitHub Actions**: [siege-analytics/socialwarehouse `.github/workflows/pr-base-guard.yml`](https://github.com/siege-analytics/socialwarehouse/blob/develop/.github/workflows/pr-base-guard.yml).
- **GitLab CI**: `templates/gitlab-pr-base-guard.yml` in this repo. Include via `.gitlab-ci.yml`'s `include:` mechanism.

Both honor the synonym tables above, allow `develop`/`dev`/`next`/`integration`/`staging`/`develop-next` as heads, allow `release/*` / `hotfix/*` branch naming, and accept an explicit `hotfix-direct-to-main` bypass label for emergency cases. `promote/*` is allowed for main-targeted PRs only as a self-reviewed linear-promotion vehicle: the promoted content must already be on the develop-role branch, and the PR body must include `Self-Review-Source: <artifact>`.

The **local** pre-tool-use enforcement is `hooks/git/pr-base-guard.sh` -- it catches both `gh pr create` (GitHub) and `glab mr create` (GitLab) before the command reaches the remote.

When this skill fires on a Gitflow repo missing the guard, propose adding it -- that's how the rule binds actors who don't share the agent's memory.

# Attribution policy

**NEVER** include AI or agent attribution in branch creation, merge commits, or related comments.

# Checklist

- [ ] Checked declared project topology first; sampled PR bases to identify drift, not to override it
- [ ] Picked branch / PR-base per declared topology (this repository: develop; only undeclared GitHub Flow projects may target main after verification)
- [ ] *Develop-first*: checked that develop is a superset of main; if not, surfaced sync/policy decision to user
- [ ] *Develop-first*: if develop missing or stale, **asked the user** before creating / syncing (no silent action)
- [ ] *GitHub Flow*: did not insist on a develop layer the repo doesn't use
- [ ] Merges to main verified intended (release event in Gitflow; standard PR-merge in GitHub Flow)
- [ ] For `promote/*` -> main PRs: final tree matches the intended develop snapshot and PR body includes `Self-Review-Source: <artifact>`
- [ ] Direct commits to main are blocked (redirected through branches) in both modes
- [ ] Existing repo conventions (branch names, synonyms, PR-review gates) are respected
