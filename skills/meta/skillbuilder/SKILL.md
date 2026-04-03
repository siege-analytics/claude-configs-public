---
name: skillbuilder
description: Create, audit, and fix Claude Code skills per Anthropic's official guidelines. Enforces frontmatter, line limits, description length, and skill classification.
disable-model-invocation: true
allowed-tools: Read Grep Glob Write Edit
argument-hint: [create|audit|fix] [skill-name-or-path]
---

# Skillbuilder

Build and maintain Claude Code skills that conform to Anthropic's specification.

## Commands

- `/skillbuilder create <name>` — scaffold a new skill with correct structure
- `/skillbuilder audit [path]` — audit one skill or all skills in a directory
- `/skillbuilder fix <path>` — fix a skill's compliance issues

## Skill Classification

Every skill is one of three types. The type determines which frontmatter fields to set.

### Reference

Knowledge Claude should absorb automatically when relevant. Not invoked as a slash command — Claude applies it when the context matches.

**Examples:** coding style, SQL conventions, spatial decision frameworks, API design patterns.

**Required frontmatter:**
```yaml
user-invocable: false
```

**Characteristics:**
- Describes *how to think* about a domain, not *steps to execute*
- No side effects — purely informational
- Claude auto-invokes when it detects relevant work (writing Python, reviewing SQL, etc.)
- The `description` field is critical — it's how Claude decides when to load the skill
- The `paths` field helps scope activation (e.g., `paths: "**/*.py"` for Python style)

### Action

Workflows with side effects that the user invokes explicitly. Claude should never auto-invoke these.

**Examples:** commit, merge, create-pr, deploy, close-ticket, wrap-up.

**Required frontmatter:**
```yaml
disable-model-invocation: true
```

**Characteristics:**
- Executes steps that change state (git, APIs, file system, external services)
- User triggers via `/skill-name`
- Often accepts arguments (`$ARGUMENTS`)
- Should specify `allowed-tools` for the tools it needs
- Should include `argument-hint` if it accepts parameters

### Analytical

Analysis that produces output or recommendations. No destructive side effects, but does real work that the user initiates.

**Examples:** code-review, im-feeling-lucky, audit, consolidate.

**Required frontmatter:**
```yaml
disable-model-invocation: true
allowed-tools: Read Grep Glob
```

**Characteristics:**
- Reads and analyzes code, data, or project state
- Produces structured output (findings, rankings, recommendations)
- User triggers via `/skill-name` because it does substantive work
- Read-only tools are usually sufficient
- Often accepts a focus argument (`$ARGUMENTS`)

## Anthropic Specification Reference

### File Structure

```
skill-name/
├── SKILL.md              # Required. Main instructions. ≤500 lines.
├── reference.md          # Optional. Detailed reference material.
├── examples.md           # Optional. Worked examples and patterns.
└── scripts/              # Optional. Helper scripts.
    └── helper.py
```

`SKILL.md` is the only required file. Supporting files are loaded by Claude when referenced.

### Frontmatter Fields

| Field | Type | Max | Purpose |
|-------|------|-----|---------|
| `name` | string | 64 chars | Slash command name. Lowercase, hyphens, numbers only. |
| `description` | string | 250 chars | What it does and when to use it. Claude uses this for auto-invocation decisions. **Front-load the key use case.** |
| `disable-model-invocation` | boolean | — | `true` = user-only. Set for Action and Analytical skills. |
| `user-invocable` | boolean | — | `false` = Claude-only. Set for Reference skills. |
| `allowed-tools` | string/list | — | Tools Claude can use without asking. Space-separated. |
| `argument-hint` | string | — | Shown in autocomplete. E.g., `[issue-number]` |
| `paths` | string/list | — | Glob patterns limiting auto-activation scope. |
| `context` | string | — | `fork` to run in isolated subagent context. |
| `agent` | string | — | Subagent type when `context: fork`. |
| `model` | string | — | Model override when skill is active. |
| `effort` | string | — | `low`, `medium`, `high`, `max`. |

### Hard Constraints

| Constraint | Limit |
|-----------|-------|
| `SKILL.md` length | ≤ 500 lines |
| `name` | ≤ 64 chars, lowercase + hyphens + numbers |
| `description` | ≤ 250 chars (truncated in listings beyond this) |
| Frontmatter | Valid YAML between `---` markers |

### String Substitutions

| Variable | Expands To |
|----------|-----------|
| `$ARGUMENTS` | All arguments passed when invoking |
| `$ARGUMENTS[N]` | Specific argument (0-based) |
| `$0`, `$1`, ... | Shorthand for `$ARGUMENTS[N]` |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing the SKILL.md |

### Dynamic Context Injection

Use `` !`command` `` to inject shell output into the skill before Claude sees it:

```markdown
Current branch: !`git branch --show-current`
Recent changes: !`git log --oneline -5`
```

## Creating a New Skill

### Step 1: Classify

Determine the skill type:

