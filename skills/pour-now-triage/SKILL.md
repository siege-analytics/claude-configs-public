---
name: pour-now-triage
description: "Restoration-mode overrides for pour-now codebases (business-backend + business-admin). TRIGGER: any PR against pour-now/* repos, or any session working on pour-now wiki pages, HANDOFF findings, or architectural-review items."
routed-by: coding-standards
user-invocable: true
paths: "**"
---

# pour-now Triage

Restoration doctrine for the pour-now stack. The system is in triage -- every finding is either (a) explicitly sanctioned for the duration, (b) flagged as a material finding for later, or (c) noted as low-priority hygiene. This skill codifies what to leave alone, what to fix in place, and what requires coordinated work.

## Scope

Two repos, two runtimes, one product:

| Repo | Stack | Status |
|---|---|---|
| `pour-now/business-backend` | Django 5 + DRF + Celery + Postgres | Active (hotfix-level) |
| `pour-now/business-admin` | Vue 3 + Pinia + Vite + Netlify | Dormant (~5 months since last commit) |
| `pour-now/admin-business` | Vue 3 + Pinia 3 (rewrite attempt) | Parked (incomplete, no deploy plumbing) |

## Backend triage overrides

These override the `django` SKILL.md for pour-now during triage:

| Override | Django skill rule | Why not now |
|---|---|---|
| Don't split `settings.py` into `settings/` | Settings stratification | K8s Secret + env vars are the override surface and are working |
| Don't squash or renumber migrations | Migrations -- never edit applied | 189 applied migrations with `_merge_` reconciliations; lineage works; rebase before generating new ones |
| Keep DRF serializers as the validation layer | Forms -- where input validation lives | pour-now puts validation on serializers (the JSON input arrives there); forms are admin-only |
| Don't unify APM stacks | Deployment essentials | Three stacks active (Sentry, New Relic, AWS App Signals); consolidation plan exists but is post-triage |
| Don't move Firebase JSON to Vault | Never commit real secrets | Critical finding, but rotation requires coordinated credential swap; file-it, fix-later |

**Model-change checklist** (from `CLAUDE.md`, not overridden):
1. Create migration
2. Check for long locks on big tables (`core_product`, `core_productprice`, `core_productpool`) -- two-step migration
3. Small tables -- single-shot acceptable
4. Test the rollback path
5. Rebase off master before generating to avoid `_merge_` migrations

**When triage ends:** all overrides above revert to the `django` skill's standard rules. The signal is the team committing to a timeline for the rewrite-or-restore decision.

---

## Frontend triage overrides

These override the `vue` SKILL.md for pour-now during triage. Parallel to the backend overrides above.

