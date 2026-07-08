# Cursor IDE — install and runtime guide

This document describes how to consume **claude-configs-public** in [Cursor](https://cursor.com). Cursor is a **Tier B (non-hook)** runtime: skills and the rules bundle provide guidance, but Claude Code-style PreToolUse hooks and mechanical enforcement gates are not available.

## What you get

| Artifact | Install location | Purpose |
|---|---|---|
| Skill directories (`skills/<slug>/SKILL.md`) | `~/.cursor/skills/` or `<project>/.cursor/skills/` | Agent skills discovered by description |
| `RESOLVER.md` | `~/.cursor/siege-resolver.md` | Skill routing reference (manual / User Rule) |
| `RULES_BUNDLE.md` | `~/.cursor/siege-rules-bundle.md` | Always-on policy addendum |
| User Rule template | Cursor Settings → Rules | Lightweight resolver substitute |
| Project rule template | `<project>/.cursor/rules/` | Optional repo-scoped policy |

**Never install into `~/.cursor/skills-cursor/`** — that directory is reserved for Cursor-managed built-in skills.

## Quick install (from repo)

```bash
git clone https://github.com/siege-analytics/claude-configs-public.git
cd claude-configs-public
bash bin/install.sh --cursor
```

Or build and install the cursor package explicitly:

```bash
python3 bin/build.py
bash bin/install-cursor.sh --package-root dist/cursor/
```

## Quick install (from release)

Pin to a tagged cursor consumer package:

```bash
TAG=v3.5.13   # replace with your pinned version
curl -fsSL -o cursor-${TAG}.tar.gz \
  "https://github.com/siege-analytics/claude-configs-public/releases/download/${TAG}/cursor-${TAG}.tar.gz"
mkdir -p /tmp/cursor-pkg && tar -xzf cursor-${TAG}.tar.gz -C /tmp/cursor-pkg
bash /tmp/cursor-pkg/bin/install-cursor.sh --package-root /tmp/cursor-pkg
```

Or clone the release branch:

```bash
git clone --depth 1 --branch release/cursor \
  https://github.com/siege-analytics/claude-configs-public.git /tmp/cursor-pkg
bash /tmp/cursor-pkg/bin/install-cursor.sh --package-root /tmp/cursor-pkg
```

## install-cursor.sh options

```bash
bash bin/install-cursor.sh [options]

Options:
  --package-root <path>   Path to dist/cursor/ (default: script-relative ../)
  --project <path>        Install skills into <path>/.cursor/skills/ instead of ~/.cursor/skills/
  --dry-run               Print actions without copying files
  -h, --help              Show help
```

**Personal install** (default): copies skill directories to `~/.cursor/skills/`, resolver to `~/.cursor/siege-resolver.md`, bundle to `~/.cursor/siege-rules-bundle.md`.

**Project install** (`--project <path>`): copies skills to `<path>/.cursor/skills/` only. Resolver and bundle remain personal (`~/.cursor/`) unless you symlink them into the project.

The script uses `rsync -a` **without** `--delete`, so existing skill directories you own are merged, not wiped.

## Wiring policy in Cursor

### 1. User Rule (recommended)

Copy the template from `cursor/templates/user-rule.md` into **Cursor Settings → Rules → User Rules**, or paste its contents directly. This tells the agent to:

- Read the `think` skill before non-trivial implementation
- Use git-workflow skills for commits and PRs
- Route language/domain work through the coding and analysis routers
- Treat `~/.cursor/siege-rules-bundle.md` as always-on policy

### 2. Project rule (optional)

Copy `cursor/templates/project-rule.mdc` to `<project>/.cursor/rules/siege-analytics.mdc` when you want repo-scoped reminders (ticket discipline, branch naming, definition-of-done).

### 3. Rules bundle

Cursor has no hook layer to inject `RULES_BUNDLE.md` every turn. Options:

- **User Rule pointer** — the bundled user-rule template references the bundle path
- **Manual @-mention** — reference `~/.cursor/siege-rules-bundle.md` at session start for high-stakes work
- **Project rule excerpt** — paste critical sections into `.cursor/rules/` if the full bundle is too large

## Tier A vs Tier B

| Capability | Claude Code (Tier A) | Cursor (Tier B) |
|---|---|---|
| Resolver injected every turn | Yes (UserPromptSubmit hook) | No — User Rule + skill descriptions |
| PreToolUse blocking gates | Yes | No |
| Skills as `/slash` commands | Yes (Claude Code) / Craft pane | Agent reads `SKILL.md` when relevant |
| Rules bundle | Fallback | Primary always-on policy path |
| Shell discipline scripts | Installed with hooks package | Not installed — skills describe the workflow |

Cursor consumers should expect **softer compliance** than hook-capable runtimes. The value is consistent engineering discipline content, not fail-closed enforcement.

## Skill layout

The cursor package ships **skill directories only** from the flat layout:

```
dist/cursor/skills/
  think/SKILL.md
  commit/SKILL.md
  coding/SKILL.md          # routers stay as directories
  shelves/.../SKILL.md
  ...
```

Excluded from the package (rules live in `RULES_BUNDLE.md` instead):

- `skills/_*-rules.md`
- `skills/RULES.md`
- `skills/_coverage.md`

Claude Code-specific frontmatter keys (`allowed-tools`, `argument-hint`) are stripped at build time.

## Validation

After building:

```bash
python3 bin/validate-cursor.py dist/cursor/
```

CI runs this on every PR and push to main/develop.

## Updating

Re-run install when you bump versions:

```bash
bash bin/install.sh --cursor
# or
bash bin/install-cursor.sh --package-root dist/cursor/
```

Start a **new Agent chat** after updating skills so Cursor reloads skill metadata.

## Tag scheme

Each source release tag `vX.Y.Z` produces:

- `vX.Y.Z-cursor` — points at the `release/cursor` branch commit
- GitHub Release asset: `cursor-vX.Y.Z.tar.gz`

Pin downstream installs to `vX.Y.Z-cursor` or `release/cursor`, not the unresolved source tree on `main`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Skills not appearing | New Agent chat; verify `SKILL.md` has `name` + `description` frontmatter |
| Loose `.md` files at skills root | Re-install from `dist/cursor/` (not raw `release/flat`) |
| Agent ignores rules | Add User Rule from template; @-mention bundle at session start |
| Conflicts with existing skills | install-cursor.sh merges by directory name; rename yours if needed |

## See also

- [`README.md`](../README.md) — distribution layouts and tag scheme
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — authoring skills for all runtimes
- [`bin/install-cursor.sh`](../bin/install-cursor.sh) — install script source
- [`bin/validate-cursor.py`](../bin/validate-cursor.py) — package validator
