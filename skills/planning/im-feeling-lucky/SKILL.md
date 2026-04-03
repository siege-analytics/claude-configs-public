---
name: im-feeling-lucky
description: Analyze ROADMAPs and suggest top 5 items to work on next, weighted by age, dependencies, diversity, and repository context.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash
---

# I'm Feeling Lucky Skill

## Purpose

Help prioritize roadmap items by analyzing:
- **Context Relevance**: How related the item is to the current repository (highest priority)
- **Age**: How long the concept has been waiting (older = higher priority)
- **Dependencies**: How many other items are blocked by this one (more = higher priority)
- **Diversity**: How different the task is from recently completed work (more different = higher priority)

## Instructions

### 0. Determine Session Context

**Critical**: Identify the current working directory to focus recommendations.

```bash
pwd  # e.g., /Users/steveblackmon/git/electinfo/ops
```

Extract the repository name from the path (e.g., `ops`, `rundeck`, `sites`).

Then fetch that repository's existing issues:

```bash
# Get open issues for the current repo
gh issue list --repo electinfo/<repo-name> --state open --json number,title,labels,createdAt

# Get the repo's ROADMAP if it exists
cat ~/git/electinfo/<repo-name>/ROADMAP.md
```

Build a **context profile** of keywords, components, and themes from:
- Open issues in the current repo
- The repo's own ROADMAP.md
- The repo's CLAUDE.md (key services, integrations mentioned)

### 1. Gather All ROADMAPs

Find and read all ROADMAP files across electinfo repositories:

```bash
find ~/git/electinfo -name "ROADMAP.md" -o -name "ROADMAP*.md" 2>/dev/null
```

Known locations:
- `~/git/electinfo/rundeck/ROADMAP.md` - Data pipeline roadmap (primary)
- `~/git/electinfo/ops/ROADMAP.md` - Infrastructure roadmap
- `~/git/electinfo/sites/ROADMAP.md` - Web content roadmap
- `~/git/electinfo/zeppelin/ROADMAP.md` - Notebook roadmap
- `~/git/electinfo/ansible/ROADMAP.md` - Cluster bootstrap roadmap

### 2. Extract Roadmap Items

For each ROADMAP, extract items that are NOT marked as completed. Look for:
- Tasks with status indicators: `[ ]`, `Not started`, `Planned`, `In progress`
- Phase/Sprint sections with incomplete tasks
- Items in "Recommended Next Steps" or similar sections

Create a list of candidate items with:
- **Item**: Task description
- **Source**: Which ROADMAP file
- **First mentioned**: Date first appeared (use git blame/log)
- **Dependencies**: Other items that reference this one
- **Category**: e.g., infrastructure, data, frontend, pipeline, documentation

### 3. Fetch Recent Completed Tasks

Query the GitHub project board for recently closed items:

```bash
# Get recent closed issues from tasks project
gh project item-list 1 --owner electinfo --format json | \
  jq '[.items[] | select(.status == "Done")] | sort_by(.closedAt) | reverse | .[0:10]'
```

Alternative if the above doesn't work:

```bash
# Get closed issues across repos
gh search issues --owner electinfo --state closed --sort updated --limit 10 --json title,repository,closedAt,labels
```

Extract categories/themes from closed items (e.g., "spark", "hive", "static pages", "neo4j", "superset").

### 4. Calculate Scores

For each candidate roadmap item, calculate a priority score:

#### Context Relevance Score (0-30 points) **NEW - HIGHEST WEIGHT**
```
relevance_score = 0

# +30 if item is from current repo's ROADMAP
if item.source_repo == current_repo:
    relevance_score += 30

# +20 if item mentions services/components from current repo's CLAUDE.md
elif item mentions keywords from current repo context profile:
    relevance_score += 20

# +15 if item is referenced by an open issue in current repo
elif item referenced by current repo open issues:
    relevance_score += 15

# +10 if item is in a related repo (shares dependencies)
elif item.source_repo in related_repos:
    relevance_score += 10
```

**Repository relationships** (for ops context):
- `ops` relates to: all infrastructure, ArgoCD apps, Helm charts, Traefik, Vault
- `rundeck` relates to: ops (Spark, Hive, pipelines run on K8s), data processing
- `sites` relates to: ops (deployments), rundeck (static page generation)
- `zeppelin` relates to: ops (K8s deployment), rundeck (Spark jobs)
- `ansible` relates to: ops (node provisioning)

