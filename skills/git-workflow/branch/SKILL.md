---
name: branch
description: Create and manage git branches using a consistent naming convention (type/descriptive_string) that mirrors ticket taxonomy
---

# Instructions

1. Determine the branch type from context
   1. Read the ticket or task that motivates this branch
   2. Map the work to a branch type (see Branch types below)
   3. If no ticket exists, create one first -- if the work is branchable, it is ticketable
2. Choose the base branch
   1. Branch from `develop` (or its synonym -- see Develop detection below)
   2. If no `develop` branch exists, create one from `main` before branching (see Develop guard below)
   3. **Never** branch directly from `main` for feature or task work
3. Create the branch with the correct naming convention
4. Push the branch to the remote

# Branch philosophy

A branch is a workspace for a ticket. Just as every commit should reference a ticket, every branch should correspond to a ticket. The branch name communicates what kind of work is happening and what it's about, without anyone needing to read the code.

**One branch, one ticket.** If a branch addresses multiple tickets, it should be split. If a ticket requires multiple branches (rare), they should be coordinated under an epic.

**Branches are temporary.** They exist to isolate work until it's ready for review. Once merged, they should be deleted. Long-lived branches (beyond `main` and `develop`) are a smell.

# Branch types

Branch types mirror the ticket taxonomy. The same concepts apply, just expressed in a path prefix.

| Branch type | When to use | Ticket type equivalent |
|-------------|-------------|----------------------|
| `bugfix/` | Correcting behaviour that deviates from intent | bugfix |
| `feature/` | Adding new behaviour or capability | feature |
| `task/` | Refactoring, cleanup, infrastructure, docs, tests, CI | task |
| `chore/` | Routine maintenance that doesn't change behaviour (dependency bumps, config updates, formatting) | task (subset) |
| `hotfix/` | Urgent production fix that must bypass the normal flow (may go directly to `main`) | bugfix (urgent) |

### Synonyms

Some teams use different terminology for the same concepts. Recognise these as equivalent:

| Canonical | Synonyms |
|-----------|----------|
| `bugfix/` | `fix/`, `bug/`, `patch/` |
| `feature/` | `feat/`, `enhancement/` |
| `task/` | `refactor/`, `tech/`, `infra/`, `docs/`, `test/` |
| `chore/` | `maintenance/`, `deps/`, `ci/` |
| `hotfix/` | `emergency/`, `critical/` |

When reading existing branches, map synonyms to the canonical type. When creating new branches, use the canonical type.

# Naming convention

```
{type}/{descriptive_string}
```

## Rules

1. **Type prefix** from the table above, followed by `/`
2. **Descriptive string** in `snake_case` -- lowercase, words separated by underscores
3. **Be specific** -- `feature/add_geographic_enrichment` not `feature/geo`
4. **Include ticket ID when useful** -- `bugfix/en_328_fix_geoid_padding` ties the branch to the ticket
5. **Keep it under 60 characters total** -- branch names appear in prompts, logs, and CI
6. **No special characters** beyond `/`, `-`, and `_`

## Examples

```
bugfix/fix_committee_id_leading_zeros
bugfix/en_328_fix_geoid_padding
feature/geographic_enrichment_phase1
feature/enterprise_parametric_api
task/split_census_into_subpackage
task/update_delta_schema_docs
chore/bump_pyspark_to_4_1
chore/fix_ruff_lint_violations
hotfix/restore_spark_connect_after_sedona_crash
```

## Anti-patterns

```
# Too vague
feature/update
bugfix/fix

# No type prefix
geographic-enrichment
fix-committee-ids

# CamelCase or mixed case
feature/AddGeographicEnrichment
Feature/geographic_enrichment

# Spaces or special characters
feature/add geographic enrichment
feature/add@geographic#enrichment
```

# Develop detection

Before creating a branch, check whether a `develop` branch (or synonym) exists:

```bash
# Check for develop or synonyms
git branch -a | grep -iE '(develop|dev|development|staging|next|integration)$'
```

### Common synonyms for develop

| Canonical | Synonyms |
|-----------|----------|
| `develop` | `dev`, `development`, `staging`, `next`, `integration` |

If found, use the existing branch as the integration branch. If none exists, see the Develop guard skill -- create `develop` from `main` before proceeding.

# Creating a branch

```bash
# Ensure develop is up to date
git checkout develop
git pull origin develop

# Create the new branch
git checkout -b feature/geographic_enrichment_phase1

# Push to remote with tracking
git push -u origin feature/geographic_enrichment_phase1
```

# After creating the branch

1. **Update the ticket** -- Add a comment noting that work has started and which branch it's on
2. **Set the ticket status** to "In Progress" (or equivalent)
3. **Begin work** -- Make commits that reference the ticket (see commit skill)

# Cleaning up branches

After a branch has been merged:

```bash
# Delete local branch
git branch -d feature/geographic_enrichment_phase1

# Delete remote branch
git push origin --delete feature/geographic_enrichment_phase1
```

Never delete branches that haven't been merged without confirming with the user.

# Attribution policy

**NEVER** include AI or agent attribution in branch names, descriptions, or related comments. This includes:
- No `claude/`, `ai/`, `bot/`, or similar prefixes
- No AI tool mentions in any ticket updates about the branch

# Checklist

- [ ] Branch type matches the work being done (bugfix, feature, task, chore, hotfix)
- [ ] Descriptive string is specific, snake_case, under 60 chars total
- [ ] Branched from `develop` (not `main`) unless this is a hotfix
- [ ] If no develop branch existed, one was created first
- [ ] Ticket exists for this work (if branchable, it's ticketable)
- [ ] Branch pushed to remote with tracking (`-u`)
- [ ] Ticket updated with branch name and status set to In Progress
