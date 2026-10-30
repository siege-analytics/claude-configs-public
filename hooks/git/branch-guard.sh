#!/bin/bash
# Hook: branch-guard
# Enforces: develop-guard skill, branch skill, commit skill (step 0)
# Trigger: PreToolUse on Bash(git commit *)
#
# Blocks commits to protected branches (main, develop, master, etc.).
# The agent must create a feature branch first.

# shellcheck source=../lib/command-text.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/command-text.sh"
set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
# Fast skip (#1083): exit before starting python3 when the tool payload's
# command cannot match this hook's trigger. Only taken when tool_input's first
# key is a non-empty "command" (an empty or missing command keeps the git-push
# fallback) and the command uses no JSON escape other than \n \t \r \" \\ \/
# (\u, \f, \b could hide letters or whitespace). \n \t \r become spaces, so an
# escaped newline before the trigger still counts as a boundary. Git-hook
# invocations (refs on stdin, no JSON) take the full path.
_FAST_CMDS=$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"(\\.|[^"\\])*"' 2>/dev/null || true)
# A long command takes the full path (#1098): bash substitutions slow down
# superlinearly under a UTF-8 locale, and past the hook timeout a skip check
# would let the command through. 16 KiB keeps the check in milliseconds.
_FAST_FULL=0; (( ${#_FAST_CMDS} > 16384 )) && { _FAST_FULL=1; _FAST_CMDS=""; }
_FAST_ESC="${_FAST_CMDS//'\\'/}"; _FAST_ESC="${_FAST_ESC//'\"'/}"; _FAST_ESC="${_FAST_ESC//'\/'/}"
_FAST_ESC="${_FAST_ESC//'\n'/}"; _FAST_ESC="${_FAST_ESC//'\t'/}"; _FAST_ESC="${_FAST_ESC//'\r'/}"
_FAST_CMDS="${_FAST_CMDS//'\n'/ }"; _FAST_CMDS="${_FAST_CMDS//'\t'/ }"; _FAST_CMDS="${_FAST_CMDS//'\r'/ }"
# The shell rebuilds words from quotes and backslashes (#1098): `git "add"`,
# `g\it add` and `git  add` all run git add. Match the trigger against the text
# as written and against a copy with quote and backslash characters dropped and
# blanks squeezed; skip only if neither matches. A command containing ANSI-C
# $'...' (which can spell any byte) takes the full path.
[[ "$_FAST_CMDS" == *"\$'"* ]] && _FAST_FULL=1
# A quote or backslash between two letters or digits (`pr"x"`, `x\git`) joins
# words; only the full path's quote handling decides what that runs. In the
# JSON text a shell `"` or `\` is itself escaped, hence the leading backslash.
[[ "$_FAST_CMDS" == *[[:alnum:]]\\[\"\\][[:alnum:]]* || "$_FAST_CMDS" == *[[:alnum:]]\'[[:alnum:]]* ]] && _FAST_FULL=1
_FAST_BUILT="${_FAST_CMDS//[\"\'\\]/}"
while [[ "$_FAST_BUILT" == *"  "* ]]; do _FAST_BUILT="${_FAST_BUILT//  / }"; done
_FAST_FIRST='"tool_input"[[:space:]]*:[[:space:]]*[{][[:space:]]*"command"[[:space:]]*:[[:space:]]*"[^"]'
_FAST_RE='(^|[^[:alnum:]])git([[:space:]]|$)|(^|[^[:alnum:]])(bash|sh|source|\.)[[:space:]]+[^[:space:]-]'
if [[ $_FAST_FULL == 0 && "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE || "$_FAST_BUILT" =~ $_FAST_RE ]]; then exit 0; fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

# Shared literal normalization protects the actual -C/-c/alias target before
# workflow checks. An implementing task never waives protected-branch policy.
GIT_POLICY="$HOOK_DIR/../lib/git_command.py"
if [[ ! -f "$GIT_POLICY" ]]; then
    echo "BLOCKED: Git operation policy helper is unavailable." >&2
    exit 2
fi
GIT_RESULT=$(printf '%s' "$COMMAND" | python3 "$GIT_POLICY" --cwd "${CWD:-$PWD}" --policy branch 2>&1)
GIT_STATUS=$?
if [[ "$GIT_STATUS" -ne 0 ]]; then
    echo "${GIT_RESULT:-BLOCKED: Git operation policy failed.}" >&2
    exit 2
fi

# Match `git commit` anywhere in the command, not just at the start, so
# forms like `cd /tmp/foo && git commit ...` and `bash -c "git commit ..."`
# don't slip through. Global-option and alias targets are checked by the
# shared Git operation policy above.
# Word boundaries via portable character-class form (not BSD-incompatible `\b`);
# see issue #106 (same fix that landed for self-review.sh in same PR).
HAS_GIT_COMMIT=false
if ct_is_git_commit "$COMMAND"; then
    HAS_GIT_COMMIT=true
fi

# Issue #98: catch script-wrapper bypass. When the command executes a shell
# script (bash/sh/source/.), the script may contain git commit internally.
# We can't inspect script contents reliably, but we CAN check whether we're
# on a protected branch — if so, block with a warning regardless.
RUNS_SCRIPT=false
if echo "$COMMAND" | grep -qE '(^|[;&|]+[[:space:]]*)(bash|sh|source|\.)[[:space:]]+[^[:space:]-]'; then
    RUNS_SCRIPT=true
fi

if [ "$HAS_GIT_COMMIT" = "false" ] && [ "$RUNS_SCRIPT" = "false" ]; then
    exit 0
fi

# Content-scope check (#699). Skip out-of-scope repositories.
if [[ -f "$HOOK_DIR/../lib/scope-check.sh" ]]; then
    source "$HOOK_DIR/../lib/scope-check.sh"
    if ! _scope_in_scope "$COMMAND" "${CWD:-$PWD}"; then
        exit 0
    fi
fi

if [[ -z "$CWD" ]]; then
    exit 0  # Can't determine directory, allow
fi

# Multi-statement-with-cd yield: the leading-cd parser below only handles
# a single cd at the start. If the command contains more than one cd OR
# contains any of newline/semicolon/`||` together with at least one cd,
# the effective cwd at the point `git commit` runs may differ from what
# the leading-cd parser captures. Yield rather than risk a false-positive
# block or false-negative pass. See issue #101 for the characterization.
CD_COUNT=$(echo "$COMMAND" | { grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    # Use case instead of grep for newline/semicolon/|| detection.
    # BSD grep on macOS chokes on $'\n' in alternation patterns.
    # See self-review.sh for the same fix.
    case "$COMMAND" in
        *$'\n'*|*';'*|*'||'*) exit 0 ;;
    esac
    if [[ "$CD_COUNT" -gt 1 ]]; then
        exit 0
    fi
fi

# When the command starts with `cd <path>` (followed by `&&` / `;` / EOL),
# the effective commit target is <path>, not $CWD. If that target is in a
# different git repo than $CWD, we can't safely verify the branch from
# this hook's vantage -- yield rather than apply a check that may be
# checking the wrong repo.
EFFECTIVE_CWD="$CWD"
if [[ "$COMMAND" =~ ^[[:space:]]*cd[[:space:]]+([^[:space:];&]+) ]]; then
    CD_TARGET="${BASH_REMATCH[1]}"
    # Strip surrounding single/double quotes if present
    CD_TARGET="${CD_TARGET%\"}"; CD_TARGET="${CD_TARGET#\"}"
    CD_TARGET="${CD_TARGET%\'}"; CD_TARGET="${CD_TARGET#\'}"
    # Resolve relative paths against $CWD
    case "$CD_TARGET" in
        /*) ;;
        *) CD_TARGET="$CWD/$CD_TARGET" ;;
    esac
    if [[ -d "$CD_TARGET" ]]; then
        OUTER_TOP=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || echo "")
        TARGET_TOP=$(git -C "$CD_TARGET" rev-parse --show-toplevel 2>/dev/null || echo "")
        if [[ -z "$TARGET_TOP" ]]; then
            exit 0  # cd target isn't a git repo we can read; yield
        fi
        if [[ "$OUTER_TOP" != "$TARGET_TOP" ]]; then
            exit 0  # cross-repo case; can't safely verify, yield
        fi
        EFFECTIVE_CWD="$CD_TARGET"
    else
        exit 0  # cd target doesn't exist; yield rather than block on $CWD's branch
    fi
fi

BRANCH=$(git -C "$EFFECTIVE_CWD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if [[ -z "$BRANCH" ]]; then
    exit 0  # Not a git repo, allow
fi

# Protected branch patterns
PROTECTED="^(main|master|develop|dev|development|staging|next|integration)$"

if [[ "$BRANCH" =~ $PROTECTED ]]; then
    if [ "$RUNS_SCRIPT" = "true" ] && [ "$HAS_GIT_COMMIT" = "false" ]; then
        cat >&2 <<EOF
BLOCKED: Running a shell script on protected branch '$BRANCH'.

The script may contain git commit or other write operations that bypass
hook inspection. Create a feature branch first, or run the script's
commands directly so hooks can inspect them.

  git checkout -b feature/your_description

This is enforced by the branch-guard hook (see issue #98).
EOF
    else
        cat >&2 <<EOF
BLOCKED: Direct commit to '$BRANCH' is not allowed.

Create a feature branch first:
  git checkout -b feature/your_description

This is enforced by the develop-guard and branch skills.
EOF
    fi
    exit 2
fi

exit 0
