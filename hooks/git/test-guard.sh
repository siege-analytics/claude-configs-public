#!/bin/bash
# Hook: test-guard
# Enforces: _testing-frameworks-rules.md (testing-frameworks:3)
# Trigger: PreToolUse on Bash(git push *), Bash(gh pr create *), Bash(gh pr merge *)
#
# Blocks pushes/PR-creates/PR-merges when the project declares a
# testing: section in PROJECT.md and the test-gate.json signal file
# is missing or lacks evidence for touched source files.
#
# Projects without a testing: section in PROJECT.md are unaffected
# (exit 0). Once a project declares testing, it demands evidence.
#
# Override: [run-skip: reason] in the latest commit message.
#
# Ref: claude-configs-public#386

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Trigger on git push, gh pr create / merge (GitHub), or glab mr create / merge
# (GitLab). Word boundaries via portable character-class form (not
# BSD-incompatible \b); mirrors self-review.sh. CCP#201 pattern.
TRIGGERS='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge)|glab[[:space:]]+mr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if ! echo "$COMMAND" | grep -qE "$TRIGGERS"; then
    exit 0
fi

# Multi-statement-with-cd yield (mirrors branch-guard.sh, issue #101).
CD_COUNT=$(echo "$COMMAND" | { grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    case "$COMMAND" in
        *$'\n'*|*';'*|*'||'*) exit 0 ;;
    esac
    if [[ "$CD_COUNT" -gt 1 ]]; then
        exit 0
    fi
fi

if [[ -z "$CWD" ]]; then
    exit 0
fi

# Resolve effective CWD when command starts with cd <path>
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
        OUTER_TOP=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || echo "")
        TARGET_TOP=$(git -C "$CD_TARGET" rev-parse --show-toplevel 2>/dev/null || echo "")
        if [[ -z "$TARGET_TOP" ]]; then
            exit 0
        fi
        if [[ "$OUTER_TOP" != "$TARGET_TOP" ]]; then
            exit 0
        fi
        EFFECTIVE_CWD="$CD_TARGET"
    else
        exit 0
    fi
fi

REPO_ROOT=$(git -C "$EFFECTIVE_CWD" rev-parse --show-toplevel 2>/dev/null || echo "")
if [[ -z "$REPO_ROOT" ]]; then
    exit 0
fi

# --- Check for PROJECT.md with testing: section ---
# Look for PROJECT.md in the repo root OR in projects/*/PROJECT.md
# (claude-configs-public layout). If no testing: section found,
# exit 0 — this project doesn't demand test evidence.
HAS_TESTING=false

find_testing_section() {
    local manifest="$1"
    if [[ -f "$manifest" ]]; then
        if grep -q '^testing:' "$manifest" 2>/dev/null || \
           grep -q '^  testing:' "$manifest" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Check repo-root PROJECT.md
if find_testing_section "$REPO_ROOT/PROJECT.md"; then
    HAS_TESTING=true
fi

# Check projects/*/PROJECT.md (claude-configs-public layout)
if [[ "$HAS_TESTING" = "false" ]] && [[ -d "$REPO_ROOT/projects" ]]; then
    for proj_manifest in "$REPO_ROOT"/projects/*/PROJECT.md; do
        if [[ -f "$proj_manifest" ]] && find_testing_section "$proj_manifest"; then
            HAS_TESTING=true
            break
        fi
    done
fi

if [[ "$HAS_TESTING" = "false" ]]; then
    exit 0
fi

# --- Check for [run-skip: reason] override in latest commit ---
LATEST_MSG=$(git -C "$EFFECTIVE_CWD" log -1 --format=%B 2>/dev/null || echo "")
if echo "$LATEST_MSG" | grep -qE '\[run-skip:[[:space:]]'; then
    echo "WARNING: test-guard: [run-skip] override found in latest commit." >&2
    echo "Test evidence verification skipped. Track override frequency." >&2
    exit 0
fi

# --- Check for test-gate.json ---
# Look in workspace root first (Craft Agent), then repo root.
SIGNAL_FILE=""
WORKSPACE_ROOT="${CRAFT_WORKSPACE_ROOT:-}"
if [[ -n "$WORKSPACE_ROOT" ]] && [[ -f "$WORKSPACE_ROOT/test-gate.json" ]]; then
    SIGNAL_FILE="$WORKSPACE_ROOT/test-gate.json"
elif [[ -f "$REPO_ROOT/test-gate.json" ]]; then
    SIGNAL_FILE="$REPO_ROOT/test-gate.json"
fi

if [[ -z "$SIGNAL_FILE" ]]; then
    cat >&2 <<EOF
BLOCKED: Project declares testing: in PROJECT.md but no test-gate.json found.

The test-guard hook requires test evidence before pushing. Run affected
tests via [skill:commit] step 4, which writes test-gate.json after tests
pass.

If tests are genuinely inapplicable, add [run-skip: reason] to the
commit message body.

See [skill:testing-frameworks] and [rule:testing-frameworks] for details.
Ref: #386
EOF
    exit 2
fi

# --- Verify evidence covers touched files ---
# Get list of source files changed relative to the merge base.
MERGE_BASE=$(git -C "$EFFECTIVE_CWD" merge-base HEAD origin/develop 2>/dev/null || \
             git -C "$EFFECTIVE_CWD" merge-base HEAD origin/main 2>/dev/null || echo "")

if [[ -z "$MERGE_BASE" ]]; then
    echo "WARNING: test-guard: cannot determine merge base. Yielding." >&2
    exit 0
fi

TOUCHED_FILES=$(git -C "$EFFECTIVE_CWD" diff --name-only "$MERGE_BASE"...HEAD 2>/dev/null || echo "")
if [[ -z "$TOUCHED_FILES" ]]; then
    exit 0
fi

# Filter to source files only (exclude docs, configs, tests themselves)
SOURCE_FILES=""
while IFS= read -r f; do
    case "$f" in
        *.py|*.js|*.ts|*.jsx|*.tsx|*.scala|*.java|*.kt|*.rs|*.sql)
            # Exclude test files themselves
            case "$f" in
                test_*|*_test.*|*.test.*|*.spec.*|tests/*|__tests__/*) ;;
                *) SOURCE_FILES="${SOURCE_FILES}${f}"$'\n' ;;
            esac
            ;;
    esac
done <<< "$TOUCHED_FILES"

if [[ -z "$SOURCE_FILES" ]]; then
    exit 0
fi

# Check each source file against the signal file evidence
MISSING=""
while IFS= read -r src; do
    [[ -z "$src" ]] && continue
    if ! python3 -c "
import json, sys
try:
    data = json.load(open('$SIGNAL_FILE'))
    evidence = data.get('evidence', [])
    found = any(e.get('source','').endswith('$src') or '$src'.endswith(e.get('source','')) for e in evidence)
    sys.exit(0 if found else 1)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        MISSING="${MISSING}  - ${src}"$'\n'
    fi
done <<< "$SOURCE_FILES"

if [[ -n "$MISSING" ]]; then
    cat >&2 <<EOF
BLOCKED: Test evidence missing for touched source files.

The following files were modified but have no recorded test evidence
in test-gate.json:

${MISSING}
Run affected tests via [skill:commit] step 4 to update test-gate.json,
or add [run-skip: reason] to the commit body if tests are inapplicable.

See [skill:testing-frameworks] and [rule:testing-frameworks] for details.
Ref: #386
EOF
    exit 2
fi

exit 0