| Question | If Yes |
|----------|--------|
| Does it change state? (git, APIs, files, deployments) | **Action** |
| Does it analyze and produce findings/recommendations? | **Analytical** |
| Is it knowledge Claude should apply automatically? | **Reference** |

### Step 2: Scaffold

Create the directory and SKILL.md:

```
<skill-category>/<skill-name>/SKILL.md
```

Categories in this repo: `coding/`, `analysis/`, `documentation/`, `git-workflow/`, `planning/`, `session/`, `maintenance/`, `meta/`.

### Step 3: Write the Frontmatter

Start with the classification template:

**Reference:**
```yaml
---
name: <name>
description: <≤250 chars, front-load the domain and trigger conditions>
user-invocable: false
paths: "<glob pattern for relevant files>"
---
```

**Action:**
```yaml
---
name: <name>
description: <≤250 chars, front-load what it does>
disable-model-invocation: true
allowed-tools: <tools needed>
argument-hint: <expected arguments>
---
```

**Analytical:**
```yaml
---
name: <name>
description: <≤250 chars, front-load the analysis type>
disable-model-invocation: true
allowed-tools: Read Grep Glob
argument-hint: <optional focus area>
---
```

### Step 4: Write the Body

**Rules:**
- Lead with a one-line purpose statement
- Use numbered steps for Action skills, decision trees for Reference skills, structured output templates for Analytical skills
- Keep SKILL.md ≤ 500 lines
- Move detailed reference material (tables, examples, long lists) to `reference.md`
- Move worked examples to `examples.md`
- Reference supporting files with relative links: `See [reference.md](reference.md) for details`
- Use `$ARGUMENTS` where the skill accepts parameters
- Use `` !`command` `` for dynamic context that should be fresh each invocation

### Step 5: Validate

Check against this list:

- [ ] `name`: ≤ 64 chars, lowercase + hyphens + numbers only
- [ ] `description`: ≤ 250 chars, front-loads the use case
- [ ] Classification frontmatter set (`disable-model-invocation` or `user-invocable`)
- [ ] `SKILL.md` ≤ 500 lines
- [ ] No org-specific content if this is a public/shared skill
- [ ] Supporting files referenced if SKILL.md would otherwise exceed 500 lines
- [ ] `allowed-tools` set for Action/Analytical skills
- [ ] `argument-hint` set if the skill accepts arguments
- [ ] `$ARGUMENTS` used in body if arguments are expected
- [ ] Attribution policy: no AI/agent attribution in any output

## Auditing Existing Skills

When auditing, check each skill for:

### Compliance

| Check | Pass Condition |
|-------|---------------|
| Line count | ≤ 500 |
| Description length | ≤ 250 chars |
| Name format | Lowercase, hyphens, numbers, ≤ 64 chars |
| Valid YAML | Frontmatter parses without errors |
| Classification | Has `disable-model-invocation` OR `user-invocable` set |

### Quality

| Check | Pass Condition |
|-------|---------------|
| Description specificity | Front-loads the use case; Claude can decide relevance from description alone |
| Body structure | Matches classification pattern (steps / decision tree / output template) |
| Portability | No hardcoded paths, org names, or credentials (for public skills) |
| Supporting files | Reference material extracted if SKILL.md > 300 lines |
| Tool specification | `allowed-tools` lists only what's needed |
| Arguments | `argument-hint` present if `$ARGUMENTS` used in body |

### Report Format

```markdown
## Audit: <skill-name>

**Classification:** Reference / Action / Analytical
**Lines:** N / 500
**Description:** N / 250 chars

### Compliance
- [x] Line count
- [ ] Description length (N chars, over by M)
- [x] Name format
- [x] Valid YAML
- [ ] Classification frontmatter missing

### Quality
- [ ] Should extract reference.md (N lines of reference material)
- [x] Portable (no org-specific content)

### Recommended Changes
1. ...
```

## Splitting Skills with Reference Files

When a skill exceeds 300 lines, consider extracting material:

| Content Type | Extract To | Reference In SKILL.md |
|-------------|-----------|----------------------|
| Lookup tables, comparison charts | `reference.md` | `See [reference.md](reference.md) for the full comparison table` |
| Worked examples, before/after code | `examples.md` | `See [examples.md](examples.md) for patterns` |
| Templates, boilerplate | `templates/` | `Use the template in [templates/job.py](templates/job.py)` |
| Helper scripts | `scripts/` | `Run the helper: ${CLAUDE_SKILL_DIR}/scripts/check.sh` |

**What stays in SKILL.md:**
- Frontmatter
- Purpose statement
- Decision trees and classification logic
- Step-by-step instructions
- Validation checklist
- Links to supporting files

**What moves out:**
- Long code examples (>20 lines each)
- Reference tables with >10 rows
- Technology comparison matrices
- Anti-pattern catalogs
- Format/dialect-specific details

## Attribution Policy

NEVER include AI or agent attribution in skills, commits, or documentation.
