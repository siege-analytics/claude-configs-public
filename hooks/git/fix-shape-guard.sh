#!/bin/bash
# Hook: fix-shape-guard
# Enforces: writing-rules:7 (pattern detection across same-shape fixes)
# Trigger: PreToolUse on Bash(git push *), Bash(gh pr create *)
#
# When N>=3 commits on the current feature branch share the same
# conventional-commit scope (e.g., fix(geo):, fix(geo):, fix(geo):),
# or touch the same file set, this hook requires a Class-Audit: trailer
# in the latest commit proving the agent considered the pattern as a class.
#
# v1: scope repetition + file-overlap detection (cheap, no AST).
# Ref: #188

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    if git rev-parse --git-dir >/dev/null 2>&1; then
        COMMAND="git push"
        CWD="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    else
        exit 0
    fi
fi

TRIGGERS='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if ! echo "$COMMAND" | grep -qE "$TRIGGERS"; then
    exit 0
fi

EFFECTIVE_CWD="$CWD"
if [[ "$COMMAND" =~ ^[[:space:]]*cd[[:space:]]+([^[:space:];&]+) ]]; then
    CD_TARGET="${BASH_REMATCH[1]}"
    CD_TARGET="${CD_TARGET%\"}"; CD_TARGET="${CD_TARGET#\"}"
    CD_TARGET="${CD_TARGET%\'}"; CD_TARGET="${CD_TARGET#\'}"
    case "$CD_TARGET" in
        /*) ;;
        *) CD_TARGET="$CWD/$CD_TARGET" ;;
    esac
    if [[ -d "$CD_TARGET" ]]; then
        EFFECTIVE_CWD="$CD_TARGET"
    fi
fi

if [[ -z "$EFFECTIVE_CWD" ]] || ! git -C "$EFFECTIVE_CWD" rev-parse --git-dir >/dev/null 2>&1; then
    exit 0
fi

BRANCH=$(git -C "$EFFECTIVE_CWD" rev-parse --abbrev-ref HEAD 2>/dev/null || true)
if [[ -z "$BRANCH" ]] || [[ "$BRANCH" == "HEAD" ]] || [[ "$BRANCH" == "main" ]] || [[ "$BRANCH" == "master" ]] || [[ "$BRANCH" == "develop" ]]; then
    exit 0
fi

MERGE_BASE=$(git -C "$EFFECTIVE_CWD" merge-base develop HEAD 2>/dev/null || git -C "$EFFECTIVE_CWD" merge-base main HEAD 2>/dev/null || true)
if [[ -z "$MERGE_BASE" ]]; then
    exit 0
fi

BRANCH_SUBJECTS=$(git -C "$EFFECTIVE_CWD" log "$MERGE_BASE..HEAD" --format='%s' 2>/dev/null || true)
if [[ -z "$BRANCH_SUBJECTS" ]]; then
    exit 0
fi

COMMIT_COUNT=$(echo "$BRANCH_SUBJECTS" | wc -l | tr -d ' ')
if [[ "$COMMIT_COUNT" -lt 3 ]]; then
    exit 0
fi

THRESHOLD=3

# Check 1: conventional-commit scope repetition.
# Extract fix(<scope>): or feat(<scope>): scopes from commit subjects.
SCOPES=$(echo "$BRANCH_SUBJECTS" | grep -oE '^(fix|feat|refactor|chore)\([^)]+\)' | sed -E 's/^[^(]+\(([^)]+)\)/\1/' | sort | uniq -c | sort -rn || true)

REPEATED_SCOPE=""
if [[ -n "$SCOPES" ]]; then
    TOP_COUNT=$(echo "$SCOPES" | head -1 | awk '{print $1}')
    TOP_SCOPE=$(echo "$SCOPES" | head -1 | awk '{print $2}')
    if [[ "$TOP_COUNT" -ge "$THRESHOLD" ]]; then
        REPEATED_SCOPE="$TOP_SCOPE"
    fi
fi

# Check 2: file-overlap repetition.
# Count how many commits touch the same file. If any file appears in N>=3
# commits, that's a file-overlap pattern.
REPEATED_FILE=""
if [[ -z "$REPEATED_SCOPE" ]]; then
    FILE_COUNTS=$(git -C "$EFFECTIVE_CWD" log "$MERGE_BASE..HEAD" --name-only --format='' 2>/dev/null | grep -v '^$' | sort | uniq -c | sort -rn || true)
    if [[ -n "$FILE_COUNTS" ]]; then
        TOP_FILE_COUNT=$(echo "$FILE_COUNTS" | head -1 | awk '{print $1}')
        TOP_FILE=$(echo "$FILE_COUNTS" | head -1 | awk '{$1=""; print $0}' | sed 's/^ //')
        if [[ "$TOP_FILE_COUNT" -ge "$THRESHOLD" ]]; then
            REPEATED_FILE="$TOP_FILE"
        fi
    fi
fi

if [[ -z "$REPEATED_SCOPE" ]] && [[ -z "$REPEATED_FILE" ]]; then
    exit 0
fi

COMMIT_MSG=$(git -C "$EFFECTIVE_CWD" log -1 --pretty=%B 2>/dev/null || true)
CLASS_AUDIT=$(echo "$COMMIT_MSG" | { grep -E '^Class-Audit:[[:space:]]+\S' || true; } | head -1)

if [[ -n "$CLASS_AUDIT" ]]; then
    exit 0
fi

NO_CLASS_AUDIT=$(echo "$COMMIT_MSG" | { grep -F '[no-class-audit' || true; } | head -1)
if [[ -n "$NO_CLASS_AUDIT" ]]; then
    exit 0
fi

if [[ -n "$REPEATED_SCOPE" ]]; then
    cat >&2 <<HOOKEOF
BLOCKED: ${TOP_COUNT} commits on this branch share scope '${REPEATED_SCOPE}'
(N>=${THRESHOLD} same-scope pattern detected).

Per writing-rules:7, when the same fix shape repeats across commits,
the pattern itself needs examination. Add a Class-Audit: trailer:

  Class-Audit: ${REPEATED_SCOPE} — N=${TOP_COUNT} fixes address the same root cause (describe)
  Class-Audit: ${REPEATED_SCOPE} — independent fixes, same scope is coincidental

Or override with evidence:
  [no-class-audit: Reason / Evidence / Falsification]

Ref: #188 (fix-shape detection)
HOOKEOF
    exit 2
fi

if [[ -n "$REPEATED_FILE" ]]; then
    cat >&2 <<HOOKEOF
BLOCKED: File '${REPEATED_FILE}' touched in ${TOP_FILE_COUNT} commits on this branch
(N>=${THRESHOLD} same-file pattern detected).

Per writing-rules:7, repeated edits to the same file suggest a pattern
that should be examined as a class. Add a Class-Audit: trailer:

  Class-Audit: ${REPEATED_FILE} — N=${TOP_FILE_COUNT} edits address the same root cause (describe)
  Class-Audit: ${REPEATED_FILE} — independent changes, file overlap is coincidental

Or override with evidence:
  [no-class-audit: Reason / Evidence / Falsification]

Ref: #188 (fix-shape detection)
HOOKEOF
    exit 2
fi

exit 0
