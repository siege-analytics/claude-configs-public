---
name: update-notion
description: Author and maintain the Notion knowledge base — accessible, 5th-grade-reading-level pages explaining what we build, how, why, and for whom. Works through the electinfo/sync system.
---

# Instructions

1. Determine what content needs to be created or updated
   1. What changed? New feature, new data source, architecture shift, new client, new technology?
   2. Which Notion pages are affected? (See Page map below)
   3. Is this a new page, an update to existing content, or a sync job enhancement?
2. Identify the correct team space and page location (see Team spaces below)
3. Write or update content at a 5th-grade reading level (see Writing rules below)
4. Determine implementation path:
   - **Sync-managed pages** (auto-rebuilt hourly): edit the sync job in `electinfo/sync/sync/jobs/`
   - **Manual pages** (human-curated): edit directly via Notion API
   - **New pages**: create via Notion API, then decide if a sync job should maintain it
5. Verify cross-references between pages — every page should link to related pages
6. Ensure the reading map ("How to Read This") is updated if page structure changed

# Philosophy

The Notion knowledge base exists for people who are **not** reading the code. It serves:
- **Leena** (PM): needs to track progress, explain the project to stakeholders, plan sprints
- **Steve** (downstream engineer): needs to understand upstream data contracts
- **Dheeraj** (engineer, product, CTO): needs documentation of every part of data and technology choices, progress to completion and project dependencies
- **Clients** (LegiNation, future): need to understand what data is available and how to use it
- **Future team members**: need onboarding material that doesn't assume existing context

Every page should be understandable by someone who has never seen a terminal. Technical terms must be defined the first time they appear. Diagrams should be labeled. Numbers should have context ("6 million records — roughly one for every campaign donation filed with the federal government since 2001").

This is **not** developer documentation — that lives in the code (see `update-docs` skill). This is knowledge management for the organisation.

# Infrastructure

## The sync system

The Notion knowledge base is maintained by a sync system under version control:

```
~/git/electinfo/sync/
├── sync/
│   ├── config/__init__.py       # API keys, Notion page/DB IDs
│   ├── clients/
│   │   ├── linear.py            # Linear GraphQL client
│   │   └── notion.py            # Notion REST client
│   ├── jobs/
│   │   ├── dashboard.py         # Linear projects → Project Dashboard DB
│   │   ├── hud.py               # Team activity → Heads Up Display page
│   │   ├── states.py            # State research → State Data Collection DB
│   │   ├── stats.py             # Summary stats callout
│   │   ├── what_building.py     # Product description page
│   │   ├── data_charts.py       # Pie charts from state data
│   │   └── deps_diagrams.py     # Architecture diagrams (kroki.io)
│   └── run.py                   # CLI: python -m sync.run [job ...]
└── CLAUDE.md
```

**Cron**: Runs hourly at :17 on cyberpower.
**Log**: `/tmp/linear-notion-sync.log`

### Running sync jobs

```bash
cd ~/git/electinfo/sync
python -m sync.run                  # All jobs
python -m sync.run dashboard hud    # Specific jobs
python -m sync.run what_building    # Single job
```

### Adding a new sync job

1. Create `sync/jobs/my_job.py` with a `run()` function
2. Register it in `sync/run.py` JOBS dict
3. Test: `python -m sync.run my_job`
4. Commit to `electinfo/sync`

## Notion workspace structure

```
Elect Info Telemetry                     (TELEMETRY_PAGE)
├── Project Dashboard [DB]               (PROJECT_DASHBOARD_DB)  ← sync: dashboard.py
├── Heads Up Display                     (HUD_PAGE)              ← sync: hud.py
├── What We're Building                  (WHAT_BUILDING_PAGE)    ← sync: what_building.py
├── How to Read This                     (manual — reading map)
├── Data                                 (DATA_PAGE)             ← sync: data_charts.py
│   └── [sub-pages per data source]      (manual)
├── State Data Collection Status [DB]    (STATE_DATA_DB)         ← sync: states.py
├── System Dependencies                  (SYSTEM_DEPS_PAGE)      ← sync: deps_diagrams.py
├── User Feedback [DB]                   (USER_FEEDBACK_DB)      (manual)
└── [team space pages — see below]
```

Page IDs are in `sync/config/__init__.py`. When creating new pages, add the ID there.

# Team spaces

Content must land in the correct team space. Each team has a different audience and reading level.

| Team | Linear key | Audience | Content focus |
|------|-----------|----------|---------------|
| Leadership (LEA2) | Strategy, investors, board | What we're building, why it matters, market position, timelines |
| Sales/Marketing/Accounts (SAL) | Clients, prospects, partners | What data is available, how clients use it, case studies, pricing context |
| Operations (OPE) | PM (Leena), project coordinators | Sprint status, who's doing what, blockers, dependencies, delivery dates |
| Engineering (ELE) | Dheeraj, Steve, future engineers | Architecture decisions, data contracts, deployment procedures, incident postmortems |

