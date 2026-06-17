#!/usr/bin/env bash
# Single-command install for claude-configs-public.
#
# Detects Craft Agent workspaces and deploys the flat layout, rules bundle,
# and hook settings automatically. Falls back to direct-clone mode for
# Claude Code CLI when no Craft Agent is found.
#
# Usage:
#   bash bin/install.sh                         # auto-detect CA, default workspace
#   bash bin/install.sh --workspace my-workspace  # explicit workspace slug
#   bash bin/install.sh --no-craft-agent        # skip CA detection, direct-clone only
#
# Run from the repo root (the directory containing bin/, skills/, hooks/).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CA_ROOT="$HOME/.craft-agent/workspaces"
WORKSPACE_SLUG=""
FORCE_NO_CA=false

usage() {
    cat <<'USAGE'
Usage: bash bin/install.sh [options]

Options:
  --workspace <slug>   Craft Agent workspace slug (default: auto-detect or my-workspace)
  --no-craft-agent     Skip CA detection; direct-clone mode only
  -h, --help           Show this help

Modes:
  Craft Agent detected:  build flat + bundle, deploy to workspace, install hooks
  No Craft Agent:        build both layouts, install hooks to .claude/settings.local.json
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --workspace)
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --workspace requires a slug" >&2
                exit 2
            fi
            WORKSPACE_SLUG="$2"
            shift 2
            ;;
        --no-craft-agent)
            FORCE_NO_CA=true
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

# -- Prerequisites --

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required but not found in PATH" >&2
    exit 1
fi

if [[ ! -f "$REPO_ROOT/bin/build.py" ]]; then
    echo "ERROR: bin/build.py not found. Run from the repo root." >&2
    exit 1
fi

# -- Detect Craft Agent --

