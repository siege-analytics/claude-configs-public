#!/bin/bash
# Shared library: detect-host.sh
# Answers "which agent runtime am I running under?" — once, for everyone.
#
# Usage as a library. Note the guard and the catch-all — both matter:
#
#   if ! . "$HOOK_DIR/../lib/detect-host.sh" 2>/dev/null \
#      || ! command -v detect_host >/dev/null 2>&1; then
#       HOST=unknown          # library missing or unreadable
#   else
#       HOST="$(detect_host)"
#   fi
#   case "$HOST" in
#       craft)       ... ;;
#       claude-code) ... ;;
#       *)           ... ;;   # unknown, or anything unexpected: least capable
#   esac
#
# A `case` without a `*)` arm is a silent fail-open: if this file is missing,
# the sourced function does not exist, `$(detect_host)` expands to the empty
# string, no arm matches, and the caller proceeds as though nothing applied.
# That is the same shape as the guards that stopped guarding today.
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

# Variables that identify each host. Any one is sufficient. Evidence for every
# entry is captured in docs/probes/craft-env.md — prose claims about environment
# state are what put the non-existent CRAFT_AGENT_* names into this codebase.
#
# Two families, and both are needed:
#
#   Per-session — set by the server when it spawns the agent subprocess, which
#   is where hooks actually run. Absent from the server's own environment, so
#   probing the daemon alone will not reveal them.
#
#   Process-wide — carried by the server and inherited by children.
#
# CRAFT_CLAUDE_OAUTH_TOKEN is deliberately NOT a signal: it is a credential, and
# reading it here would spread it.
_DETECT_HOST_CRAFT_VARS=(
    CRAFT_SESSION_DIR
    CRAFT_SESSION_ID
    CRAFT_SESSION_NAME
    CRAFT_IS_PACKAGED
    CRAFT_RESOURCES_PATH
    CRAFT_BUNDLED_ASSETS_ROOT
    CRAFT_RPC_PORT
)

# Names that look plausible and are set by nothing. Kept here so the regression
# test can assert they are never treated as signals: `CRAFT_AGENT_SESSION_ID`,
# `CRAFT_AGENT_SESSION_DIR` and `CRAFT_AGENT_WORKSPACE` are read in
# resolve-think-gate.py, standing-order-guard.sh and log-block.sh, and every
# branch behind them is dead. The real names carry no `AGENT`.

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
