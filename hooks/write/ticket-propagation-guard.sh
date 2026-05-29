#!/usr/bin/env bash
# Hook: write/ticket-propagation-guard
# Enforces: artifact-to-ticket propagation (#251)
# Trigger: PreToolUse on Write and Edit
#
# When an agent writes an artifact (plans/*.md, docs/investigations/*.md)
# whose body contains ticket references, this hook requires either:
#   1. ticket_refs: frontmatter declaring propagation intent
#   2. propagation-deferred: <reason> frontmatter acknowledging the skip
#   3. scratch-* filename prefix (exploratory drafts exempt)
#
# This is the mechanical trigger that fires at artifact-creation time
# without requiring agent volition. See #251 for the failure evidence:
# the agent who filed the propagation rule still elided it on the next
# artifact in the same session.
#
# Exit 0 = allow, Exit 2 = block with message.

set -uo pipefail

INPUT=$(cat)

# --- Parse file_path ---
if command -v jq >/dev/null 2>&1; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || echo "")
else
    FILE_PATH=$(printf '%s' "$INPUT" \
        | node -e \
        'const d=JSON.parse(require("fs").readFileSync("/dev/stdin","utf8")); process.stdout.write((d.tool_input?.file_path||d.tool_input?.path||""))' \
        2>/dev/null || echo "")
fi

[[ -z "$FILE_PATH" ]] && exit 0

# --- Path filter: only fire for artifact paths ---
BASENAME=$(basename "$FILE_PATH")

# Must be a markdown file
[[ "$BASENAME" != *.md ]] && exit 0

# scratch-* prefix is the exploratory-draft escape hatch
[[ "$BASENAME" == scratch-* ]] && exit 0

# Only match artifact directories
ARTIFACT_PATH=false
case "$FILE_PATH" in
    */plans/*.md|*/plans/**/*.md)       ARTIFACT_PATH=true ;;
    */docs/investigations/*.md)          ARTIFACT_PATH=true ;;
    */docs/investigations/**/*.md)       ARTIFACT_PATH=true ;;
esac
[[ "$ARTIFACT_PATH" == "false" ]] && exit 0

# --- Extract content ---
# For Write: tool_input.content
# For Edit: read existing file from disk (frontmatter may already exist)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")

if [[ "$TOOL_NAME" == "Edit" ]]; then
    # For Edit, read the file from disk to check existing frontmatter.
    # If the file already has valid frontmatter, allow the edit.
    if [[ -f "$FILE_PATH" ]]; then
        CONTENT=$(cat "$FILE_PATH")
    else
        # File doesn't exist yet (unusual for Edit), allow
        exit 0
    fi
else
    # Write tool: extract content from tool_input
    if command -v jq >/dev/null 2>&1; then
        CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty' 2>/dev/null || echo "")
    else
        CONTENT=$(printf '%s' "$INPUT" \
            | node -e \
            'const d=JSON.parse(require("fs").readFileSync("/dev/stdin","utf8")); process.stdout.write(d.tool_input?.content||"")' \
            2>/dev/null || echo "")
    fi
fi

[[ -z "$CONTENT" ]] && exit 0

# --- Extract frontmatter (between first pair of --- markers) ---
FRONTMATTER=$(echo "$CONTENT" | sed -n '/^---$/,/^---$/p' | sed '1d;$d')

# --- Scan body (below frontmatter) for ticket references ---
# Body = everything after the second --- marker. If no frontmatter, body is everything.
if echo "$CONTENT" | head -1 | grep -q '^---$'; then
    # Has frontmatter: skip past the closing ---
    BODY=$(echo "$CONTENT" | awk 'BEGIN{n=0} /^---$/{n++; if(n==2){found=1; next}} found{print}')
else
    BODY="$CONTENT"
fi

# Ticket reference patterns (org-qualified only, no bare #N)
TICKET_REGEX='(siege-analytics|electinfo)/[^#[:space:]]+#[0-9]+|github\.com/[^/]+/[^/]+/(issues|pull)/[0-9]+'

FOUND_REFS=$(echo "$BODY" | grep -oE "$TICKET_REGEX" | sort -u)

# No ticket refs in body → nothing to enforce
[[ -z "$FOUND_REFS" ]] && exit 0

# --- Check frontmatter for ticket_refs or propagation-deferred ---

# Check for ticket_refs: with at least one entry
HAS_TICKET_REFS=false
if echo "$FRONTMATTER" | grep -qE '^ticket_refs:'; then
    # Verify it's not empty (must have at least one line with - after it)
    REFS_BLOCK=$(echo "$CONTENT" | sed -n '/^ticket_refs:/,/^[^[:space:]-]/p' | tail -n +2 | grep -E '^\s+-' || true)
    if [[ -n "$REFS_BLOCK" ]]; then
        HAS_TICKET_REFS=true
    fi
fi

# Check for propagation-deferred: with a non-empty, non-boolean reason
HAS_DEFERRED=false
if echo "$FRONTMATTER" | grep -qE '^propagation-deferred:'; then
    DEFERRED_VALUE=$(echo "$FRONTMATTER" | grep -E '^propagation-deferred:' | sed 's/^propagation-deferred:[[:space:]]*//')
    # Reject empty, false, true — must be a real reason string
    if [[ -n "$DEFERRED_VALUE" ]] && [[ "$DEFERRED_VALUE" != "false" ]] && [[ "$DEFERRED_VALUE" != "true" ]]; then
        HAS_DEFERRED=true
    fi
fi

if [[ "$HAS_TICKET_REFS" == "true" ]] || [[ "$HAS_DEFERRED" == "true" ]]; then
    exit 0
fi

# --- Block: ticket refs found but no propagation metadata ---
REF_LIST=$(echo "$FOUND_REFS" | sed 's/^/  /')

cat >&2 <<HOOKEOF

BLOCKED by ticket-propagation-guard (siege-analytics/claude-configs-public#251).

File: $FILE_PATH
Found ticket references in body but no propagation metadata in frontmatter:
$REF_LIST

Resolution (choose one):

  1. Add ticket_refs: frontmatter listing each ticket:
     ---
     ticket_refs:
       - siege-analytics/repo#N: comment posted
       - siege-analytics/repo#M: comment pending
     ---

  2. Add propagation-deferred: with a reason:
     ---
     propagation-deferred: workspace-only draft, will propagate after review
     ---

  3. Use scratch- filename prefix (plans/scratch-*.md) for exploratory drafts.

HOOKEOF
exit 2