detect_craft_agent() {
    if [[ "$FORCE_NO_CA" == "true" ]]; then
        return 1
    fi
    if [[ ! -d "$CA_ROOT" ]]; then
        return 1
    fi

    local workspaces=()
    for ws_dir in "$CA_ROOT"/*/; do
        [[ -d "$ws_dir" ]] || continue
        local slug
        slug="$(basename "$ws_dir")"
        workspaces+=("$slug")
    done

    if [[ ${#workspaces[@]} -eq 0 ]]; then
        return 1
    fi

    if [[ -n "$WORKSPACE_SLUG" ]]; then
        if [[ ! -d "$CA_ROOT/$WORKSPACE_SLUG" ]]; then
            echo "ERROR: workspace '$WORKSPACE_SLUG' not found at $CA_ROOT/$WORKSPACE_SLUG" >&2
            echo "Available workspaces: ${workspaces[*]}" >&2
            exit 1
        fi
        return 0
    fi

    if [[ ${#workspaces[@]} -eq 1 ]]; then
        WORKSPACE_SLUG="${workspaces[0]}"
        return 0
    fi

    # Multiple workspaces -- check for my-workspace default
    for ws in "${workspaces[@]}"; do
        if [[ "$ws" == "my-workspace" ]]; then
            WORKSPACE_SLUG="my-workspace"
            echo "Multiple workspaces found; defaulting to 'my-workspace'."
            echo "Use --workspace <slug> to target a different one."
            echo "Available: ${workspaces[*]}"
            echo
            return 0
        fi
    done

    echo "Multiple workspaces found but no 'my-workspace' default:" >&2
    echo "  ${workspaces[*]}" >&2
    echo "Use --workspace <slug> to specify which one." >&2
    exit 1
}

# -- Install: Craft Agent mode --

install_craft_agent() {
    local ws_path="$CA_ROOT/$WORKSPACE_SLUG"
    echo "=== Craft Agent install ==="
    echo "Workspace: $WORKSPACE_SLUG ($ws_path)"
    echo

    # Build flat layout + rules bundle and deploy to workspace
    echo "--- Building and deploying ---"
    python3 "$REPO_ROOT/bin/build.py" --layout flat --deploy --craft-workspace "$ws_path"
    echo

    # Install hooks settings
    echo "--- Installing hook settings ---"
    bash "$REPO_ROOT/bin/install-hooks.sh" \
        --workspace "$ws_path" \
        --hooks-root "$ws_path"
    echo

    # Validate
    echo "--- Validating deployment ---"
    local errors=0

    if [[ -d "$ws_path/skills" ]] && [[ -n "$(ls -A "$ws_path/skills/" 2>/dev/null)" ]]; then
        local skill_count
        skill_count="$(find "$ws_path/skills" -name "SKILL.md" | wc -l | tr -d ' ')"
        echo "  [ok] skills/ deployed ($skill_count skills)"
    else
        echo "  [FAIL] skills/ is empty or missing" >&2
        errors=$((errors + 1))
    fi

    if [[ -f "$ws_path/RULES_BUNDLE.md" ]]; then
        local bundle_lines
        bundle_lines="$(wc -l < "$ws_path/RULES_BUNDLE.md" | tr -d ' ')"
        echo "  [ok] RULES_BUNDLE.md present ($bundle_lines lines)"
    else
        echo "  [FAIL] RULES_BUNDLE.md not found" >&2
        errors=$((errors + 1))
    fi

    if [[ -L "$ws_path/CLAUDE.md" ]]; then
        local link_target
        link_target="$(readlink "$ws_path/CLAUDE.md")"
        if [[ "$link_target" == "RULES_BUNDLE.md" ]]; then
            echo "  [ok] CLAUDE.md -> RULES_BUNDLE.md (CA auto-mount wired)"
        else
            echo "  [warn] CLAUDE.md is a symlink but points at '$link_target', not RULES_BUNDLE.md"
        fi
    elif [[ -f "$ws_path/CLAUDE.md" ]]; then
        echo "  [warn] CLAUDE.md exists as a regular file (operator-owned); bundle NOT auto-mounted"
        echo "         (rename or append to wire the bundle into CA auto-inject)"
    else
        echo "  [warn] CLAUDE.md missing; bundle present but CA will not auto-inject it"
        errors=$((errors + 1))
    fi

    if [[ -f "$ws_path/RESOLVER.md" ]]; then
        echo "  [ok] RESOLVER.md present"
    else
        echo "  [FAIL] RESOLVER.md not found" >&2
        errors=$((errors + 1))
    fi

    local settings_file="$ws_path/.claude/settings.json"
    if [[ -f "$settings_file" ]]; then
        if python3 -c "import json; json.load(open('$settings_file'))" 2>/dev/null; then
            echo "  [ok] .claude/settings.json valid JSON"
        else
            echo "  [FAIL] .claude/settings.json is invalid JSON" >&2
            errors=$((errors + 1))
        fi
    else
        echo "  [warn] .claude/settings.json not found (hooks may not fire in CLI mode)"
    fi

    if [[ -d "$ws_path/hooks" ]]; then
        local hook_count
        hook_count="$(find "$ws_path/hooks" -name "*.sh" | wc -l | tr -d ' ')"
        echo "  [ok] hooks/ deployed ($hook_count scripts)"
    else
        echo "  [FAIL] hooks/ not found" >&2
        errors=$((errors + 1))
    fi

    # CA enforcement artifacts
    if [[ -f "$ws_path/enforcement-manifest.json" ]]; then
        local gate_count
        gate_count="$(python3 -c "import json; print(len(json.load(open('$ws_path/enforcement-manifest.json'))['gates']))" 2>/dev/null || echo 0)"
        echo "  [ok] enforcement-manifest.json present ($gate_count gates)"
    else
        echo "  [warn] enforcement-manifest.json not found (CA enforcement not active)"
    fi

    if [[ -d "$ws_path/.githooks" ]] && [[ -f "$ws_path/.githooks/pre-push" ]]; then
        echo "  [ok] .githooks/pre-push installed"
    else
        echo "  [warn] .githooks/pre-push not found (push-time enforcement not active)"
    fi

    echo
    if [[ $errors -gt 0 ]]; then
        echo "Deployment completed with $errors error(s)." >&2
        return 1
    fi

    echo "Deployment complete. Workspace '$WORKSPACE_SLUG' is ready."
    echo
    echo "Bundle mount status (Craft Agent):"
    echo "  RULES_BUNDLE.md  -> $ws_path/RULES_BUNDLE.md (always written)"
    echo "  CLAUDE.md        -> symlink to RULES_BUNDLE.md (if no operator CLAUDE.md present)"
    echo
    echo "CA auto-injects CLAUDE.md content into the system prompt of any session whose"
    echo "working directory is at or above the CLAUDE.md (CA walks cwd and its"
    echo "subdirectories; it does NOT walk parents). For workspace-wide coverage:"
    echo
    echo "  1. Open Settings -> Workspace Settings -> Default Working Directory"
    echo "  2. Set it to: $ws_path"
    echo "  3. New sessions in this workspace will start with cwd there and pick"
    echo "     up CLAUDE.md (= RULES_BUNDLE.md) on first system-prompt render."
    echo
    echo "Existing sessions inherit their old cwd; restart them to apply the new mount."
    echo
    echo "CA enforcement is active: UserPromptSubmit gates block via continue:false."
    echo "Native git pre-push hooks are at: $ws_path/.githooks/"
    echo
    echo "Verified empirically 2026-06-07 via probe sessions (claude-configs-public#380)."
    return 0
}

# -- Install: direct-clone mode --

install_direct_clone() {
    echo "=== Direct-clone install (no Craft Agent detected) ==="
    echo

    # Build both layouts
    echo "--- Building ---"
    python3 "$REPO_ROOT/bin/build.py" --layout both
    echo

    # Install hooks for direct use
    echo "--- Installing hook settings ---"
    bash "$REPO_ROOT/bin/install-hooks.sh"
    echo

    echo "Install complete. Hooks configured for Claude Code CLI."
}

# -- Main --

if detect_craft_agent; then
    install_craft_agent
else
    install_direct_clone
fi
