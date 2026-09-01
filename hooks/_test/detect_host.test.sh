#!/usr/bin/env bash
# Test: hooks/lib/detect-host.sh
#
# The runtime host decides whether hooks can block, which frontmatter keys are
# understood, and whether data sources are gated. Getting it wrong is silent,
# so every branch is asserted here — including the case that motivated the
# detection order: Craft spawns Claude Code, so both hosts' variables can be
# present at once.
#
# Ref: #696

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
DETECT="$ROOT/hooks/lib/detect-host.sh"

# Run the detector in a clean environment with only the named vars set, so a
# variable leaking in from the developer's own shell cannot make a test pass.
detect_with() {
    env -i PATH="$PATH" HOME="$HOME" "$@" bash "$DETECT" 2>/dev/null
}

check() {
    local name="$1" want="$2" got="$3"
    if [[ "$got" == "$want" ]]; then
        _HARNESS_PASS=$((_HARNESS_PASS + 1))
        printf '  [PASS] %s\n' "$name"
    else
        _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
        _HARNESS_FAILED_NAMES+=("$name")
        printf '  [FAIL] %s (want %s, got %s)\n' "$name" "$want" "$got"
    fi
}

# --- the three outcomes ---

check "craft via CRAFT_IS_PACKAGED" craft \
    "$(detect_with CRAFT_IS_PACKAGED=true)"
check "craft via CRAFT_RESOURCES_PATH" craft \
    "$(detect_with CRAFT_RESOURCES_PATH=/app/resources)"
check "craft via CRAFT_BUNDLED_ASSETS_ROOT" craft \
    "$(detect_with CRAFT_BUNDLED_ASSETS_ROOT=/app)"
check "craft via CRAFT_RPC_PORT" craft \
    "$(detect_with CRAFT_RPC_PORT=9100)"

check "claude-code via CLAUDECODE" claude-code \
    "$(detect_with CLAUDECODE=1)"
check "claude-code via CLAUDE_CODE_ENTRYPOINT" claude-code \
    "$(detect_with CLAUDE_CODE_ENTRYPOINT=cli)"
check "claude-code via CLAUDE_PROJECT_DIR" claude-code \
    "$(detect_with CLAUDE_PROJECT_DIR=/repo)"

check "unknown when neither is present" unknown \
    "$(detect_with)"

# --- the ordering case this exists for ---
#
# Craft spawns Claude Code as a child, which sets CLAUDECODE for itself while
# inheriting the CRAFT_* variables. A hook in that child sees both. It is
# running under Craft, and must be told so.

check "craft wins when both hosts' vars are present" craft \
    "$(detect_with CRAFT_IS_PACKAGED=true CLAUDECODE=1)"
check "craft wins regardless of which craft var is set" craft \
    "$(detect_with CRAFT_RPC_PORT=9100 CLAUDE_CODE_ENTRYPOINT=cli CLAUDECODE=1)"

# --- empty is not set ---
#
# An exported-but-empty variable must not count as a signal; that is how a
# cleared environment gets misread as a live runtime.

check "empty craft var does not signal craft" unknown \
    "$(detect_with CRAFT_IS_PACKAGED=)"
check "empty claude var does not signal claude-code" unknown \
    "$(detect_with CLAUDECODE=)"
check "empty craft var falls through to claude-code" claude-code \
    "$(detect_with CRAFT_IS_PACKAGED= CLAUDECODE=1)"

# --- credentials are never used as a signal ---

check "oauth token alone is not a host signal" unknown \
    "$(detect_with CRAFT_CLAUDE_OAUTH_TOKEN=sk-ant-oat01-placeholder)"

# --- sourceable as well as executable ---

sourced=$(env -i PATH="$PATH" HOME="$HOME" CRAFT_IS_PACKAGED=true bash -c \
    "source '$DETECT'; detect_host" 2>/dev/null)
check "sourceable: detect_host available as a function" craft "$sourced"

# Sourcing must not print anything by itself — a library that echoes on source
# corrupts any hook that sources it before writing its own output.
noise=$(env -i PATH="$PATH" HOME="$HOME" bash -c "source '$DETECT'" 2>/dev/null)
check "sourcing is silent" "" "$noise"

report
