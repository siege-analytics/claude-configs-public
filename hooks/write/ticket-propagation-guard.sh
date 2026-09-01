#!/usr/bin/env bash
# Hook: write/ticket-propagation-guard
# Enforces: artifact-to-ticket propagation (#251)
# Trigger: PreToolUse on Write, Edit, MultiEdit and NotebookEdit
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

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
AFTER_IMAGE="$HOOK_DIR/../lib/after-image.py"

# --- Parse the target path ---
FILE_PATH=$(printf '%s' "$INPUT" | python3 "$AFTER_IMAGE" path)
PATH_STATUS=$?

# A missing or broken helper must not silently empty the path and allow the
# write. `path` succeeds for any payload, so a non-zero status here is the
# helper failing, not an irrelevant tool.
if [[ "$PATH_STATUS" -ne 0 ]]; then
    printf '\nBLOCKED by ticket-propagation-guard: hooks/lib/after-image.py failed (status %d).\nThe guard fails closed when its payload resolver is unavailable.\n\n' "$PATH_STATUS" >&2
    exit 2
fi

[[ -z "$FILE_PATH" ]] && exit 0

# --- Path filter: only fire for artifact paths ---
BASENAME=$(basename "$FILE_PATH")

# A separate `*.md` test used to sit here. Every pattern in the case block below
# already ends in `.md`, so it could be deleted with no scenario changing, which
# is the definition of a check that is not doing anything.
#
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

# --- Extract the content this write would leave on disk ---
# Reading the file from disk checks the wrong document: an Edit that introduces
# the first ticket reference into a clean artifact is judged against the clean
# pre-image and allowed. See hooks/lib/after-image.py.
#
# Exit 3 means the payload is a write whose result cannot be determined -- an
# unhandled tool, or malformed edit strings. That must block rather than fall
# through as an empty document, which is how MultiEdit and NotebookEdit payloads
# passed unchecked.
CONTENT=$(printf '%s' "$INPUT" | python3 "$AFTER_IMAGE" content)
AFTER_IMAGE_STATUS=$?

if [[ "$AFTER_IMAGE_STATUS" -ne 0 ]]; then
    printf '\nBLOCKED by ticket-propagation-guard: cannot determine the result of this write for %s (hooks/lib/after-image.py status %d).\nThe guard fails closed on payloads it cannot resolve.\n\n' \
        "$FILE_PATH" "$AFTER_IMAGE_STATUS" >&2
    exit 2
fi

[[ -z "$CONTENT" ]] && exit 0

# --- Split frontmatter from body ---
# Everything here avoids `cmd | grep -q` and `cmd | head` on large variables.
# Under `set -o pipefail` those pipelines fail spuriously once the variable
# exceeds the pipe buffer: the reader exits early, the writer takes SIGPIPE,
# and 141 becomes the pipeline's status. That made the guard ignore valid
# frontmatter on large artifacts only, which is #688.
#
# The old frontmatter extraction also used `sed -n '/^---$/,/^---$/p'`, whose
# range restarts at every `---` in the body. On a document with horizontal
# rules that captured most of the file as "frontmatter".
#
# Treating the first `---` after line 1 as the closing delimiter is not enough
# either. A document whose opener is never closed has the prose above its first
# horizontal rule read as metadata, which lets a `propagation-deferred:` line
# quoted inside a fenced code block satisfy this guard. The split therefore
# requires the candidate region to be YAML-shaped and fails closed otherwise.
# See hooks/lib/split-frontmatter.py.
SPLIT="$HOOK_DIR/../lib/split-frontmatter.py"
FRONTMATTER=$(printf '%s' "$CONTENT" | python3 "$SPLIT" frontmatter)
SPLIT_STATUS=$?
BODY=$(printf '%s' "$CONTENT" | python3 "$SPLIT" body)
BODY_STATUS=$?

# A missing or failing helper must not empty both halves and allow the write.
if [[ "$SPLIT_STATUS" -ne 0 ]] || [[ "$BODY_STATUS" -ne 0 ]]; then
    printf '\nBLOCKED by ticket-propagation-guard: hooks/lib/split-frontmatter.py failed (status %d/%d).\nThe guard fails closed when its frontmatter split is unavailable.\n\n' \
        "$SPLIT_STATUS" "$BODY_STATUS" >&2
    exit 2
fi

# Ticket reference patterns (org-qualified only, no bare #N)
TICKET_REGEX='(siege-analytics|electinfo)/[^#[:space:]]+#[0-9]+|github\.com/[^/]+/[^/]+/(issues|pull)/[0-9]+'

FOUND_REFS=$(echo "$BODY" | { grep -oE "$TICKET_REGEX" || true; } | sort -u)

# No ticket refs in body → nothing to enforce
[[ -z "$FOUND_REFS" ]] && exit 0

# --- Check frontmatter for ticket_refs or propagation-deferred ---

# Check for ticket_refs: with at least one entry
HAS_TICKET_REFS=false
# Scoped to FRONTMATTER, so a `ticket_refs:` line in the body cannot satisfy it.
REFS_BLOCK=$(awk '
    /^ticket_refs:/ { f = 1; next }
    f && /^[[:space:]]+-/ { print; next }
    f { exit }
' <<< "$FRONTMATTER")
if [[ -n "$REFS_BLOCK" ]]; then
    HAS_TICKET_REFS=true
fi

# Check for propagation-deferred: with a non-empty, non-boolean reason
HAS_DEFERRED=false
DEFERRED_VALUE=$(awk '
    sub(/^propagation-deferred:[[:space:]]*/, "") { print; exit }
' <<< "$FRONTMATTER")
# Reject empty, false, true: must be a real reason string
if [[ -n "$DEFERRED_VALUE" ]] && [[ "$DEFERRED_VALUE" != "false" ]] && [[ "$DEFERRED_VALUE" != "true" ]]; then
    HAS_DEFERRED=true
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