#### Age Score (0-40 points)
```
age_days = (today - first_mentioned_date).days
age_score = min(40, age_days / 7)  # 1 point per week, max 40
```

Use git to find when item first appeared:
```bash
git log --all --oneline --follow -p -- ROADMAP.md | grep -B5 "Task description"
```

#### Dependency Score (0-30 points)
```
dependency_count = number of other roadmap items that mention this item
dependency_score = min(30, dependency_count * 10)  # 10 points per dependent item
```

Look for:
- Explicit "depends on X" or "requires X" references
- Items that can't start until this one completes
- Foundation/infrastructure items that enable other work

#### Diversity Score (0-20 points)
```
category_overlap = count of recent completed tasks in same category
diversity_score = max(0, 20 - (category_overlap * 5))  # -5 per overlapping task
```

Categories to track:
- `infrastructure` - K8s, networking, storage, ArgoCD, Helm
- `data-pipeline` - Bronze/silver/gold, Hive, Spark jobs
- `graph` - Neo4j, entity resolution, Linkurious
- `frontend` - Static pages, search, web, OpenSearch
- `analytics` - Superset, dashboards, metrics, Grafana
- `cicd` - Tekton, builds, deployments
- `documentation` - CLAUDE.md, docs/

**Total Score**: Context (0-30) + Age (0-40) + Dependencies (0-30) + Diversity (0-20) = **0-120 points**

### 5. Rank and Present Results

Sort items by total score (context + age + dependencies + diversity) descending.

Present the top 5 with this format:

```markdown
## Top 5 Recommended Tasks

**Session context**: ops (infrastructure, ArgoCD, Helm, Traefik, Vault)

### 1. [Task Name] (Score: XX/120)
**Source**: rundeck/ROADMAP.md - Phase X, Task Y.Z
**Context**: +XX (related to ops via [keyword])
**Age**: XX days (+XX points, first mentioned: YYYY-MM-DD)
**Dependencies**: [List of items blocked by this] (+XX points)
**Diversity**: Category "X" - Y recent completions (+XX points)
**Why**: Brief explanation of why this ranks high

### 2. [Task Name] (Score: XX/120)
...
```

### 6. Bonus Analysis

If time permits, also report:
- **Blocked items**: Tasks explicitly waiting on something else
- **Quick wins**: Small tasks that could be done in <1 hour
- **Stale items**: Tasks >90 days old with no progress

## Example Output

```markdown
## Top 5 Recommended Tasks

**Session context**: ops (infrastructure, ArgoCD, Helm, Traefik, Vault, OpenSearch, Spark)

### 1. Task 11.4: Superset Asset SCM Export (Score: 72/120)
**Source**: rundeck/ROADMAP.md - Phase 11, Task 11.4
**Context**: +20 (mentions "ArgoCD", "Helm" from ops context)
**Age**: 7 days (+1 point)
**Dependencies**: Enables disaster recovery for Superset dashboards (+10 points)
**Diversity**: Category "analytics" - 0 recent completions (+20 points)
**Why**: High context relevance to ops, enables GitOps pattern, untouched category

### 2. Task 7.2: Financial Summary Enhancement (Score: 58/120)
**Source**: rundeck/ROADMAP.md - Phase 7, Task 7.2
**Context**: +10 (rundeck is related repo to ops)
**Age**: 14 days (+2 points)
**Dependencies**: Enriches candidate_entities used by static pages, search (+20 points)
**Diversity**: Category "data-pipeline" - 2 recent completions (+10 points)
**Why**: High dependency score - many downstream consumers benefit
```

## Checklist

- [ ] Identified current session context (repo, keywords, open issues)
- [ ] Found all ROADMAP files
- [ ] Extracted incomplete items with metadata
- [ ] Retrieved last 10 closed tasks from project board
- [ ] Calculated context relevance scores
- [ ] Calculated age scores using git history
- [ ] Identified dependency relationships
- [ ] Categorized items and scored diversity
- [ ] Ranked and presented top 5 by total score
- [ ] No AI/agent attribution in any output or recommendations
- [ ] Included score breakdown for each recommendation