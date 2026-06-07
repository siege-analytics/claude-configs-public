#!/usr/bin/env python3
"""Scaffold project-specific skills and rules for claude-configs-public.

Three subcommands:

  init <slug>        -- create an in-tree project under projects/<slug>/
  satellite <slug>   -- generate a standalone satellite repo directory
  add-skill <project> <skill> -- add a skill to an existing project

Usage:
    python bin/scaffold-project.py init my-project --repo org/my-repo --owner me@example.com
    python bin/scaffold-project.py satellite my-project --repo org/my-repo --owner me@example.com
    python bin/scaffold-project.py add-skill siege-utilities my-new-skill

Run from the repo root (the directory containing bin/, projects/, skills/).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def project_md_template(
    slug: str,
    repo: str,
    owner: str,
    description: str,
) -> str:
    return dedent(f"""\
        ---
        name: {slug}
        description: {description}
        repo: {repo}
        scope:
          - "src/**"
          - "tests/**"
        owners:
          - {owner}
        ---

        # {slug}

        ## What it is

        TODO: describe the project in 2-3 sentences.

        ## Strategic goal

        TODO: what does success look like for this project?

        ## Scope

        This project definition activates when the working directory matches
        the `{repo}` repository. All project-specific rules and skills below
        apply only within that scope.

        ## Key invariants

        1. TODO: list the project's non-negotiable invariants.
    """)


def rules_md_template(slug: str) -> str:
    return dedent(f"""\
        ---
        description: Project-specific rules for {slug}. These take precedence over general rules within the {slug} scope. Falls back to general rules for anything not described here.
        ---

        # {slug} project rules

        These rules apply only when working in the {slug} repository. They
        take precedence over general rules within this scope. For any situation
        not described here, the general rules in `skills/RULES.md` apply.

        ## Overrides table

        Any project rule that weakens a general rule must be declared here. If
        a project rule weakens a general rule without an entry in this table,
        the general rule wins.

        | Project rule | General rule weakened | Justification |
        |---|---|---|
        | *(none yet)* | | |
    """)


def skill_md_template(skill_name: str, project_slug: str) -> str:
    return dedent(f"""\
        ---
        name: "{skill_name} ({project_slug})"
        description: "TODO: describe when this skill should be loaded."
        ---

        # {skill_name} -- {project_slug}

        TODO: describe what this skill does and when to use it.

        ## When to run

        TODO: describe the trigger conditions.

        ## Procedure

        TODO: step-by-step instructions.
    """)


def satellite_readme_template(slug: str, upstream_repo: str) -> str:
    return dedent(f"""\
        # {slug}_claude_skills

        Claude Code skills for {slug} repositories.

        ## Layout

        ```
        skills/            # project-specific skills (yours to edit)
        upstream/           # synced from {upstream_repo} (read-only)
          skills/           # general-purpose skills
          projects/         # project definitions
        PROJECT.md          # project definition (two-layer: upstream + local)
        UPSTREAM.md         # sync state and instructions
        README.md           # this file
        ```

        ## Sync policy

        The `upstream/` directory is a read-only copy of the upstream
        configs repo. Do not edit files under `upstream/` directly --
        changes will be overwritten on the next sync.

        Project-specific skills live in `skills/` at the repo root.
        These are yours to create, edit, and delete freely.

        ## Updating upstream

        See `UPSTREAM.md` for sync instructions and history.
    """)


def satellite_upstream_template(
    slug: str,
    upstream_repo: str,
    upstream_url: str,
) -> str:
    return dedent(f"""\
        # Upstream sync state

        | Field | Value |
        |---|---|
        | Upstream repo | {upstream_repo} |
        | Upstream URL | {upstream_url} |
        | Current tag | *(not yet synced)* |
        | Last synced | *(never)* |

        ## Sync history

        | Date | From tag | To tag | Notes |
        |---|---|---|---|
        | *(no syncs yet)* | | | |

        ## How to sync

        1. Check the latest release tag on the upstream repo.
        2. Download or clone at that tag.
        3. Copy the `skills/` and `projects/` directories into `upstream/`.
        4. Update the "Current tag" and "Last synced" fields above.
        5. Add a row to the sync history table.
        6. Review the diff for any breaking changes to skills you depend on.
        7. Commit with a message like: `chore: sync upstream to vX.Y.Z`

        ```bash
        # Example using git archive (adjust paths as needed):
        UPSTREAM_TAG="v3.0.1"
        git archive --remote={upstream_url} "$UPSTREAM_TAG" skills/ projects/ | \\
            tar -x -C upstream/
        ```

        ## Assessment policy

        Every sync must include a written assessment of what changed upstream
        and whether any project-specific skills or rules need updating. This
        assessment goes in the commit message body, not in a separate file.
    """)


def satellite_project_template(
    slug: str,
    repo: str,
    owner: str,
    description: str,
) -> str:
    return dedent(f"""\
        ---
        name: {slug}
        description: {description}
        repo: {repo}
        scope:
          - "src/**"
          - "tests/**"
        owners:
          - {owner}
        ---

        # {slug}

        ## Integration policy

        This project uses a two-layer skill model:

        1. **Upstream layer** (`upstream/`) -- read-only copy of the shared
           configs repo. Synced periodically from tagged releases. Do not
           edit directly.

        2. **Project layer** (`skills/`) -- project-specific skills that
           extend or override upstream behavior. These are owned by this
           repo and edited freely.

        When a skill exists in both layers, the project layer takes
        precedence. See `UPSTREAM.md` for sync state and instructions.

        ## Key invariants

        1. TODO: list the project's non-negotiable invariants.
    """)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    """Scaffold an in-tree project under projects/<slug>/."""
    slug = args.slug
    project_dir = PROJECTS_DIR / slug

    if project_dir.exists():
        print(f"ERROR: {project_dir.relative_to(REPO_ROOT)} already exists.", file=sys.stderr)
        return 1

    description = args.description or f"Project definition for {slug}."
    skills_dir = project_dir / "skills"

    project_dir.mkdir(parents=True)
    skills_dir.mkdir()

    (project_dir / "PROJECT.md").write_text(
        project_md_template(slug, args.repo, args.owner, description)
    )
    (project_dir / "_rules.md").write_text(rules_md_template(slug))
    (skills_dir / ".gitkeep").write_text("")

    print(f"Created in-tree project at {project_dir.relative_to(REPO_ROOT)}/")
    print(f"  PROJECT.md  -- edit frontmatter (name, description, repo, scope, owners)")
    print(f"  _rules.md   -- add project-specific rules")
    print(f"  skills/     -- add skills with: scaffold-project.py add-skill {slug} <name>")
    print()
    print("Next steps:")
    print(f"  1. Edit PROJECT.md -- fill in the TODO sections")
    print(f"  2. Edit _rules.md  -- add project-specific rules if needed")
    print(f"  3. Run: python bin/build.py --check")
    return 0


def cmd_satellite(args: argparse.Namespace) -> int:
    """Generate a standalone satellite repo directory."""
    slug = args.slug
    output_dir = Path(args.output) if args.output else Path(f"{slug}_claude_skills")

    if output_dir.exists():
        print(f"ERROR: {output_dir} already exists.", file=sys.stderr)
        return 1

    description = args.description or f"Project definition for {slug}."
    upstream_repo = "siege-analytics/claude-configs-public"
    upstream_url = f"https://github.com/{upstream_repo}.git"

    output_dir.mkdir(parents=True)
    (output_dir / "skills").mkdir()
    (output_dir / "skills" / ".gitkeep").write_text("")
    (output_dir / "upstream").mkdir()
    (output_dir / "upstream" / ".gitkeep").write_text("")

    (output_dir / "README.md").write_text(
        satellite_readme_template(slug, upstream_repo)
    )
    (output_dir / "UPSTREAM.md").write_text(
        satellite_upstream_template(slug, upstream_repo, upstream_url)
    )
    (output_dir / "PROJECT.md").write_text(
        satellite_project_template(slug, args.repo, args.owner, description)
    )

    print(f"Created satellite project at {output_dir}/")
    print(f"  README.md    -- repo overview and sync policy")
    print(f"  UPSTREAM.md  -- sync state tracker (update after each sync)")
    print(f"  PROJECT.md   -- project definition (two-layer model)")
    print(f"  skills/      -- your project-specific skills")
    print(f"  upstream/    -- will hold synced upstream content")
    print()
    print("Next steps:")
    print(f"  1. cd {output_dir} && git init")
    print(f"  2. Edit PROJECT.md -- fill in the TODO sections")
    print(f"  3. Perform first upstream sync (see UPSTREAM.md)")
    return 0


def cmd_add_skill(args: argparse.Namespace) -> int:
    """Add a skill to an existing project."""
    project = args.project
    skill = args.skill

    # Check in-tree first, then look for satellite pattern
    in_tree = PROJECTS_DIR / project / "skills"
    if in_tree.exists():
        skill_dir = in_tree / skill
    else:
        # Satellite: skills/ at the working directory root
        cwd_skills = Path.cwd() / "skills"
        if cwd_skills.exists() and (Path.cwd() / "UPSTREAM.md").exists():
            skill_dir = cwd_skills / skill
        else:
            print(
                f"ERROR: cannot find project '{project}'.\n"
                f"  Checked in-tree: {in_tree.relative_to(REPO_ROOT)}\n"
                f"  Checked satellite: {Path.cwd()}/skills/ (with UPSTREAM.md)\n"
                f"\n"
                f"For in-tree projects, run from the claude-configs-public root.\n"
                f"For satellite projects, run from the satellite repo root.",
                file=sys.stderr,
            )
            return 1

    if skill_dir.exists():
        print(f"ERROR: {skill_dir} already exists.", file=sys.stderr)
        return 1

    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        skill_md_template(skill, project)
    )

    print(f"Created skill at {skill_dir}/SKILL.md")
    print()
    print("Next steps:")
    print(f"  1. Edit SKILL.md -- fill in the description, triggers, and procedure")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- init --
    p_init = subparsers.add_parser(
        "init",
        help="Create an in-tree project under projects/<slug>/",
    )
    p_init.add_argument("slug", help="Project slug (directory name)")
    p_init.add_argument("--repo", required=True, help="Repository identifier (e.g. org/repo-name)")
    p_init.add_argument("--owner", required=True, help="Owner email address")
    p_init.add_argument("--description", help="One-line project description")

    # -- satellite --
    p_sat = subparsers.add_parser(
        "satellite",
        help="Generate a standalone satellite repo directory",
    )
    p_sat.add_argument("slug", help="Project slug")
    p_sat.add_argument("--repo", required=True, help="Repository identifier (e.g. org/repo-name)")
    p_sat.add_argument("--owner", required=True, help="Owner email address")
    p_sat.add_argument("--description", help="One-line project description")
    p_sat.add_argument("--output", "-o", help="Output directory (default: <slug>_claude_skills)")

    # -- add-skill --
    p_skill = subparsers.add_parser(
        "add-skill",
        help="Add a skill to an existing project",
    )
    p_skill.add_argument("project", help="Project slug")
    p_skill.add_argument("skill", help="Skill slug (directory name)")

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "satellite":
        return cmd_satellite(args)
    elif args.command == "add-skill":
        return cmd_add_skill(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
