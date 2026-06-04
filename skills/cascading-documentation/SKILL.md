---
name: update-docs
description: Update documentation at every cascade level (inline, files, repo, KMS) when making changes. Keeps docs federated and consistent.
user-invocable: false
---

# Instructions

1. Identify what changed and which documentation levels are affected
   1. Run `git diff --name-only` (or `git diff develop..HEAD --name-only`) to see changed files
   2. Categorize changes: new module, changed API, new feature, config change, bug fix, infrastructure
   3. Determine which documentation levels need updating (see Documentation levels below)
2. Inventory existing documentation at each level
   1. **Inline**: Read the changed files -- do docstrings, comments, and section anchors exist?
   2. **Files**: Check for README, docs/, CLAUDE.md, ROADMAP.md, SESSION_STATUS.md
      ```bash
      find . -maxdepth 2 -name "*.md" -o -name "*.rst" | head -30
      ls docs/ 2>/dev/null
      ```
   3. **Repository**: Check for wiki, GitHub Pages, Sphinx docs
      ```bash
      gh api repos/{owner}/{repo} --jq '.has_wiki, .has_pages'
      git branch -a | grep -i gh-pages
      ls docs/conf.py 2>/dev/null  # Sphinx
      ```
   4. **Knowledge management**: Check for references to external systems in CLAUDE.md or README
      ```bash
      grep -ri "confluence\|notion\|wiki\|linear\|jira" CLAUDE.md README.md 2>/dev/null
      ```
3. Determine which levels need updates (see Decision tree below)
4. Execute updates at each affected level, bottom-up (inline first, KMS last)
5. Verify consistency across levels -- no contradictions between inline docs and README, etc.
6. Use the commit skill when committing documentation changes (ticket references still required)

# Documentation philosophy

Any work worth doing is worth documenting. That is why we have skills for commits, tickets, and PRs -- each is documentation at a different level. This skill governs the documentation *of the code and systems themselves*, organized as a federation.

Like government, every level serves a different audience and purpose. Missing a level creates a gap that forces readers to reverse-engineer intent from the wrong source. A README reader should not have to read source code to understand what a project does. A code reader should not have to find a wiki page to understand what a function does.

**Document at the level closest to the thing being described.** A function's behaviour belongs in its docstring. A project's architecture belongs in its README or docs/. A cross-project integration pattern belongs in the knowledge management system.

**Abstraction increases as you move up.** Inline docs describe *how*. File docs describe *what and why*. Repo docs describe *architecture and decisions*. KMS docs describe *strategy and relationships*.

## Greenfield vs. recovery / forensic mode

The four-level model assumes documentation is *describing the system you are building*. When the project is in recovery mode -- prior maintainers gone, codebase partly abandoned, the goal is to map the actual state rather than the intended one -- the output shapes change. The same four levels still apply, but the audience is investigators, executives, and incoming engineers who need honest information about what is real now.

Documentation in recovery / forensic mode adds these shapes:

- **Last-shipped inventories.** Per-surface tables of when something was last built, last deployed, last touched in source. Stale state is information.
- **Deviation catalogues.** Departures from convention with severity ratings (Critical / Major / Minor / Suggestion). What's wrong, why it matters, what would fix it.
- **Open-question sections that feed tracking tickets.** Anything the investigation can't answer without domain knowledge becomes a labeled question and a ticket reference (see [Level 3 to Level 4 federation](#level-3-to-level-4-federation) under sync patterns).
- **"What this repo does well" framing.** When one repo holds patterns worth importing back into sibling repos, name them explicitly so future investigators know where to look for good examples.
- **Anomaly logs.** Name / domain / repo mismatches. Branches still pinned to stale upstreams. Env vars wired without code references. The forensic value is in surfacing the surprise.

In recovery mode the deliverable of an investigation may be wiki pages plus a ticket tree, with no code PR. Definition-of-done applies to the wiki PR directly; the epic plus sub-issue chain is the audit trail.

# Documentation levels

## Level 1: Inline documentation

Lives inside source files, closest to the code.

### What belongs here

- **Docstrings**: Every public function, class, and module
  - Purpose (one sentence)
  - Arguments with types
  - Return value with type
  - Raises (if applicable)
  - Example usage (for non-obvious APIs)
- **Section anchors**: Structural comments marking significant blocks
  ```python
  # === Bronze-to-Silver Transform ===
  # Converts raw FEC filings to typed Delta Lake records
  ```
- **Decision comments**: Explain *why*, not *what* -- only where the code is non-obvious
  ```python
  # Use StringType, not IntegerType -- FEC IDs have meaningful leading zeros
  ```
- **Constants and magic values**: Explain the source or reasoning
  ```python
  MAX_OVERLAP_DISTRICTS = 12  # Empirical max from census cd_zcta crosswalk
  ```

