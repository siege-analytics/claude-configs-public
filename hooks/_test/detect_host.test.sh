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

# --- the one genuine per-session signal ---
#
# CRAFT_SESSION_DIR is injected into the agent subprocess (pi-agent.ts),
# alongside CRAFT_DEBUG — those two are the only per-session additions. It is
# absent from the server's own environment, so probing the daemon misses it.

check "craft via CRAFT_SESSION_DIR" craft \
    "$(detect_with CRAFT_SESSION_DIR=/home/craftagents/.craft-agent/workspaces/x/sessions/y)"

# CRAFT_SESSION_ID and CRAFT_SESSION_NAME are automation template variables,
# not session variables — absent from a hook's environment. CRAFT_SESSION_NAME
# derives from a user-typed label, so treating it as a signal would let anything
# claim to be craft.
check "CRAFT_SESSION_ID is not a signal (automation var)" unknown \
    "$(detect_with CRAFT_SESSION_ID=260901-cool-gold)"
check "CRAFT_SESSION_NAME is not a signal (user-typed label)" unknown \
    "$(detect_with CRAFT_SESSION_NAME=cool-gold)"
check "CRAFT_DEBUG is not a signal (developer flag)" unknown \
    "$(detect_with CRAFT_DEBUG=1)"

# --- names that are set by nothing must never be signals ---
#
# CRAFT_AGENT_SESSION_ID, CRAFT_AGENT_SESSION_DIR and CRAFT_AGENT_WORKSPACE are
# read by three live hooks and exported by no runtime. If one of them ever
# starts satisfying this detector, the detector has acquired the same defect.

check "CRAFT_AGENT_SESSION_ID is not a signal" unknown \
    "$(detect_with CRAFT_AGENT_SESSION_ID=session-a)"
check "CRAFT_AGENT_SESSION_DIR is not a signal" unknown \
    "$(detect_with CRAFT_AGENT_SESSION_DIR=/tmp/x)"
check "CRAFT_AGENT_WORKSPACE is not a signal" unknown \
    "$(detect_with CRAFT_AGENT_WORKSPACE=electinfo-4)"

# --- credentials are never used as a signal ---

check "oauth token alone is not a host signal" unknown \
    "$(detect_with CRAFT_CLAUDE_OAUTH_TOKEN=sk-ant-oat01-placeholder)"

# --- the documented usage pattern fails safe ---
#
# A `case` without a `*)` arm is a silent fail-open when the library is absent:
# the function does not exist, the substitution is empty, no arm matches, and
# the caller proceeds as though nothing applied.

# This runs the recipe EXACTLY as the header documents it. If the header
# changes, this must change with it — a test of a recipe nobody is told to use
# proves nothing. Each arm echoes something distinct, so "detects correctly" is
# distinguishable from "merely avoided the catch-all".
guarded_recipe() {
    local lib="$1"; shift
    env -i PATH="$PATH" HOME="$HOME" "$@" bash -c '
        HOST=unknown
        _dh="$1"
        [ -r "$_dh" ] && . "$_dh" && command -v detect_host >/dev/null 2>&1 \
            && HOST="$(detect_host)"
        case "$HOST" in
            craft)       echo GOT-CRAFT ;;
            claude-code) echo GOT-CLAUDE ;;
            *)           echo LEAST-CAPABLE ;;
        esac' _ "$lib" 2>/dev/null
}

check "recipe: missing library reaches the catch-all" \
    "LEAST-CAPABLE" "$(guarded_recipe /nonexistent/detect-host.sh)"
check "recipe: present library detects craft specifically" \
    "GOT-CRAFT" "$(guarded_recipe "$DETECT" CRAFT_IS_PACKAGED=true)"
check "recipe: present library detects claude-code specifically" \
    "GOT-CLAUDE" "$(guarded_recipe "$DETECT" CLAUDECODE=1)"

# A library that exists but is broken must also reach the catch-all rather than
# taking the caller down with it.
_broken="$(mktemp)"; printf 'detect_host() {\n  echo unterminated\n' >"$_broken"
check "recipe: syntactically broken library reaches the catch-all" \
    "LEAST-CAPABLE" "$(guarded_recipe "$_broken" CRAFT_IS_PACKAGED=true)"
_unreadable="$(mktemp)"; printf 'detect_host(){ echo craft; }\n' >"$_unreadable"; chmod 000 "$_unreadable"
check "recipe: unreadable library reaches the catch-all" \
    "LEAST-CAPABLE" "$(guarded_recipe "$_unreadable" CRAFT_IS_PACKAGED=true)"
rm -f "$_broken"; chmod 600 "$_unreadable" 2>/dev/null; rm -f "$_unreadable"

# --- sourceable as well as executable ---

sourced=$(env -i PATH="$PATH" HOME="$HOME" CRAFT_IS_PACKAGED=true bash -c \
    "source '$DETECT'; detect_host" 2>/dev/null)
check "sourceable: detect_host available as a function" craft "$sourced"

# Sourcing must not print anything by itself — a library that echoes on source
# corrupts any hook that sources it before writing its own output.
noise=$(env -i PATH="$PATH" HOME="$HOME" bash -c "source '$DETECT'" 2>/dev/null)
check "sourcing is silent" "" "$noise"

report
