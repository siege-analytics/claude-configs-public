#!/bin/bash
# Shared library: detect-host.sh
# Answers "which agent runtime am I running under?" — once, for everyone.
#
# Usage as a library:
#   source "$HOOK_DIR/../lib/detect-host.sh"
#   case "$(detect_host)" in
#       craft)       ... ;;
#       claude-code) ... ;;
#       unknown)     ... ;;   # assume the least capable runtime
#   esac
#
# Usage as a command (for python, make, CI):
#   host=$(bash hooks/lib/detect-host.sh)
#
# Why this exists: rules, hooks and skills now run on more than one host, and
# the hosts differ in ways that change behaviour — whether a PreToolUse hook can
# block, which frontmatter keys the skill panel understands, whether data
# sources are gated behind a per-source guide. Before this, each site invented
# its own test, and several tested variables that no runtime sets
# (CRAFT_AGENT_SESSION_ID, CRAFT_AGENT_SESSION_DIR, CRAFT_AGENT_WORKSPACE) —
# so they were silent no-ops that always took the fallback branch.
#
# Detection order is deliberate. Craft Agents spawns Claude Code as a child
# process, so a hook running under Craft can see BOTH the inherited CRAFT_*
# variables and the CLAUDECODE variable that the child sets for itself.
# Craft is therefore tested first: "both present" means craft, not claude-code.
# Verified on cyberpower — the Craft server process carries ten CRAFT_* vars
# and zero CLAUDE* vars; the CLAUDE* ones appear only in the spawned child.
#
# `unknown` is a real answer, not a failure. Returning it is correct when
# neither runtime is identifiable, and callers must treat it as the least
# capable host: assume hooks cannot block, assume nothing is auto-injected.
# Guessing "probably claude-code" is how enforcement silently disappears.
#
# Ref: #696

# Variables that identify each host. Any one of them is sufficient; they are
# listed most-stable first. CRAFT_CLAUDE_OAUTH_TOKEN is deliberately NOT used
# as a signal — it is a credential, and reading it here would spread it.
_DETECT_HOST_CRAFT_VARS=(
    CRAFT_IS_PACKAGED
    CRAFT_RESOURCES_PATH
    CRAFT_BUNDLED_ASSETS_ROOT
    CRAFT_RPC_PORT
)

_DETECT_HOST_CLAUDE_VARS=(
    CLAUDECODE
    CLAUDE_CODE_ENTRYPOINT
    CLAUDE_PROJECT_DIR
)

_detect_host_any_set() {
    local name value
    for name in "$@"; do
        value="${!name-}"
        [ -n "$value" ] && return 0
    done
    return 1
}

# Echo the current host: craft | claude-code | unknown
detect_host() {
    if _detect_host_any_set "${_DETECT_HOST_CRAFT_VARS[@]}"; then
        echo "craft"
        return 0
    fi
    if _detect_host_any_set "${_DETECT_HOST_CLAUDE_VARS[@]}"; then
        echo "claude-code"
        return 0
    fi
    echo "unknown"
    return 0
}

# Executed directly rather than sourced: print the answer.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    detect_host
fi