### Routing decision

```
Who needs to read this?
├── Investors / board → Leadership space
├── Clients / prospects → Sales space
├── PM / coordinators → Operations space
├── Engineers → Engineering space (or code-level docs via update-docs skill)
└── Everyone → Top-level Telemetry page (What We're Building, How to Read This)
```

# Content types

Each content type has a standard structure. Follow these templates.

## Data source page

Explains where data comes from, what it contains, and why it matters.

```markdown
# [Source Name]
   (e.g., "FEC Federal Campaign Finance", "New Jersey ELEC", "US Census ACS")

## What this data is
   Plain-language description. What does a single record represent?
   Example: "Every time someone donates money to a federal political campaign,
   the campaign must report it to the Federal Election Commission. This data
   is one row per donation."

## Why it matters
   What questions can this data answer? Who cares about the answers?

## Where we get it
   URL, API, FOIA, scrape, purchase. Include update frequency.
   "The FEC publishes new filings every day at [link]. We download them nightly."

## What it looks like
   Key fields, explained in plain language. A table with:
   | Field | What it means | Example |
   |-------|--------------|---------|

## How much we have
   Row counts, date ranges, geographic coverage. Use concrete numbers.
   "6.1 million individual donations from 2001 to today, covering all 50 states."

## Known limitations
   What's missing, what's messy, what we can't trust.
   "Addresses before 2005 often lack ZIP+4, so we can't always assign
   the exact congressional district."
```

## Technology page

Explains a technology choice to a non-technical reader.

```markdown
# [Technology Name]
   (e.g., "Apache Spark", "Neo4j", "Delta Lake")

## What it does (one paragraph)
   No jargon. Use analogies.
   "Spark is like a team of workers who split a big job into small pieces
   and work on all the pieces at the same time. Instead of one computer
   reading 6 million records one by one, Spark divides them across many
   computers so the job finishes in minutes instead of hours."

## Why we use it
   The specific problem it solves for us. Not why it's good in general.

## What we considered instead
   Other options and why they didn't fit.
   | Option | Why not |
   |--------|---------|

## Where it runs
   Physical location, cloud/on-prem, who maintains it.

## Who interacts with it
   Which team members, which automated systems.
```

## Stakeholder value page

Explains who gets what from the system.

```markdown
# [Stakeholder Group]
   (e.g., "Campaign Strategists", "Journalists", "Academic Researchers")

## What they need
   The questions they're trying to answer.

## What we give them
   Specific data products, reports, API endpoints, dashboards.

## How they access it
   Portal, API, CSV export, custom report, static pages.

## Example use case
   A concrete scenario, narrated step by step.
   "A campaign manager in NJ-7 wants to know which ZIP codes have the
   highest donor density for her opponent. She opens the API, queries..."
```

## Reading map page ("How to Read This")

This is the front door. It tells a new reader where to start and how to navigate.

```markdown
# How to Read This

## If you want to know what we're building
   → Start with [What We're Building]
   → Then read [System Dependencies] for how the pieces fit together

## If you want to know how the project is going
   → Check the [Heads Up Display] for today's status
   → See the [Project Dashboard] for progress by project

## If you want to understand a specific data source
   → Go to [Data] and find the source you're interested in

## If you want to understand a technology choice
   → Find it under [System Dependencies] or the relevant team space

## If you want to know what's blocked or needs attention
   → The [Heads Up Display] shows blocked items at the top
```

# Writing rules

## Reading level: 5th grade

Every page must be understandable by a smart 12-year-old. This means:

1. **Short sentences.** Under 20 words when possible. One idea per sentence.
2. **Common words.** "Use" not "utilise". "Send" not "transmit". "Fix" not "remediate".
3. **Define terms.** First use of any technical term gets a plain-language definition.
   - Bad: "We use DLT for CDC on Delta tables."
   - Good: "We use a system called Delta Live Tables to track changes in our data. When a new campaign donation is filed, only that new record gets processed — we don't have to redo everything from scratch."
4. **Concrete numbers.** "6 million records" not "a large dataset". "50 states" not "nationwide".
5. **Analogies.** Compare technical concepts to everyday things.
   - "A knowledge graph is like a map of relationships. Instead of showing roads between cities, it shows connections between people, organisations, and money."
6. **Active voice.** "The pipeline downloads new filings every night" not "New filings are downloaded nightly by the pipeline."
7. **No acronyms without expansion.** First use: "Federal Election Commission (FEC)". After that: "FEC".
8. **Paragraphs under 4 sentences.** Break up walls of text.

