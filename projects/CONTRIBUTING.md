# Contributing a Project

This directory holds **project-specific** rules and skills that supplement the general set published in `skills/`. Project content is owned by a single repository, scoped to that repository, and prefix-flattened at publish time so the flat slug fully encodes the project namespace.

## File layout

```
projects/
  <project-slug>/
    PROJECT.md              # Manifest (frontmatter + key invariants prose)
    _rules.md               # Project-specific rules + Overrides table
    skills/
      <skill-name>/
        SKILL.md            # Project-specific skill
        [supporting files]
```

A project's slug must be lowercase, hyphen-separated, and **must not contain `--`** (the project separator).

## Prefix-flatten convention

When `bin/build.py` produces `dist/{nested,flat}/`, project content is published using a `--` separator that prefixes the project slug onto every skill and rule. This gives every project a unique, addressable namespace in the flat catalog with no implicit shadowing.

| Source | Flat publish path | Resolver token |
|---|---|---|
| `projects/siege-utilities/skills/hostile-review/SKILL.md` | `skills/siege-utilities--hostile-review/SKILL.md` | `[skill:siege-utilities--hostile-review]` |
| `projects/siege-utilities/_rules.md` | `skills/_siege-utilities--rules.md` | `[rule:siege-utilities--rules]` |
| `projects/siege-utilities/PROJECT.md` | `projects/siege-utilities/PROJECT.md` (verbatim) | — (not routing) |

Project skills land at the same depth as general flat skills (`skills/<slug>/`), so downstream consumers honoring the depth-2 catalog convention see them automatically.

## PROJECT.md frontmatter

Required:

```yaml
---
name: <human-readable name>
description: <one-paragraph what the project is>
repo: <github org/repo, e.g. siege-analytics/siege_utilities>
scope:
  - <glob pattern>     # documentary: which subpaths this project's skills typically fire on
  - <glob pattern>
owners:
  - <email>
---
```

Optional:

- `status: active | archived | retired` — defaults to `active`. `archived` keeps the project visible in the resolver catalog but routing entries are dormant; `retired` means the directory should be removed (kept here only during transition).
- `retired_at: YYYY-MM-DD`, `successor: <project-slug>` — for archived/retired projects, documents when and what replaced it.

Below the frontmatter, narrate the project's strategic goal, key invariants, and anything a contributor needs to know to author skills/rules consistent with the project's standards.

## `_rules.md` structure

Required sections:

1. **Overrides table.** Lists every project rule that weakens a general rule, with justification. May be empty (`*(none yet)*`). An undeclared weakening is void — the general rule wins.
2. **Project rules.** Each rule numbered with a stable identifier (e.g., `SU-1`, `SU-2`) so downstream skills can cite them precisely.
3. **Branch/merge conventions** for the project repo, if they differ from general practice.
4. **Review standards** specific to the project.

Cite incidents or audit findings as justification for each rule. "We've always done it this way" is not a justification.

## SKILL.md frontmatter for project skills

Same shape as general skills (`name`, `description`, optional `disable-model-invocation`, `user-invocable`, `allowed-tools`, `globs`). At build time the publisher injects:

```yaml
project: <project-slug>
```

so the runtime can introspect provenance without parsing the slug. Don't write `project:` by hand — it's added at publish time and any pre-existing value is preserved.

## RESOLVER.template.md updates

When you add a project, also update the **Project-specific rules and skills** section of `skills/RESOLVER.template.md`:

1. Add the project to the **Active projects** table.
2. Create a new `### <project>-specific routing` subsection beneath it with trigger → skill rows using the prefixed-slug tokens (e.g., `[skill:<project>--<skill>]`).
3. If a rule is referenced by a routing entry, use the `[rule:<project>--rules]` token so the link resolves into the published rules file.

## Cross-references within a project

If a project skill references a sibling project skill or its project rules, use the full prefixed slug in the token. The build does not auto-prefix tokens inside project SKILL.md files — be explicit:

```markdown
This skill chains with [skill:siege-utilities--notebook-impact].
The invariants below come from [rule:siege-utilities--rules].
```

If a project skill references a **general** skill or rule, use the unprefixed slug as normal: `[skill:think]`, `[rule:output]`.

## Validation

Run `python3 bin/build.py --check` before opening a PR. The build fails if:

- A project slug or skill slug contains `--`.
- A project skill's flat slug (`<project>--<skill>`) collides with a general skill slug.
- A project rule's flat slug (`<project>--rules`) collides with a general rule slug.
- A `[skill:...]` or `[rule:...]` token references a slug that doesn't exist (rendered as `` `<slug>` (planned) `` and listed in the build's forward-looking-references summary).

## PR checklist

- [ ] `PROJECT.md` with required frontmatter and key-invariants prose.
- [ ] `_rules.md` with Overrides table (may be empty).
- [ ] At least one project skill under `skills/<skill-name>/` with a meaningful trigger.
- [ ] `RESOLVER.template.md` updated: active-projects row + routing subsection.
- [ ] Top-level `RESOLVER.md` updated to mirror the template (manual; not auto-generated).
- [ ] `python3 bin/build.py --check` passes.
- [ ] Each project rule cites an incident, audit finding, or documented invariant as justification.