### What does NOT belong here

- Play-by-play narration of obvious code (`# increment counter`)
- TODOs without ticket references (use `# TODO(#42): ...` format)
- Commented-out code (delete it; git has history)

### Style guide

- Python: Google-style docstrings (already used in siege_utilities and enterprise)
- Bash/YAML: Comment blocks above significant sections
- SQL: Comment above each CTE or subquery explaining its role

## Level 2: Documentation files

README.md, docs/, CLAUDE.md, ROADMAP.md -- files that describe the project.

### What belongs here

- **README.md**: What this project is, how to install/use it, quickstart
- **CLAUDE.md**: Agent-facing project context, conventions, architecture notes
- **ROADMAP.md**: Planned work, phases, priorities
- **docs/**: Detailed guides, design decisions, architecture diagrams, API reference
- **SESSION_STATUS.md**: Current resumption point for ongoing work (pure-translation, siege_utilities)
- **Sample scripts / notebooks**: Working examples of key workflows

### When to update

| Change type | README | CLAUDE.md | docs/ | ROADMAP |
|-------------|--------|-----------|-------|---------|
| New module or feature | Yes | If it changes conventions | Yes (design doc) | Mark complete |
| API change | Yes (if public) | If it changes usage patterns | Yes | -- |
| Bug fix | -- | -- | If it reveals a known issue | -- |
| Config/infra change | -- | Yes (if it affects dev workflow) | Yes (if architectural) | -- |
| Dependency change | Yes (if install changes) | -- | -- | -- |

### Style guide

- Use ATX headers (`#`, `##`, `###`), not Setext (underlines)
- One sentence per line in prose (better diffs)
- Tables for structured data, not bullet lists
- Relative links between docs (`../docs/architecture.md`), not absolute URLs
- Code blocks with language tags for syntax highlighting

## Level 3: Repository-level documentation

GitHub/GitLab wiki, GitHub Pages (Sphinx/MkDocs), hosted docs site.

### What belongs here

- Architecture decisions and ADRs (Architecture Decision Records)
- Programming and style guides
- Tables of contents and cross-repo navigation
- Data dictionaries and schema catalogs
- Dependency maps
- Usability guides and tutorials
- Known errors and workarounds
- API reference (generated from docstrings)

### Detection and setup

```bash
# Check if wiki exists and is populated
gh api repos/{owner}/{repo} --jq '.has_wiki'
gh api repos/{owner}/{repo}/wiki/pages 2>/dev/null

# Check if GitHub Pages / Sphinx exists
git branch -a | grep gh-pages
ls docs/conf.py docs/source/conf.py 2>/dev/null

# Check for MkDocs
ls mkdocs.yml 2>/dev/null
```

### When repo-level docs don't exist

1. Ask the user: "This repo has no wiki or generated docs site. Should I set one up?"
2. If yes, recommend based on the project:
   - Python library → Sphinx + gh-pages (siege_utilities already uses this)
   - Multi-service project → MkDocs with navigation
   - Small project → GitHub wiki is sufficient
3. If no, ensure Level 2 docs (README, docs/) are thorough enough to compensate

### GitHub wiki: enable vs. bootstrap (two-step)

Enabling a GitHub wiki is two steps that the API only does the first of:

1. **Enable the feature.** `gh api -X PATCH repos/{owner}/{repo} -f has_wiki=true` flips the `has_wiki` boolean.
2. **Bootstrap the wiki repo.** GitHub does not create the underlying `<repo>.wiki.git` until a human clicks **Create the first page** on the wiki tab on github.com. Until that click, `git push origin master` against the wiki URL returns `Repository not found.`

When an agent needs to push to a wiki that's been enabled but not bootstrapped, stage the commits locally:

```bash
git init -q -b master
git remote add origin https://github.com/{owner}/{repo}.wiki.git
# ... write SKILL.md, Home.md, etc. ...
git add . && git commit -m "..."
# do not push yet -- repo does not exist on the remote
```

Then ask the user for a one-click bootstrap. Once they confirm, reconcile with their bootstrap commit:

```bash
git fetch origin
git rebase -X theirs origin/master master
git push origin master
```

`-X theirs` resolves any conflict in the local commits' favor (the user's bootstrap content is typically a placeholder you intend to overwrite).

When an investigation will produce multiple new wikis at once, batch the bootstrap asks into a single message rather than serializing them.

### Multi-repo projects: the consolidating-hub pattern

When a project spans multiple repos and each repo has its own wiki, designate one wiki as the **consolidating hub**. The hub's Home includes a navigation table (often called "How the rest of the system fits") that lists every other wiki with one-line scope and links to it. Every reader landing on any wiki page should be able to walk back to the hub in one hop.

Choose the hub based on which repo holds the system of record. Common choices:

- The backend / API repo when the project is FE-and-BE
- The platform repo when the project is a SaaS with multiple client SDKs
- The orchestrator repo when the project is a fleet of services

Once the hub is named, the federation rules are:

- **Hub Home lists every federated wiki** with one-line scope. Drop the row when the wiki is no longer relevant.
- **Each federated wiki links back to the hub** in its own Home, ideally in the first paragraph.
- **Cross-wiki contradictions are findings.** When investigation finds two wikis disagreeing, the contradiction is tracked at the more-canonical claim and a delta is proposed to whichever side is wrong.
- **Updates to a federated wiki don't bypass the hub.** If the hub Home's federation table needs a new row, new scope text, or a removed row, the same PR touches both wikis.

If the project doesn't have a hub yet, naming one is itself a Level 3 contribution. Propose it explicitly, then update the federation table on the hub Home.

## Level 4: Knowledge management system

Company-wide: Linear, Confluence, Notion, or equivalent.

### What belongs here

- Ticket and epic context -- is the work tracked on the right ticket?
- Project/milestone alignment -- does the milestone reflect current state?
- Cross-project knowledge at every abstraction level:
  - **High**: Business goals, initiative rationale, stakeholder context
  - **Mid**: Technical architecture spanning multiple repos, integration patterns
  - **Low**: Operational procedures, runbooks, incident postmortems
- Relationships between knowledge systems: ticket → wiki, wiki → docs, docs → code

### Detection

```bash
# Check for Linear references
grep -ri "linear\|ELE-\|SU-" CLAUDE.md README.md 2>/dev/null

# Check for other KMS references
grep -ri "confluence\|notion\|wiki\..*\.com" CLAUDE.md README.md 2>/dev/null
```

### When Level 4 doesn't exist

This is regrettable but permissible. Not every project has a company KMS. If absent:
- Ensure Levels 1-3 are strong enough to stand alone
- Recommend creating one if the project has multiple contributors or stakeholders
- Do not block documentation work on KMS availability

# Decision tree

```
Code changed?
├── Public API (function signature, class, CLI flag)?
│   ├── Update docstring (Level 1)
│   ├── Update docs/ if design doc exists (Level 2)
│   ├── Update API reference if Sphinx/generated docs exist (Level 3)
│   └── Update ticket with scope change if significant (Level 4)
├── New module or feature?
│   ├── Add docstrings to all public functions (Level 1)
│   ├── Add section to README or create design doc in docs/ (Level 2)
│   ├── Update wiki/generated docs navigation (Level 3)
│   └── Ensure ticket/epic reflects the new scope (Level 4)
├── Bug fix?
│   ├── Add comment explaining the fix if non-obvious (Level 1)
│   ├── Update known issues in docs/ if applicable (Level 2)
│   └── Update ticket with resolution details (Level 4)
├── Config or infrastructure change?
│   ├── Comment the config file (Level 1)
│   ├── Update CLAUDE.md if it affects dev workflow (Level 2)
│   └── Update architecture docs if significant (Level 2/3)
└── Documentation-only change?
    ├── Ensure consistency across all levels
    └── Cross-reference between levels where helpful
```

# Style guide negotiation

When starting documentation work in a new repo:

1. **Check for existing style guides**:
   ```bash
   find . -iname "*style*" -o -iname "*contributing*" -o -iname ".editorconfig" | head -10
   grep -ri "style guide\|documentation standard" CLAUDE.md README.md CONTRIBUTING.md 2>/dev/null
   ```
2. **If guides exist**: Follow them. If they conflict with best practices, note the conflict to the user and suggest improvements -- but accept the user's decision.
3. **If no guides exist**: Announce which conventions you will use:
   - Python docstrings: Google style
   - Markdown: CommonMark with ATX headers
   - Commit messages: type-prefixed (per commit skill)
   - Line width: 80 chars for prose, no limit for code/tables
4. **Apply consistently** across all levels. A project should not use Google docstrings in source but NumPy docstrings in docs/.

# Syncs between levels

Documentation levels may feed each other through automated or semi-automated transforms.

### Common sync patterns

| Source | Target | Mechanism |
|--------|--------|-----------|
| Docstrings (L1) | API reference (L3) | Sphinx autodoc, MkDocs mkdocstrings |
| CHANGELOG.md (L2) | Release notes (L3/L4) | GitHub Releases, `gh release create --notes-file` |
| Design docs (L2) | Wiki pages (L3) | Manual sync or git submodule |
| Polished repo docs (L2) | Wiki pages (L3) | [Repo-canonical lift](#repo-canonical-lift) -- bidirectional |
| Wiki section (L3) ↔ Tracking ticket (L4) | each other | [Level 3 to Level 4 federation](#level-3-to-level-4-federation) -- bidirectional |
| Tickets (L4) | ROADMAP.md (L2) | Manual sync -- update ROADMAP when epics close |

### Repo-canonical lift

When a repo has polished documentation files (HANDOFF.md, DEPLOY.md, MIGRATION.md, ARCHITECTURE.md) and the goal is to make them discoverable in a wiki, **lift them with a top-of-page admonition** rather than rewriting from scratch:

```markdown
# Deploy -- {service}, {key-property}

> Source: lifted from the repo's [`DEPLOY.md`](https://github.com/{owner}/{repo}/blob/main/DEPLOY.md).
> That file in the repo is the source of truth -- when it changes, this wiki page should be
> updated to match (or vice versa, and PR back).

{lifted content}
```

The repo file remains canonical. The wiki page is a mirror with a bidirectional update obligation: editing either side without updating the other is a violation visible to readers.

Cross-repo references in the original (`[DEPLOY.md](DEPLOY.md)`, `[MIGRATION.md](MIGRATION.md)`) rewrite to wiki cross-links (`[Deploy](Deploy)`, `[Database Setup](Database-Setup)`). Absolute filesystem paths (`~/Documents/Code/<repo>`) genericize (`/path/to/your/clone/<repo>`). Repo file references in the original keep their absolute URLs so they survive the wiki rendering context.

### Level 3 to Level 4 federation

When wiki documentation surfaces a decision or unanswered question, federate it across Level 3 (wiki) and Level 4 (tracking tickets) bidirectionally:

- The wiki page's "Open questions" section names the question and links to the tracking ticket. Example phrasing: *"Tracked as urgent on the {owner}/{repo} repo: issue #N. Answer in that thread; this section gets rewritten with the resolutions when the ticket closes."*
- The tracking ticket links back to the specific wiki section so anyone reading the ticket can find the forensic detail.
- Decisions requiring leadership input roll up to an epic. Each sub-issue is self-contained for an executive reading it, cross-linking to the most-relevant wiki section and to the parent epic.

When a decision closes, the wiki section is rewritten with the resolution (delete the question, replace with the answer + commit/PR reference) in the same PR that closes the ticket. Wiki and ticket are then back in sync.

This pattern works equally well for non-recovery investigations -- any time the wiki captures decisions that need more than a docs-only fix, the bidirectional sync prevents the ticket and the wiki from drifting apart.

### When updating syncs

1. Identify which syncs exist:
   ```bash
   # Check for Sphinx autodoc
   grep -r "autodoc\|automodule\|autoclass" docs/ 2>/dev/null
   # Check for generated files
   grep -ri "auto-generated\|do not edit" docs/ 2>/dev/null
   ```
2. Track what is automatically generated vs. manually maintained -- never hand-edit generated files
3. If a change affects a sync source, trigger the rebuild:
   ```bash
   # Sphinx
   cd docs && make html
   # MkDocs
   mkdocs build
   ```
4. If the sync introduces a significant change (new module in API docs, restructured navigation), get user approval before committing

# Executing documentation updates

Work bottom-up: inline → files → repo → KMS. Each level builds on the one below.

1. **Inline (Level 1)**: Add or update docstrings and comments in changed files
2. **Files (Level 2)**: Update README, CLAUDE.md, docs/ as needed
3. **Repo (Level 3)**: Rebuild generated docs, update wiki if applicable
4. **KMS (Level 4)**: Update tickets, milestones, project boards

For each level:
- Read the existing documentation before modifying (match tone and structure)
- Write for the audience at that level (developer, contributor, stakeholder)
- Cross-reference other levels where helpful (`See [architecture docs](../docs/architecture.md)`)
- Verify no contradictions between levels after updating

# Attribution policy

**NEVER** include AI or agent attribution in documentation at any level. This includes:
- No "Generated with Claude Code", "Made with Cursor", "Built with Codex", or any AI tool mentions
- No `🤖`, `[bot]`, or other markers that signal AI involvement
- No attribution to any AI assistant, code generation tool, or agent framework
- This applies to docstrings, README files, wiki pages, design docs, and all other documentation

# Checklist

- [ ] Identified which documentation levels exist for this repo
- [ ] Determined which levels are affected by the current change
- [ ] **Level 1**: Docstrings and comments are current for changed code
- [ ] **Level 2**: README, CLAUDE.md, docs/ updated if applicable
- [ ] **Level 3**: Generated docs rebuilt, wiki updated if applicable
- [ ] **Level 4**: Tickets and project boards reflect current state (if KMS exists)
- [ ] Style guides detected and followed (or announced if none exist)
- [ ] No contradictions between documentation levels
- [ ] Sync mechanisms identified and triggered where applicable
- [ ] No auto-generated files were hand-edited
- [ ] No AI/agent attribution anywhere in documentation
- [ ] Documentation changes committed with ticket references (per commit skill)
