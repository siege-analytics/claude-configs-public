#!/bin/bash
# evaluate-ticket.sh — ticket structural-fitness rubric
#
# Usage: evaluate-ticket.sh <ticket-ref>
#   <ticket-ref> := '#NNN'                          (owner/repo from `gh repo view`)
#                 | 'owner/repo#NNN'                (cross-repo GitHub)
#                 | 'PROJ-NNN'                      (Linear / Jira; stubbed)
#                 | local file path                  (design-note-as-ticket)
#
# Verifies that the ticket meets the structural-fitness rubric so the
# work it grounds is groundable. Six checks:
#
#   1. Title is a complete sentence with subject + verb (heuristic).
#   2. Body has the canonical sections: Context / Goal / Acceptance.
#      (Repo-local override is NOT supported per session 260502-vital-channel
#      direction: canonical across all repos.)
#   3. Body cites ≥1 falsifiable observation token (link, command,
#      fenced code block, stat). Same EVIDENCE_TOKEN_RE family as
#      check-trivial-claim.sh.
#   4. Body links to a `/think` design note (recognized via
#      `plans/think-*.md` path, explicit `Design: <path>` line, or an
#      inline design note inside the ticket body following the think
#      SKILL structure).
#   5. Body has an `## Assumptions` block.
#   6. For behavior-change tickets (label `behavior-change`/`feature`/
#      `bug`): body states falsification in writing-tests:1 shape
#      ("Revert ...; <test> goes red because <observable>").
#
# Exits 0 PASS with a one-line summary, 2 BLOCK with per-criterion
# gap list and remediation.
#
# Originating ticket: claude-configs-public#147 (parent #146).

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: evaluate-ticket.sh <ticket-ref>" >&2
    exit 64
fi

REF="$1"

# ---------------------------------------------------------------------
# Fetch ticket body + labels
# ---------------------------------------------------------------------

