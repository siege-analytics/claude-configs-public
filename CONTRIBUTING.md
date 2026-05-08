# Contributing

This repo serves two runtimes from one source: Claude Code (with the resolver hook) and Craft Agent (with the skills pane). The dual-output build keeps the source single while emitting layout-appropriate artifacts.

If you're adding a skill or editing one, the only conventions you need to know are below.

## The slug-token convention

Skills cross-reference each other by **slug token**, not file path:

```markdown
<!-- YES — works in both layouts -->
See [skill:code-review] for the review checklist.

<!-- NO — breaks when the layout changes -->
See [`../../coding/code-review/SKILL.md`](../../coding/code-review/SKILL.md) for the review checklist.
```

Always-on rules files use a parallel form:

```markdown
<!-- YES -->
Defers to [rule:output] for commit-message conventions.

<!-- NO -->
Defers to [`../../_output-rules.md`](../../_output-rules.md).
```

The build expands tokens to layout-appropriate paths. You don't think about whether the link target is two levels up or one.

### When to use which token

| Token | Resolves to | Use for |
|---|---|---|
| `[skill:<slug>]` | `path/to/<slug>/SKILL.md` | Any other skill — leaves, routers, shelves, books |
| `[rule:<slug>]` | `path/to/_<slug>-rules.md` | Always-on rules at `skills/_*-rules.md` |
| Plain Markdown link | (unchanged) | External URLs, GitHub issues, anything outside the skill tree |

### Forward-looking references

If you want to reference a skill that doesn't exist yet (planned, not built), use the token anyway. The build emits it as `<slug> (planned)` and logs a warning. Once the skill lands, the reference resolves automatically.

## Adding a new skill

1. **Pick a slug** — lowercase, alphanumeric + hyphens. Globally unique across all categories. Validated by build (collisions = build failure).
2. **Decide nesting** — slot under the appropriate category (`coding/`, `git-workflow/`, `planning/`, etc.). The build flattens leaves automatically for Craft Agent; routers stay nested.
3. **Write `SKILL.md`** with frontmatter:
   ```yaml
   ---
   name: <slug>
   description: "One-sentence description shown in skills pane and resolver."
   disable-model-invocation: true   # if user-invokable as /slug
   allowed-tools: Read Grep Bash    # tools the skill needs
   ---
   ```
