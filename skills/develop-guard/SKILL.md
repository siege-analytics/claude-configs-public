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
> **Do not override an explicit project topology.** This repository mandates feature/fix -> develop -> main (K5); observed PR history may reveal drift but cannot authorize main-direct work. In other projects, detect mode and ask when uncertain; never silently create or push an integration branch.

# Instructions

This skill is a guardrail that runs before branching or merging. A declared project topology takes precedence over observed workflow history.

1. **Verify the declared topology, then detect workflow drift** (see Mode detection below). Sample the last ~10 merged PR bases; main-direct history in a declared develop-first repository is drift to surface, not permission to change the PR base.
2. **Apply the declared project topology first (this repository: develop-first), then the verified mode where no project policy exists:**
   - *Gitflow*: branch from `develop`; PR base is `develop`; merges to main are promotion events that require existing explicit or applicable standing release authorization with its conditions satisfied. A `promote/*` branch may target `main` only when it represents an already-merged `develop` tree and the PR body carries `Self-Review-Source: <artifact>` evidence.
   - *GitHub Flow*: branch from `main`; PR base is `main`; the PR review IS the curation gate. Don't insist on a develop layer the repo doesn't use.
3. **If a declared develop-first project has a missing or stale integration branch**, verify current refs and keep dependent branching stopped until repaired. Use an existing explicit or applicable standing instruction to perform the scoped sync or creation through the required reviewed workflow. If that authority is missing, ask for it once. Do not infer a topology change, overwrite existing work or fall through to main. Repeated stale-develop history is drift to repair within authority, not permission to change the declared topology.
4. **Before any merge to main, verify applicable authorization and readiness** (Gitflow release or GitHub Flow PR merge). Check the task and standing instructions; a new session or first PR does not invalidate existing authorization. Ask only when the intended destination or authority is genuinely unresolved.

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

If multiple develop-role synonyms exist (e.g., both `dev` and `staging`), check declared topology and prior decisions for the primary branch. Ask only if that material choice remains unresolved.

## Stale-develop detection (declared develop-first or verified Gitflow repos)

This check applies when project policy requires develop-first or when an undeclared project's verified mode is Gitflow. If recent merged PRs target main, this may be drift: check the declared project policy before treating develop as decorative. For this repository staleness blocks branching regardless of PR history.

For develop-first repos:

```bash
# Commits on main but not on develop (this set must be empty for develop to be a true superset)
git log --oneline origin/develop..origin/main | head
```

If that command returns ANY commits in a develop-first repo, develop is stale relative to main. **Stop dependent branching** and inspect the existing sync authority. If repair is already authorized, prepare the normal reviewed sync without asking again. If authority is missing, surface the specific decision:

> `develop` is behind `main` by N commits. The declared topology requires `main` ⊆ `develop`. Should we open a reviewed sync PR into `develop`, or investigate whether project topology should change? I will not branch or target `main` directly without a separately approved policy change.

An authorized sync preserves the declared topology; it does not authorize changing that topology. A topology change still requires an explicit project policy decision, not just a single PR override.

# Creating develop when missing

If no integration branch exists (no `develop`, no synonym):

1. **Verify creation authority first.** If an explicit or applicable standing instruction already authorizes this integration-branch setup, follow it and its conditions within your role. Otherwise ask for that missing decision:

   > This repository has no `develop` branch (and no synonym -- `dev`, `development`, `staging`, `next`, `integration`, `trunk`). The develop-first workflow needs an integration branch. Should we explicitly approve creation of an integration branch from verified `main`, or stop and decide a different documented topology? I will not target `main` directly under a develop-first project policy.

   The user owns the onboarding decision. Do not infer it merely because a branch is absent; honor an existing instruction to perform the setup without requesting it again.

2. After verifying the scoped creation authority and its conditions above, **create and push**:

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

Before any merge to main, verify the applicable existing authorization and readiness conditions. Request a new decision only when the necessary scope is missing; an already-authorized release does not need repeat confirmation.

## Decision tree

