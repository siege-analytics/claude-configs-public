#!/bin/bash
# Hook: branch-guard
# Enforces: develop-guard skill, branch skill, commit skill (step 0)
# Trigger: PreToolUse on Bash(git commit *)
#
# Blocks commits to protected branches (main, develop, master, etc.).
# The agent must create a feature branch first.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)

# Match `git commit` anywhere in the command, not just at the start, so
# forms like `cd /tmp/foo && git commit ...` and `bash -c "git commit ..."`
# don't slip through. Known limitations (see issues #97, #98): commands
# that invoke a script which itself runs git commit (`bash wrapper.sh`)
# are not inspected; `git -C <path> commit` without a leading `cd` is not
# parsed for its target path.
if ! echo "$COMMAND" | grep -qE '\bgit commit\b'; then
    exit 0
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
CD_COUNT=$(echo "$COMMAND" | grep -oE '\bcd[[:space:]]' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    if [[ "$CD_COUNT" -gt 1 ]] || echo "$COMMAND" | grep -qE $'\n|;|\\|\\|'; then
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
    cat >&2 <<EOF
BLOCKED: Direct commit to '$BRANCH' is not allowed.

Create a feature branch first:
  git checkout -b feature/your_description

This is enforced by the develop-guard and branch skills.
EOF
    exit 2
fi

exit 0