| Override | Vue skill rule | Why not now | Deviations ref |
|---|---|---|---|
| Don't migrate `components/Layout/` to `features/` | Two-organization split rule (vue SS3) | The migration is in stasis; complete during the rewrite decision, not restoration. Piecemeal extraction during bug fixes creates a third org pattern worse than either extreme. | [SS1.1](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#11-five-months-since-last-commit-on-this-repo) |
| Don't rename `visibleEntityTypes` to `visibleAccountTypes` | Route guards SS5 | Touch only the side the guard reads (`visibleEntityTypes`). The guard ignores `visibleAccountTypes`; renaming without guard extension is a silent no-op. Full rename is a separate coordinated PR. | [SS4.2](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#42-router-guard-reads-visibleentitytypes-but-new-routes-set-visibleaccounttypes) |
| Don't introduce refresh-rotation flow | JWT + refresh rotation (api-integration SS3) | The backend's JWT lifetime is 99999 days. Adding rotation to the FE before the backend reduces the lifetime is dead code. The two PRs must ship together. | [SS5.2](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#52-refresh-tokens-issued-by-backend-are-ignored-by-fe) |
| Don't fix `tracePropagationTargets` alone | Distributed tracing (api-integration SS5) | Fixing the placeholder without deciding which APM stack to centralize on creates a half-fix. Coordinate with the backend observability consolidation. | [SS3.2](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#32-tracepropagationtargets-still-set-to-sentry-quickstart-placeholder) |
| Don't remove dead deps | General hygiene | Low risk; belongs in a dedicated cleanup PR, not mixed with feature work. | [SS7.1](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#71-stripestripe-js-listed-in-packagejson-but-never-imported) |
| Don't unify permission constant catalogues | TypeScript discipline | Both catalogues (`src/constants/permissionEnums` and `features/shared/constants/permissions`) resolve to the same backend strings. Unification is cosmetic. | [SS4.3](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#43-two-parallel-permission-constant-catalogues) |
| Don't register `features/plans/stores/` in `resetAllStores()` as a drive-by | Pinia stores -- mandatory registration (vue SS4) | Known security gap (data survives logout). Fix requires understanding the plan store's contents; don't assume it's safe to null. File as a security-review ticket. | [SS5.4](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#54-feature-stores-not-included-in-logout-reset-hierarchy) |

**What IS safe to fix during FE triage:**
- Bug fixes in existing code (in place, same organizational pattern)
- Swallowed-error fixes (`console.log(error)` -> `Sentry.captureException(error)`)
- Adding missing TypeScript types where the fix is local
- Fixing broken i18n keys or missing translations
- Route-level permission checks that are verifiably wrong

---

## The "inherited code, dormant maintainer" pattern

pour-now has two dormant FE codebases:

| Repo | Last meaningful commit | Deploy plumbing | Feature parity |
|---|---|---|---|
| `business-admin` | ~Dec 2025 | Full (Netlify, env vars, Sentry, PostHog) | Complete -- the production SPA |
| `admin-business` | Unknown (parked) | Incomplete (no Netlify config, no env setup) | Partial -- rewrite attempt |

**The load-bearing fact:** no one is actively maintaining either FE codebase. Any work done on either repo is restoration-in-the-dark -- the original developers' intent, in-progress decisions, and implicit knowledge are unavailable.

**The rule:** every FE PR opened against either repo must explicitly state which decision tree it assumes:

1. **Legacy stays alive.** The PR fixes or extends `business-admin`. The rewrite is dead. All future work happens here.
2. **Rewrite resumes.** The PR is preparatory work for migrating to `admin-business`. No new features land in `business-admin`.
3. **Neither decided yet.** The PR is a minimal fix that works regardless of which path the team picks. No structural changes, no migration work, no rewrite-preparation.

**Why this rule exists:** "I'll just fix this small thing while I'm here" PRs anchor the codebase to a future the team hasn't picked. A bug fix in `business-admin` that also migrates three components to `features/` assumes decision (1). A refactor that introduces Pinia 3 patterns assumes decision (2). Without the explicit statement, reviewers can't evaluate whether the PR's structural assumptions match the team's direction.

**The default assumption is (3)** -- minimal fix, no structural opinion -- until the team commits to (1) or (2) in a `PROJECT.md` or equivalent decision document.

---

## The two-repos decision criterion

A worked example of how to choose between resuming `business-admin` and resuming `admin-business`.

### Inputs

| Factor | `business-admin` | `admin-business` | Weight |
|---|---|---|---|
| **Feature parity** | Complete -- production SPA | Partial -- unknown coverage gaps | High |
| **Deploy plumbing** | Full (Netlify auto-detect, env vars, Sentry DSN, PostHog key, CORS allowlisted) | None visible (no `netlify.toml`, no env config, no Sentry/PostHog wiring) | High |
| **Framework currency** | Vue 3.5, Pinia 2.2, Vite 5.4, TS 5.5, Tailwind 4.1 | Vue 3.x, Pinia 3 (newer), unknown Vite/TS versions | Medium |
| **Code organization** | Mixed (legacy-by-layer + newer-by-feature, partially migrated) | Presumably by-feature throughout (rewrite intent) | Medium |
| **Known debt** | 21 deviations catalogued ([Vue Deviations](https://github.com/pour-now/business-admin/wiki/Vue-Deviations)), 6 Major | Unknown -- no audit performed | Low (unaudited debt is still debt) |
| **Maintainer capacity** | Dormant (no active FE developers) | Dormant | Critical |
| **Time to first deploy** | Zero -- it's already deployed | Unknown -- full deploy setup required | High |
| **Time to business value** | Fix a bug -> deploy -> user sees it. Hours. | Stand up deploy -> verify parity -> fix the bug -> deploy. Weeks minimum. | High |

### Decision matrix

**If maintainer capacity is zero or one part-time FE developer:**
-> Stay on `business-admin`. The deploy plumbing alone is weeks of work to recreate. One developer cannot simultaneously build deploy infra AND deliver features. The deviations catalogue makes the debt visible and manageable.

**If the team hires or assigns >= 2 FE developers AND commits to a 3+ month FE project:**
-> Evaluate `admin-business` seriously. Read the rewrite, audit its parity, estimate the deploy-setup cost. The decision becomes: is the remaining migration work less than the debt-remediation work in `business-admin`?

**If the team needs one specific FE feature shipped in < 4 weeks:**
-> `business-admin`, regardless of long-term preference. Feature parity + working deploy = the only path that meets the timeline.

### The recommendation format

The decision should be recorded in a `PROJECT.md` (or equivalent) that the next FE PR can reference:

```markdown
## FE direction (decided YYYY-MM-DD)

**Decision:** [continue business-admin | resume admin-business | not decided]

**Rationale:** [2-3 sentences citing the factors above]

**Implication for PRs:** [which decision tree from the "inherited code, dormant maintainer"
section applies by default]
```

Until this document exists, the default is **(3) -- neither decided yet**. All FE PRs are minimal fixes with no structural opinion.

---

## Cross-cutting: coupled changes

Changes that must ship on both sides. Sourced from the [Integration pages](https://github.com/pour-now/business-admin/wiki/Integration) on both wikis.

| Change | Sequencing | Triage status |
|---|---|---|
| Reduce JWT lifetime + add FE refresh rotation | **Together** -- same day | Blocked until decision on FE repo |
| Change error envelope shape | **FE first** if adding; **together** if renaming/removing | Open to either side |
| Add rate limit to unthrottled endpoint + FE backoff | **Together** if user-facing | Backend side open; FE side blocked on repo decision |
| Backend RESTifies action URLs | Backend first (both URLs work); FE migrates; backend deprecates | Post-triage |
| Switch JWT storage to httpOnly cookies | **Together** with backend CORS/CSRF changes | Rewrite-only (clean window to swap storage model) |

---

## Find-it, file-it, fix-later

The triage loop for new findings:

1. **Find it.** You encounter a deviation, bug, or debt item.
2. **File it.** Add to the relevant wiki deviations page (Django Deviations or Vue Deviations) with severity, evidence, and the skill rule it violates. Create a GitHub issue if it's actionable.
3. **Fix later.** Don't fix it in the current PR unless it's a bug that's actively breaking users. The deviations page is the backlog; the triage skill controls the prioritization.

**The exception:** security findings at Critical severity (active data exposure, credential leak, unauthenticated write access) get fixed immediately regardless of triage status. File, then fix.

## Attribution Policy

See [rule:output]. NEVER include AI or agent attribution.