4. **Add an icon** at `<skill-dir>/icon.svg` (optional but recommended for Craft Agent's pane).
5. **Reference other skills** with `[skill:<slug>]`, never paths.
6. **Add a routing entry** to `skills/RESOLVER.template.md` so the resolver dispatches to your skill.
7. **Run the build locally** to validate:
   ```bash
   python3 bin/build.py --check
   ```

## The build

`bin/build.py` produces two outputs:

- **`dist/nested/`** — mirrors the source layout. Skills live under category folders. The resolver hook works as designed.
- **`dist/flat/`** — leaf skills move to `skills/<slug>/SKILL.md`. Routers stay at their category root. Craft Agent's skills pane sees every leaf as a slash command.

You can build locally any time:

```bash
python3 bin/build.py              # both layouts
python3 bin/build.py --layout flat
python3 bin/build.py --check      # validate tokens, no output
```

## Sync (don't fight habits)

`bin/sync-skill-references.py` is the canonical reference normalizer. Run it whenever you've written path-form links by habit:

```bash
python3 bin/sync-skill-references.py             # rewrite in place
python3 bin/sync-skill-references.py --dry-run   # preview changes
python3 bin/sync-skill-references.py --check     # exit 1 if any path-form refs found
```

CI runs `--check` on every PR. If it fails, run the script locally and re-push.

## CI

`.github/workflows/build-and-publish.yml` runs:

- **On every PR:** `sync-skill-references.py --check` + `build.py --check`
- **On push to main:** the validate job + publishes `dist/nested/` to `release/nested` branch and `dist/flat/` to `release/flat` branch
- **On tag push (`vX.Y.Z`):** all of the above + tags `release/nested` and `release/flat` with `vX.Y.Z-nested` / `vX.Y.Z-flat` for stable consumer pinning

## How downstream consumes this repo

### Claude Code with the resolver hook (nested layout)

```bash
git subtree pull --prefix .claude/skills \
  https://github.com/siege-analytics/claude-configs-public.git release/nested --squash
```

Or pin to a specific version:

```bash
git subtree pull --prefix .claude/skills \
  https://github.com/siege-analytics/claude-configs-public.git v1.0.0-nested --squash
```

### Craft Agent (flat layout)

```bash
# Sync the workspace skills/ directory from the flat release
TMP=$(mktemp -d)
git clone --depth 1 --branch release/flat \
  https://github.com/siege-analytics/claude-configs-public.git "$TMP/repo"
rsync -a "$TMP/repo/skills/" ~/.craft-agent/workspaces/my-workspace/skills/
rm -rf "$TMP"
```

Or pin to a specific version (`release/flat` → `v1.0.0-flat`).

The local workspace's `UPSTREAM-UPDATE.md` documents the canonical sync flow.

## Releases & versioning

Versions follow [SemVer](https://semver.org/):

- **Major** — breaking changes to skill discovery, slug taxonomy, frontmatter conventions, or build outputs
- **Minor** — new skills, new shelves, new always-on rules, additive changes
- **Patch** — fixes to existing skills, doc corrections

Every tag on `main` produces matching tags on the release branches:

- `v1.0.0` (source) → `v1.0.0-nested` and `v1.0.0-flat` (release branches)

Pin downstream consumers to a release-branch tag, not the source tag — the source tag is on `main`, which has the build infrastructure but not the resolved skills.

## Skill design guidelines

When writing a new skill or editing one:

- **One skill = one task or domain.** Don't bundle multiple workflows into a single skill; create a router instead.
- **Description is what the user sees.** It appears in slash-command autocomplete and the skills pane. Make it actionable.
- **Reference other skills by slug.** Never path. The build handles paths.
- **Keep cross-links to a minimum.** Each cross-link is a maintenance edge; only add one if loading the linked skill is genuinely useful in this skill's context.
- **Add edge-case checks** when the skill performs work — see `[skill:code-review]` §1 for the universal edge-case checklist.
- **No AI/agent attribution** in commits, PR descriptions, skill body, or anywhere else user-visible. See `[rule:output]`.

## Skill validation

For Craft Agent compatibility, every `SKILL.md` should:

- Have a top-level slug folder under `skills/<category>/<slug>/` (or in the flat output, `skills/<slug>/`)
- Have valid YAML frontmatter with `name` and `description` minimum
- Pass `bin/build.py --check`

You can also use the Craft Agent skill validator:

```python
mcp__session__skill_validate(skillSlug="<slug>")
```

## How rules get promoted into this repo

The `_*-rules.md` files at `skills/_*-rules.md` are **Tier 3** of a three-tier rules pipeline. Rules don't get added here based on opinion — they get promoted from evidence accumulated in downstream consumer repos.

| Tier | Lives in | Owned by | Promotion gate |
|---|---|---|---|
| 1 — Ledger | `<consumer-repo>/LESSONS.md` | `[skill:lessons-learned]` | recurrence ≥ 3, or 1 production incident, or Critical-severity → Tier 2 |
| 2 — Project rules | `<consumer-repo>/.claude/rules/<topic>.md` | `[skill:distill-lessons]` | appears in 2+ projects, or is language/framework-level → Tier 3 |
| **3 — Org rules (this repo)** | `claude-configs-public/skills/_<topic>-rules.md` | **Human PR with cited evidence** | (top of pipeline) |

`[skill:rules-audit]` runs the cross-tier hygiene pass that surfaces Tier-3 promotion candidates.

### Opening a Tier 3 PR

When you propose adding or amending a rule in any `_*-rules.md` file, the PR description must:

1. **Cite at least two Tier-2 projects** that have independently arrived at the same rule (link to `.claude/rules/<topic>.md` in each).
2. **OR** cite a single Tier-2 project plus a justification for why the rule is language/framework-level (and therefore broadly applicable beyond that one project).
3. **List the originating Tier-1 evidence** — link to the `LESSONS.md` entries that fed each Tier-2 rule. Reviewers should be able to trace every clause back to a real incident, comment, or code-review finding.
4. **Pass the conflict gate** — confirm the new rule does not contradict an existing rule in the same file. If it does, the PR amends or retires the conflicting rule in the same change.

PRs that propose new rules without cited evidence will be asked to either gather evidence first (open a Tier-1/Tier-2 PR in the relevant consumer repo) or downgrade to a discussion issue.

### Why this discipline

The rules in `_*-rules.md` get loaded into every session that uses this repo. Adding a rule based on opinion means every reviewer in every project pays the cost of a rule that may not actually solve a recurring problem. Requiring evidence keeps the rules earning their slot.

The reverse pipeline (Tier 3 → Tier 2 → Tier 1) doesn't exist by design: org-wide rules don't flow downstream as new evidence; they apply uniformly. Evidence flows up; rules apply down.

## Definition of Done

This repo's own contributions are subject to the [Definition of Done](skills/_definition-of-done-rules.md) it ships:

1. **Code-reviewed** — at least self-review of the diff; CodeRabbit on PR
2. **Edge cases explored** — for the skill content itself: does it handle absent dependencies, partial state, alternative tools?
3. **Tests** — for `bin/` scripts, add a smoke test if behavior is non-trivial
4. **Ticket updated** — link the PR to the ticket; close on merge
5. **Work has a ticket** — every PR references at least one tracked issue

The PR-creation skill (`/create-pr` in workspaces using this repo) gates on all five before opening. PRs that fail any criterion open as drafts with the failures listed.
