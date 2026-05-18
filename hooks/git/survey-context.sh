#!/bin/bash
# Hook: survey-context (v2.1)
# Enforces: skills/thinking/survey-context/SKILL.md Definition-of-Done rule
# Trigger: PreToolUse on Bash(git push *), Bash(gh pr create *), Bash(gh pr merge *)
#
# When the diff being pushed touches a file listed as the Definition for an
# entity in the project's .agents/skills/survey-context/config.md entity
# catalog, the corresponding doc page must also be in the diff -- OR the
# latest commit carries a Doc-Update-Source: trailer pointing at a sibling
# PR/issue/path where the doc update lives.
#
# v2.1 scope (file-based detection):
#   - Catalog entries parsed from a markdown table with columns:
#       | Name | Type | Namespace | Doc page |
#     and an associated Definition file. The Definition is detected from
#     the entity's doc page front matter or its first **Definition:** line.
#   - Trigger when any pushed file path equals a Definition file path.
#   - Pass when corresponding doc page is in the same push OR when a
#     Doc-Update-Source: trailer is present.
#
# Silent skips (no nag):
#   - No .agents/skills/survey-context/config.md in the repo.
#   - Catalog parses to zero entries.
#   - Pushed diff touches no Definition file.
#
# v2.2 follow-ups (NOT in this hook):
#   - Symbol-based detection (caller diffs, not just definition diffs).
#   - AST-aware shape-change vs cosmetic-change distinction.
#   - Auto-suggest the doc-page edit.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Triggers + leading-cd handling mirror self-review.sh; see issue #106 for
# the BSD-portable boundary form.
TRIGGERS='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if ! echo "$COMMAND" | grep -qE "$TRIGGERS"; then
    exit 0
fi

CD_COUNT=$(echo "$COMMAND" | grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    if [[ "$CD_COUNT" -gt 1 ]] || echo "$COMMAND" | grep -qE $'\n|;|\\|\\|'; then
        exit 0
    fi
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

REPO_ROOT=$(git -C "$EFFECTIVE_CWD" rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "$REPO_ROOT" ]]; then
    exit 0
fi

CONFIG="$REPO_ROOT/.agents/skills/survey-context/config.md"
if [[ ! -f "$CONFIG" ]]; then
    exit 0
fi

# Parse the entity catalog table. Rows look like:
#   | DimGeography | Django model | socialwarehouse.warehouse.models | docs/entities/dim_geography.md |
# Skip header + separator rows. Extract (name, doc_page).
ENTITIES=()
while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*\|[[:space:]]*Name[[:space:]]*\| ]] && continue
    [[ "$line" =~ ^[[:space:]]*\|[[:space:]]*-+[[:space:]]*\| ]] && continue
    [[ ! "$line" =~ ^[[:space:]]*\| ]] && continue
    IFS='|' read -ra COLS <<< "$line"
    [[ "${#COLS[@]}" -lt 5 ]] && continue
    name=$(echo "${COLS[1]}" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
    doc_page=$(echo "${COLS[4]}" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
    [[ -z "$name" || -z "$doc_page" ]] && continue
    ENTITIES+=("$name|$doc_page")
done < "$CONFIG"

if [[ "${#ENTITIES[@]}" -eq 0 ]]; then
    exit 0
fi

# For each entity, find its Definition from the doc page's `**Definition:**` line.
# Build a list of (definition_file, name, doc_page) tuples.
DEFS=()
for entry in "${ENTITIES[@]}"; do
    name="${entry%%|*}"
    doc_page="${entry##*|}"
    doc_abs="$REPO_ROOT/$doc_page"
    [[ ! -f "$doc_abs" ]] && continue
    # **Definition:** `path/to/file.py:LINE`
    def_line=$(grep -m1 -E '^\*\*Definition:\*\*[[:space:]]+`' "$doc_abs" 2>/dev/null || true)
    [[ -z "$def_line" ]] && continue
    def_path=$(echo "$def_line" | sed -E 's/^\*\*Definition:\*\*[[:space:]]+`([^:`]+)(:[0-9]+)?`.*/\1/')
    [[ -z "$def_path" ]] && continue
    DEFS+=("$def_path|$name|$doc_page")
done

if [[ "${#DEFS[@]}" -eq 0 ]]; then
    exit 0
fi

# Determine which files this push covers. Use the range between upstream and
# HEAD; fall back to last commit if no upstream is set yet (first push).
UPSTREAM=$(git -C "$EFFECTIVE_CWD" rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true)
if [[ -n "$UPSTREAM" ]]; then
    DIFF_FILES=$(git -C "$EFFECTIVE_CWD" diff --name-only "$UPSTREAM"..HEAD 2>/dev/null || true)
else
    DIFF_FILES=$(git -C "$EFFECTIVE_CWD" diff --name-only HEAD~1..HEAD 2>/dev/null || true)
fi

if [[ -z "$DIFF_FILES" ]]; then
    exit 0
fi

# Check trailer escape on the latest commit.
COMMIT_MSG=$(git -C "$EFFECTIVE_CWD" log -1 --pretty=%B 2>/dev/null || true)
TRAILERS=$(echo "$COMMIT_MSG" | git -C "$EFFECTIVE_CWD" interpret-trailers --parse --no-divider 2>/dev/null || true)
HAS_DOC_UPDATE_SOURCE=$(echo "$TRAILERS" | grep -cE '^Doc-Update-Source:[[:space:]]+\S' || true)

# Walk every (def_path, name, doc_page); for each whose def_path is in DIFF_FILES,
# require doc_page also in DIFF_FILES or Doc-Update-Source trailer.
VIOLATIONS=()
while IFS= read -r diff_file; do
    [[ -z "$diff_file" ]] && continue
    for tup in "${DEFS[@]}"; do
        def_path="${tup%%|*}"
        rest="${tup#*|}"
        name="${rest%%|*}"
        doc_page="${rest##*|}"
        if [[ "$diff_file" == "$def_path" ]]; then
            if echo "$DIFF_FILES" | grep -qxF "$doc_page"; then
                continue
            fi
            if [[ "$HAS_DOC_UPDATE_SOURCE" -gt 0 ]]; then
                continue
            fi
            VIOLATIONS+=("$name|$def_path|$doc_page")
        fi
    done
done <<< "$DIFF_FILES"

if [[ "${#VIOLATIONS[@]}" -eq 0 ]]; then
    exit 0
fi

{
    echo "BLOCKED: pushed diff modifies entity definition files without touching"
    echo "the corresponding doc page(s). The survey-context skill requires shape"
    echo "changes to update the entity doc in the same PR."
    echo ""
    for v in "${VIOLATIONS[@]}"; do
        name="${v%%|*}"; rest="${v#*|}"
        def_path="${rest%%|*}"; doc_page="${rest##*|}"
        echo "  - Entity: $name"
        echo "    Touched definition: $def_path"
        echo "    Doc page (untouched): $doc_page"
    done
    echo ""
    echo "Either:"
    echo "  - Update the doc page(s) above in the same PR (add to your branch)."
    echo "  - Add a Doc-Update-Source: <ref> trailer to the latest commit"
    echo "    pointing at the sibling PR/issue where the doc update lands."
    echo ""
    echo "See skills/thinking/survey-context/SKILL.md for the DoD contract."
    echo "Project catalog: $CONFIG"
} >&2
exit 2