fetch_ticket() {
    local ref="$1"
    # Local file path
    if [[ -f "$ref" ]]; then
        TITLE=$(head -1 "$ref" | sed -E 's/^#+[[:space:]]*//')
        BODY=$(cat "$ref")
        LABELS=""
        return 0
    fi

    # GitHub: '#NNN' or 'owner/repo#NNN'
    if [[ "$ref" =~ ^(([^/#]+/[^/#]+)#)?([0-9]+)$ ]]; then
        local repo="${BASH_REMATCH[2]}"
        local num="${BASH_REMATCH[3]}"
        local args=("$num")
        [[ -n "$repo" ]] && args=("--repo" "$repo" "$num")
        local json
        json=$(gh issue view "${args[@]}" --json title,body,labels 2>/dev/null) || {
            echo "BLOCK: could not fetch ticket $ref via gh issue view" >&2
            exit 2
        }
        TITLE=$(echo "$json" | jq -r '.title')
        BODY=$(echo "$json" | jq -r '.body')
        LABELS=$(echo "$json" | jq -r '.labels[].name' | tr '\n' ' ')
        return 0
    fi

    # Linear: 'TEAM-NNN' (stubbed per session 260502 direction).
    if [[ "$ref" =~ ^[A-Z]+-[0-9]+$ ]]; then
        # TODO(linear): wire `linear-cli issue view "$ref" --json` when
        # the user starts using Linear. Per session direction: stubbed.
        # TODO(jira): same shape via `jira issue view "$ref" --json`.
        echo "BLOCK: external-tracker ref $ref — Linear/Jira fetchers are stubbed v1." >&2
        echo "       Enable in evaluate-ticket.sh fetch_ticket(); requires linear-cli or jira-cli." >&2
        exit 2
    fi

    echo "BLOCK: unrecognized ticket ref shape: $ref" >&2
    echo "       Expected: '#NNN', 'owner/repo#NNN', 'PROJ-NNN', or local file path." >&2
    exit 2
}

# ---------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------

EVIDENCE_TOKEN_RE='```|[/-][a-zA-Z0-9_-]+\.[a-zA-Z]{1,5}|git[[:space:]]+(diff|log|status|rev-parse|merge-base)|[0-9]+[[:space:]]+(lines?|files?|bytes?|insertions?|deletions?)|https?://'

GAPS=()

check_title_shape() {
    # Heuristic: title should have a verb. Block obvious noun-phrase titles
    # by requiring the first word to NOT be a common noun-only pattern
    # and the title to contain at least one verb-like token.
    if [[ "${#TITLE}" -lt 10 ]]; then
        GAPS+=("title is too short to be a complete sentence (<10 chars)")
        return
    fi
    # Reject pure noun-phrase patterns: starts with "The ", or single
    # capitalized noun followed by another noun, or single word.
    local word_count
    word_count=$(echo "$TITLE" | wc -w | tr -d ' ')
    if [[ "$word_count" -lt 3 ]]; then
        GAPS+=("title has $word_count words; need ≥3 (subject + verb + observable)")
        return
    fi
    # Heuristic verb token: at least one word that's not Title-Case (most
    # verbs are lowercase mid-title); or a common verb suffix (-s, -ed, -ing).
    # Conventional commit prefixes ("feat:", "fix:", "chore:") are accepted.
    if echo "$TITLE" | grep -qiE '^(feat|fix|chore|docs|test|refactor|perf|style|ci|build|revert)(\([^)]+\))?:'; then
        return  # conventional commit shape is fine
    fi
    if ! echo "$TITLE" | grep -qE '[a-z]+(s|ed|ing)\b|\b(add|fix|remove|update|enforce|allow|block|require|surface|guard|prevent|handle|return|emit|skip)\b'; then
        GAPS+=("title lacks a verb token (e.g., 'add', 'fix', 'enforce', '...es', '...ed', '...ing')")
    fi
}

check_sections() {
    local missing=()
    for section in "Context" "Goal" "Acceptance"; do
        if ! echo "$BODY" | grep -qiE "^#+[[:space:]]+${section}"; then
            missing+=("$section")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        GAPS+=("missing sections: $(IFS=, ; echo "${missing[*]}")")
    fi
}

check_evidence() {
    if ! echo "$BODY" | grep -qE "$EVIDENCE_TOKEN_RE"; then
        GAPS+=("no falsifiable evidence token in body (need at least one of: code fence, file path with extension, git command, stat/count, URL)")
    fi
}

check_think_link() {
    if echo "$BODY" | grep -qE 'plans/think-[^[:space:]]+\.md|^Design:[[:space:]]+\S|^#+[[:space:]]+(Design|Thinking)\b'; then
        return
    fi
    GAPS+=("no /think design-note reference (need 'plans/think-*.md' path, 'Design: <path>' line, or inline '## Design' section)")
}

check_assumptions_block() {
    if ! echo "$BODY" | grep -qE '^#+[[:space:]]+Assumptions'; then
        GAPS+=("no '## Assumptions' block")
    fi
}

check_falsification() {
    # Only applies to behavior-change tickets.
    if ! echo " $LABELS " | grep -qE ' (behavior-change|feature|bug) '; then
        return  # not behavior-change; skip
    fi
    # Look for falsification language.
    if ! echo "$BODY" | grep -qiE '(revert|restore|undo)[[:space:]]+the[[:space:]]+(implementation|change|fix)|goes red because|fails because|surfaces as|observable[[:space:]]+(failure|symptom)'; then
        GAPS+=("behavior-change ticket without falsification criterion (need writing-tests:1 shape: 'revert the implementation; <test> goes red because <observable>')")
    fi
}

# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------

fetch_ticket "$REF"

check_title_shape
check_sections
check_evidence
check_think_link
check_assumptions_block
check_falsification

if [[ ${#GAPS[@]} -eq 0 ]]; then
    echo "PASS: ticket $REF is fit for execution"
    echo "  title: \"$TITLE\""
    echo "  sections: Context, Goal, Acceptance — present"
    echo "  evidence: at least one falsifiable token in body"
    echo "  /think link: present"
    echo "  assumptions block: present"
    if echo " $LABELS " | grep -qE ' (behavior-change|feature|bug) '; then
        echo "  falsification: stated (behavior-change label)"
    fi
    exit 0
fi

echo "BLOCK: ticket $REF has gaps before it is fit for execution:" >&2
printf '  - %s\n' "${GAPS[@]}" >&2
echo "" >&2
echo "Remediation: edit ticket $REF body to add the missing sections, or" >&2
echo "             paste an exemption block in your self-review artifact" >&2
echo "             with the evidence chain (Reason / Evidence / Falsification)" >&2
echo "             per writing-rules:4." >&2
exit 2
