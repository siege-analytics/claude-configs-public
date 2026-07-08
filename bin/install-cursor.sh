#!/usr/bin/env bash
# Install claude-configs-public cursor consumer package.
#
# Copies skill directories to ~/.cursor/skills/ (or project .cursor/skills/),
# resolver to ~/.cursor/siege-resolver.md, and rules bundle to
# ~/.cursor/siege-rules-bundle.md.
#
# NEVER touches ~/.cursor/skills-cursor/ (Cursor-managed built-ins).
#
# Usage:
#   bash bin/install-cursor.sh
#   bash bin/install-cursor.sh --package-root dist/cursor/
#   bash bin/install-cursor.sh --project /path/to/repo
#   bash bin/install-cursor.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_PATH=""
DRY_RUN=false

usage() {
    cat <<'USAGE'
Usage: bash bin/install-cursor.sh [options]

Options:
  --package-root <path>   Path to dist/cursor/ (default: parent of bin/)
  --project <path>        Install skills to <path>/.cursor/skills/ instead of ~/.cursor/skills/
  --dry-run               Print actions without copying files
  -h, --help              Show this help

Install targets:
  Skills:   ~/.cursor/skills/          (or <project>/.cursor/skills/)
  Resolver: ~/.cursor/siege-resolver.md
  Bundle:   ~/.cursor/siege-rules-bundle.md

Does NOT modify ~/.cursor/skills-cursor/
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --package-root)
            [[ -n "${2:-}" ]] || { echo "ERROR: --package-root requires a path" >&2; exit 2; }
            PACKAGE_ROOT="$(cd "$2" && pwd)"
            shift 2
            ;;
        --project)
            [[ -n "${2:-}" ]] || { echo "ERROR: --project requires a path" >&2; exit 2; }
            PROJECT_PATH="$(cd "$2" && pwd)"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown arg: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

SKILLS_SRC="$PACKAGE_ROOT/skills"
RESOLVER_SRC="$PACKAGE_ROOT/RESOLVER.md"
BUNDLE_SRC="$PACKAGE_ROOT/RULES_BUNDLE.md"

if [[ ! -d "$SKILLS_SRC" ]]; then
    echo "ERROR: skills/ not found at $SKILLS_SRC" >&2
    echo "Run: python3 bin/build.py  (or pass --package-root dist/cursor/)" >&2
    exit 1
fi

if [[ -n "$PROJECT_PATH" ]]; then
    SKILLS_DEST="$PROJECT_PATH/.cursor/skills"
else
    SKILLS_DEST="$HOME/.cursor/skills"
fi

RESOLVER_DEST="$HOME/.cursor/siege-resolver.md"
BUNDLE_DEST="$HOME/.cursor/siege-rules-bundle.md"
CURSOR_MANAGED="$HOME/.cursor/skills-cursor"

# Safety: refuse if destination resolves under skills-cursor
case "$SKILLS_DEST" in
    "$CURSOR_MANAGED"|"$CURSOR_MANAGED"/*)
        echo "ERROR: refusing to install into Cursor-managed skills-cursor directory" >&2
        exit 1
        ;;
esac

run_cmd() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[dry-run] $*"
    else
        "$@"
    fi
}

echo "=== Cursor install ==="
echo "Package:  $PACKAGE_ROOT"
echo "Skills:   $SKILLS_SRC/ -> $SKILLS_DEST/"
echo "Resolver: $RESOLVER_SRC -> $RESOLVER_DEST"
echo "Bundle:   $BUNDLE_SRC -> $BUNDLE_DEST"
echo

run_cmd mkdir -p "$SKILLS_DEST"

# Copy skill directories only (exclude loose rule files at package skills root)
for entry in "$SKILLS_SRC"/*; do
    [[ -e "$entry" ]] || continue
    name="$(basename "$entry")"
    if [[ -f "$entry" ]]; then
        case "$name" in
            _*-rules.md|RULES.md|_coverage.md)
                echo "  [skip] loose rule file: $name"
                continue
                ;;
        esac
    fi
    if [[ -d "$entry" ]]; then
        run_cmd mkdir -p "$SKILLS_DEST"
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[dry-run] rsync -a \"$entry/\" \"$SKILLS_DEST/$name/\""
        else
            rsync -a "$entry/" "$SKILLS_DEST/$name/"
        fi
    fi
done

if [[ -f "$RESOLVER_SRC" ]]; then
    run_cmd mkdir -p "$(dirname "$RESOLVER_DEST")"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[dry-run] cp \"$RESOLVER_SRC\" \"$RESOLVER_DEST\""
    else
        cp "$RESOLVER_SRC" "$RESOLVER_DEST"
    fi
else
    echo "  [warn] RESOLVER.md not found in package" >&2
fi

if [[ -f "$BUNDLE_SRC" ]]; then
    run_cmd mkdir -p "$(dirname "$BUNDLE_DEST")"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[dry-run] cp \"$BUNDLE_SRC\" \"$BUNDLE_DEST\""
    else
        cp "$BUNDLE_SRC" "$BUNDLE_DEST"
    fi
else
    echo "  [warn] RULES_BUNDLE.md not found in package" >&2
fi

if [[ "$DRY_RUN" == "true" ]]; then
    echo
    echo "Dry run complete. No files copied."
else
    SKILL_COUNT="$(find "$SKILLS_DEST" -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' ')"
    LOOSE="$(find "$SKILLS_DEST" -maxdepth 1 -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
    echo
    echo "Install complete."
    echo "  Skills installed/merged: $SKILL_COUNT SKILL.md files under $SKILLS_DEST"
    echo "  Loose .md at skills root: $LOOSE (should be 0)"
    echo
    echo "Next steps:"
    echo "  1. Add User Rule from cursor/templates/user-rule.md (see cursor/CURSOR.md)"
    echo "  2. Start a new Agent chat to reload skills"
fi
