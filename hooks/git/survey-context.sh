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
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

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
# Also collect optional Watched paths (v2.2): glob patterns the entity doc declares
# alongside the Definition. Build TUPLES like:
#   "def|<path>|<name>|<doc_page>"        for Definition matches
#   "wp|<pattern>|<name>|<doc_page>"      for Watched-path matches
# The prefix lets the BLOCK message distinguish v2.1 vs v2.2 triggers.
TUPLES=()
for entry in "${ENTITIES[@]}"; do
    name="${entry%%|*}"
    doc_page="${entry##*|}"
    doc_abs="$REPO_ROOT/$doc_page"
    [[ ! -f "$doc_abs" ]] && continue

    # Definition line: **Definition:** `path/to/file.py:LINE`
    def_line=$(grep -m1 -E '^\*\*Definition:\*\*[[:space:]]+`' "$doc_abs" 2>/dev/null || true)
    if [[ -n "$def_line" ]]; then
        def_path=$(echo "$def_line" | sed -E 's/^\*\*Definition:\*\*[[:space:]]+`([^:`]+)(:[0-9]+)?`.*/\1/')
        if [[ -n "$def_path" ]]; then
            TUPLES+=("def|$def_path|$name|$doc_page")
        fi
    fi

    # v2.2: optional Watched-paths line. Format:
    #   **Watched paths:** `pat1`, `pat2`, `pat3`
    # Globs are matched against repo-root-relative diff paths via case+glob.
    # Comma-separated; per-pattern backtick-quoted.
    wp_line=$(grep -m1 -E '^\*\*Watched paths:\*\*[[:space:]]+' "$doc_abs" 2>/dev/null || true)
    if [[ -n "$wp_line" ]]; then
        # Strip the leading label + extract everything between backticks.
        wp_rest="${wp_line#*Watched paths:**}"
        # Extract every `quoted` token.
        while [[ "$wp_rest" =~ \`([^\`]+)\` ]]; do
            pattern="${BASH_REMATCH[1]}"
            wp_rest="${wp_rest#*\`${pattern}\`}"
            TUPLES+=("wp|$pattern|$name|$doc_page")
        done
    fi
done

if [[ "${#TUPLES[@]}" -eq 0 ]]; then
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

# Walk every (kind, pattern, name, doc_page); for each diff file that matches,
# require doc_page also in DIFF_FILES or Doc-Update-Source trailer.
# kind = "def" => exact path match; kind = "wp" => glob match (v2.2).
# Violation entries record kind for the BLOCK message.
VIOLATIONS=()
seen_violation=""  # de-dupe per (name|doc_page|kind) so multiple wp matches collapse
while IFS= read -r diff_file; do
    [[ -z "$diff_file" ]] && continue
    for tup in "${TUPLES[@]}"; do
        kind="${tup%%|*}"; rest="${tup#*|}"
        pattern="${rest%%|*}"; rest="${rest#*|}"
        name="${rest%%|*}"; doc_page="${rest##*|}"

        matched=0
        if [[ "$kind" == "def" ]]; then
            [[ "$diff_file" == "$pattern" ]] && matched=1
        else
            # Glob match via bash's `case` (supports * ? [] but not **).
            case "$diff_file" in
                $pattern) matched=1 ;;
            esac
        fi
        [[ "$matched" -eq 0 ]] && continue

        # Already satisfied? doc page touched or trailer escape present.
        if echo "$DIFF_FILES" | grep -qxF "$doc_page"; then
            continue
        fi
        if [[ "$HAS_DOC_UPDATE_SOURCE" -gt 0 ]]; then
            continue
        fi

        # De-dupe per (kind, name, doc_page) so 5 watched-path matches against
        # the same entity collapse to one violation line.
        dedupe_key="${kind}|${name}|${doc_page}"
        case " $seen_violation " in
            *" $dedupe_key "*) continue ;;
        esac
        seen_violation="$seen_violation $dedupe_key"

        VIOLATIONS+=("$kind|$name|$pattern|$doc_page|$diff_file")
    done
done <<< "$DIFF_FILES"

if [[ "${#VIOLATIONS[@]}" -eq 0 ]]; then
    exit 0
fi

{
    echo "BLOCKED: pushed diff touches files associated with documented entities"
    echo "but the corresponding doc page(s) are untouched. The survey-context"
    echo "skill requires shape and contract changes to update the entity doc"
    echo "in the same PR."
    echo ""
    for v in "${VIOLATIONS[@]}"; do
        kind="${v%%|*}"; rest="${v#*|}"
        name="${rest%%|*}"; rest="${rest#*|}"
        pattern="${rest%%|*}"; rest="${rest#*|}"
        doc_page="${rest%%|*}"; matched_file="${rest##*|}"
        echo "  - Entity: $name"
        if [[ "$kind" == "def" ]]; then
            echo "    Trigger: [v2.1 definition-file match]"
            echo "    Touched definition: $matched_file"
        else
            echo "    Trigger: [v2.2 watched-path match]"
            echo "    Watched pattern: $pattern"
            echo "    Matched diff file: $matched_file"
        fi
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