## Tone

- Confident but not boastful
- Informative but not lecturing
- Specific but not overwhelming
- Use "we" for the team, name individuals when relevant ("Dheeraj builds the data warehouse, Steve builds the public website")

## Formatting for Notion

- Use callout blocks for key takeaways (blue background for info, green for success, red for warnings)
- Use toggle blocks for detail that most readers can skip
- Use tables for structured comparisons
- Use numbered lists for sequences, bullet lists for unordered items
- Use dividers between major sections
- Embed diagrams via kroki.io (see `deps_diagrams.py` for the pattern)
- Link to Linear projects by slug URL: `https://linear.app/elect-info/project/{slug}`
- Link to GitHub repos: `https://github.com/electinfo/{repo}`

# Decision tree: sync job vs. manual page

```
Is this content derived from Linear or GitHub data?
├── Yes → Should be a sync job (auto-rebuilt hourly)
│   ├── Does a sync job already cover this? → Update the existing job
│   └── New content area → Create a new sync job in sync/jobs/
└── No → Manual page (curated by humans)
    ├── Will it change frequently? → Consider making it a sync job later
    └── Stable content → Create via Notion API, maintain by hand
```

### When to create a new sync job

- The content is derived from structured data (Linear projects, GitHub issues, state DB)
- It changes frequently enough that manual updates would fall behind
- The content follows a repeatable template (not free-form prose)

### When to create a manual page

- The content requires human judgment and narrative (stakeholder value, technology rationale)
- It changes rarely (architecture decisions, data source descriptions)
- It needs a specific editorial voice

# Execution workflow

## Creating a new page

1. Determine the content type (data source, technology, stakeholder, reading map)
2. Determine the team space (Leadership, Sales, Operations, Engineering)
3. Write the content following the appropriate template and writing rules
4. Create the page via Notion API:
   ```bash
   # Use the sync client for consistency
   cd ~/git/electinfo/sync
   python3 -c "
   from sync.clients import notion
   from sync.config import TELEMETRY_PAGE  # or appropriate parent
   # Create page, add blocks...
   "
   ```
5. Add the page ID to `sync/config/__init__.py` if it will be referenced by sync jobs
6. Update the reading map ("How to Read This") with a pointer to the new page
7. Verify cross-references: does this page link to related pages? Do related pages link back?

## Updating an existing sync-managed page

1. Edit the sync job in `sync/jobs/`
2. Test locally: `python -m sync.run <job_name>`
3. Review the Notion page to verify rendering
4. Commit the change to `electinfo/sync`

## Updating a manual page

1. Read the current page content via Notion API
2. Edit using the Notion block API (append, patch, or delete+recreate)
3. Verify the rendering
4. If the page now has enough structure to justify a sync job, propose creating one

# Cross-level sync with update-docs

This skill (update-notion) and the cascading-documentation skill (update-docs) are complementary:

| Level | Owner | Skill |
|-------|-------|-------|
| Inline docs (code) | update-docs | Developers read code |
| File docs (README, docs/) | update-docs | Contributors read repos |
| Repo docs (wiki, Sphinx) | update-docs | Contributors and advanced users |
| Knowledge base (Notion) | **update-notion** | Everyone else |

**Flow**: Technical changes → update-docs updates code-level documentation → update-notion translates the *impact* of those changes into accessible Notion pages.

A change to a Spark transform doesn't need a Notion page. But if that change means "we can now process state-level data, not just federal" — that's a Notion page for Leadership, Sales, and Operations.

# Attribution policy

**NEVER** include AI or agent attribution in Notion pages, comments, or any content. This includes:
- No "Generated with Claude Code", "Made with Cursor", "Built with Codex", or any AI tool mentions
- No bot markers, AI assistant references, or agent framework attribution
- This applies to page content, comments, database entries, and callout blocks

# Checklist

- [ ] Content type identified (data source, technology, stakeholder, reading map, status)
- [ ] Correct team space selected (Leadership, Sales, Operations, Engineering)
- [ ] Content written at 5th-grade reading level — no unexplained jargon
- [ ] Technical terms defined on first use
- [ ] Concrete numbers and examples throughout
- [ ] Implementation path chosen (sync job vs. manual page)
- [ ] If sync job: tested locally, committed to electinfo/sync
- [ ] If manual page: page ID recorded in sync/config if needed
- [ ] Reading map ("How to Read This") updated if page structure changed
- [ ] Cross-references verified — related pages link to each other
- [ ] Cross-level sync considered — does update-docs also need to run?
- [ ] No AI/agent attribution anywhere in content