```
Merge target is main?
├── Applicable explicit/standing release authority AND readiness satisfied?
│   ├── No authority? -> Ask for that missing decision; continue authorized preparation
│   ├── Missing review/CI/evidence? -> Complete prerequisites within role; keep merge stopped
│   └── Yes -> Apply the source/topology checks below
├── Source is develop? -> Proceed after the common authorization/readiness check
├── Source is promote/*?
│   ├── Final tree equals intended develop snapshot AND Self-Review-Source exists? -> Proceed after common check
│   └── Missing evidence or tree mismatch? -> Fix promotion PR; keep merge stopped
├── Source is an authorized hotfix/ branch? -> Proceed after common check, then back-merge to develop
├── Source is any other branch?
│   └── Stop main merge; use declared integration path
│       └── A requested topology change needs a separate explicit policy decision
└── Direct commit to main? -> Stop; use the declared reviewed branch path
```

## Phrasing the question

Only when applicable release authorization is missing, ask:

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
- **All / nearly-all merged PRs based on `main`** -> in a project without a declared integration policy this suggests GitHub Flow; branch from main only after verifying topology. In a declared develop-first project, flag drift and retain develop as the base.
- **All / nearly-all merged PRs based on `develop` (or synonym)** -> repo is **Gitflow**. Branch from develop; PR to develop. Merges to main are release events.
- **Mixed** -> follow an existing declared topology and surface drift. If no declared policy or prior decision settles the mode, ask for that missing topology decision; do not invent one from mixed history.

A `develop` branch that exists but receives no PRs is NOT evidence of Gitflow -- it's evidence of a workflow that aspires to Gitflow but operates as GitHub Flow. Surface observed workflow and check declared project topology; PR-base history cannot silently override this repository's develop-first policy.

# Repository setup patterns

| Pattern | Branches | Detection |
|---------|----------|---------------|
| **Gitflow** | main + develop + feature/* | `develop` exists AND recent merged PRs target develop |
| **GitHub Flow** | main + feature/* | Recent merged PRs target main; `develop` is absent OR decorative |
| **Trunk-based** | main only, short-lived branches | Same as GitHub Flow with even shorter branch lifetimes |

**Aspirational-Gitflow gotcha:** if `develop` exists but recent merged PRs all target main, this repo is operating as GitHub Flow despite the branch existing. Surface the observation and ask about a policy decision. Under an existing develop-first declaration, do not switch to main-direct work or infer authority to sync/create branches; carry out a sync only when existing authorization covers it.

**Onboarding a new repo to Gitflow:** distinguish discussion of a preferred topology from an instruction to implement it. If setup already has applicable authorization, perform the scoped creation/sync through its required review process. If the user has only expressed a preference and migration authority is unresolved, ask for that decision. Do not reinterpret routine setup as permission to rewrite existing branches or change project policy.

# Edge cases

## Newly initialised repository

For a brand new repository with only an initial commit on main, verify that explicit or applicable standing setup authorization covers the following steps; ask only if it is missing:

```bash
git checkout -b develop
git push -u origin develop
```

## Repository with only a main branch and existing feature branches

Some feature branches may already target main. When you encounter this:

1. Verify the declared topology and existing creation authority; ask only for a missing decision, then create develop from verified main when authorized
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
- [ ] *Develop-first*: checked the declared integration invariant; if repair is needed, verified existing sync authority or asked for the missing decision
- [ ] *Develop-first*: missing/stale integration repair uses explicit or applicable standing authority and its required reviewed workflow; no inferred topology change or overwritten work
- [ ] *GitHub Flow*: did not insist on a develop layer the repo doesn't use
- [ ] Merges to main have applicable explicit or standing authorization and satisfied readiness conditions; no redundant session-based confirmation
- [ ] For `promote/*` -> main PRs: final tree matches the intended develop snapshot and PR body includes `Self-Review-Source: <artifact>`
- [ ] Direct commits to main are blocked (redirected through branches) in both modes
- [ ] Existing repo conventions (branch names, synonyms, PR-review gates) are respected
