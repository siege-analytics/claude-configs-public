#!/bin/bash
# Hook: pre-push-self-review
# Type: git pre-push hook (NOT a Claude Code PreToolUse hook)
# Enforces: Self-Review trailers on commits being pushed
#
# Install: symlink or copy to .git/hooks/pre-push in target repos
#   ln -sf /path/to/claude-configs-public/hooks/git/pre-push-self-review.sh .git/hooks/pre-push
#
# This hook fires for ALL push sources: sub-agents, Craft Agent, Claude
# Code, humans, CI. It validates that every non-merge commit in the push
# range has Self-Review: and Self-Review-Source: trailers.
#
# Tier A requires inline review. Tier B/C require source evidence; local
# artifact paths are checked in each commit, including required sections.
# URL/ticket evidence pointers follow the accepted review-policy contract.
#
# Scope: commits being pushed, not all commits on the branch. Uses the
# git pre-push protocol: stdin receives lines of
#   <local ref> <local sha> <remote ref> <remote sha>
#
# Review commits new to this destination, excluding only its currently
# advertised branch heads. Other remotes and stale local tracking refs cannot
# hide an invalid interior commit. Already-published history is not re-reviewed
# during canonical promotion (#491). Missing objects/protocol errors fail closed.

set -uo pipefail

# Selected registration supplies all policy authority inputs as a host binding.
# The remaining body is the retained repository compatibility wrapper.
if [[ "${1:-}" == "--selected" && $# -ge 3 ]]; then
    shift
    SELECTED_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
    exec python3 -B "$SELECTED_ROOT/bin/native_git.py" pre-push -- "$@"
fi

BLOCKED=0
BLOCKED_COMMITS=""
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
RISK_SCRIPT="$HOOK_DIR/../../bin/review-risk.py"

incomplete() {
    echo "pre-push: incomplete range evidence: $1" >&2
    exit 2
}

EXCLUSIONS=()
if [[ "$#" -eq 2 ]]; then
    [[ -n "$1" && -n "$2" ]] || incomplete "missing push destination"
    REMOTE_HEADS=$(git ls-remote --heads -- "$2") || incomplete "cannot read destination heads"
    while read -r REMOTE_OID ADVERTISED_REF EXTRA; do
        [[ -n "$REMOTE_OID" ]] || continue
        [[ "$REMOTE_OID" =~ ^[0-9a-f]{40}$ && "$ADVERTISED_REF" == refs/heads/* && -z "$EXTRA" ]] \
            || incomplete "malformed destination advertisement"
        git cat-file -e "$REMOTE_OID^{commit}" 2>/dev/null \
            || incomplete "destination commit $REMOTE_OID is unavailable; fetch this destination and retry"
        EXCLUSIONS+=("^$REMOTE_OID")
    done <<< "$REMOTE_HEADS"
elif [[ "$#" -ne 0 ]]; then
    incomplete "expected native Git remote name and location"
fi
# A direct no-argument fixture has no remote baseline and checks the full graph.

validate_committed_artifact() {
    local commit="$1" value="$2" tier="$3" content section
    [[ "$value" =~ ^https?:// || "$value" =~ ^#[0-9]+$ ]] && return 0
    content=$(git show "$commit:${value#./}" 2>/dev/null) || return 1
    if [[ "$tier" == "B" ]]; then
        for section in "## Assumptions" "## Test plan"; do grep -qE "^${section}[[:space:]]*$" <<<"$content" || return 1; done
    else
        if grep -Eq '^## Peer review[[:space:]]*$' <<<"$content" && grep -Eq '^## Lead review[[:space:]]*$' <<<"$content" && grep -Eq '^## Quantified claims[[:space:]]*$' <<<"$content"; then
            for section in "## Assumptions" "## Peer review" "## Lead review" "## Quantified claims"; do grep -qE "^${section}[[:space:]]*$" <<<"$content" || return 1; done
        else
            for section in "## Assumptions" "## Test plan" "## Findings" "## Independent review"; do grep -qE "^${section}[[:space:]]*$" <<<"$content" || return 1; done
        fi
    fi
    local findings unresolved findings_heading_re='^[ ]?[ ]?[ ]?##[[:blank:]]+findings([^[:alnum:]_]|$)'
    findings=$(awk -v heading="$findings_heading_re" '{
        line=$0
        sub(/\r$/, "", line)
        sub(/^[ ]?[ ]?[ ]?/, "", line)
        first=substr(line,1,1)
        if (first == "`" || first == "~") {
            count=0
            while (substr(line,count+1,1) == first) count++
            rest=substr(line,count+1)
            if (!fence && count >= 3 && (first == "~" || rest !~ /`/)) {fence=first; width=count; next}
            if (fence == first && count >= width && rest ~ /^[[:blank:]]*$/) {fence=""; next}
        }
        if (fence) next
        if (line ~ /^##[[:blank:]]+/) {active=(tolower($0) ~ heading); next}
        if (active) print
    }' <<<"$content")
    unresolved=$(
        printf '%s\n' "$findings" | awk '/^[ ]?[ ]?[ ]?\|/ {
            delete cells
            count=1
            for (i=1; i<=length($0); i++) {
                char=substr($0, i, 1)
                if (char == "\\" && i<length($0)) {
                    cells[count]=cells[count] char substr($0, ++i, 1)
                } else if (char == "|") {
                    count++
                } else {
                    cells[count]=cells[count] char
                }
            }
            if (cells[3] ~ /^[[:space:]]*P1[[:space:]]*$/) {
                resolution=cells[5]
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", resolution)
                if ((count != 5 && count != 6) ||
                    (count == 6 && cells[6] !~ /^[[:space:]]*$/) ||
                    tolower(resolution) != "fixed") print
            }
        }'
        printf '%s\n' "$findings" | awk '
            tolower($0) ~ /^[[:space:]]*([-*][[:space:]]+)?p1[[:space:]]*:/ {
                count=split($0, fields, ";")
                resolutions=0
                fixed=0
                for (i=1; i<=count; i++) {
                    value=fields[i]
                    sub(/^[[:space:]]+/, "", value)
                    if (tolower(value) ~ /^resolution[[:space:]]*:/) {
                        resolutions++
                        sub(/^[^:]*:/, "", value)
                        gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
                        if (tolower(value) == "fixed") fixed++
                    }
                }
                if (resolutions != 1 || fixed != 1) print
            }'
    )
    [[ -z "$unresolved" ]]
}

while read -r LOCAL_REF LOCAL_SHA REMOTE_REF REMOTE_SHA EXTRA || [[ -n "$LOCAL_REF$LOCAL_SHA$REMOTE_REF$REMOTE_SHA$EXTRA" ]]; do
    [[ -n "$LOCAL_REF" && -n "$REMOTE_REF" && -z "$EXTRA" \
       && "$LOCAL_SHA" =~ ^[0-9a-f]{40}$ && "$REMOTE_SHA" =~ ^[0-9a-f]{40}$ ]] \
        || incomplete "malformed push update line"
    # Skip branch deletions
    if [[ "$LOCAL_SHA" == "0000000000000000000000000000000000000000" ]]; then
        continue
    fi

    LOCAL_COMMIT=$(git rev-parse --verify "$LOCAL_SHA^{commit}" 2>/dev/null) \
        || incomplete "local update is not an available commit"
    RANGE_EXCLUSIONS=("$LOCAL_COMMIT" ${EXCLUSIONS[@]+"${EXCLUSIONS[@]}"})
    if [[ "$REMOTE_SHA" != "0000000000000000000000000000000000000000" ]]; then
        REMOTE_COMMIT=$(git rev-parse --verify "$REMOTE_SHA^{commit}" 2>/dev/null) \
            || incomplete "remote update base is not an available commit"
        RANGE_EXCLUSIONS+=("^$REMOTE_COMMIT")
    fi
    COMMITS=$(git rev-list --reverse "${RANGE_EXCLUSIONS[@]}" 2>/dev/null) \
        || incomplete "cannot enumerate the exact push range"

    # Iterate commits in push range
    for COMMIT in $COMMITS; do
        # Merge commits are explicitly outside this policy; all non-merge
        # commits, including revert/fixup/squash subjects, are validated.
        PARENT_COUNT=$(git cat-file -p "$COMMIT" | grep -c '^parent ' || true)
        if [[ "$PARENT_COUNT" -gt 1 ]]; then continue; fi

        MSG=$(git log -1 --format='%B' "$COMMIT")
        TRAILERS=$(printf '%s' "$MSG" | git interpret-trailers --parse 2>/dev/null || true)
        SHORT=$(git log -1 --format='%h %s' "$COMMIT")
        TIER_COUNT=$(echo "$TRAILERS" | grep -ci '^Review-Tier:[[:space:]]*[ABC][[:space:]]*$')
        TIER=$(echo "$TRAILERS" | grep -i '^Review-Tier:' | sed -E 's/^Review-Tier:[[:space:]]+//' | tr '[:lower:]' '[:upper:]')
        SELF_COUNT=$(echo "$TRAILERS" | grep -cE '^Self-Review:[[:space:]]+\S')
        SOURCE_COUNT=$(echo "$TRAILERS" | grep -cE '^Self-Review-Source:[[:space:]]+\S')
        HOSTILE_COUNT=$(echo "$TRAILERS" | grep -cE '^Hostile-Review:[[:space:]]+\S')
        SOURCE_VALUE=$(echo "$TRAILERS" | grep -E '^Self-Review-Source:' | sed -E 's/^Self-Review-Source:[[:space:]]+//')
        HOSTILE_VALUE=$(echo "$TRAILERS" | grep -E '^Hostile-Review:' | sed -E 's/^Hostile-Review:[[:space:]]+//')
        # Collect every violation for this commit in one report (#1168). An
        # absent or downgraded tier is replaced by the computed one so the
        # remaining trailer requirements can be listed; a classifier failure
        # still stops evaluation of this commit.
        REASONS=()
        PROTECTED=false
        git diff-tree --root --no-renames --name-only -r "$COMMIT" | grep -Eq '^(bin/review-risk\.py|catalog/review-risk-policy\.json|\.githooks/commit-msg|hooks/git/(self-review|pre-push-self-review)\.sh)$' && PROTECTED=true
        DECLARED=""; [[ "$TIER_COUNT" -eq 1 && "$TIER" =~ ^[ABC]$ ]] && DECLARED="$TIER"
        COMPUTED=""
        if [[ -f "$RISK_SCRIPT" ]]; then
            RISK_RESULT=$(python3 "$RISK_SCRIPT" --repo "$REPO_ROOT" --commit "$COMMIT" ${DECLARED:+--declared "$DECLARED"} 2>/dev/null) && RISK_OK=true || RISK_OK=false
            COMPUTED=$(printf '%s' "$RISK_RESULT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("computed_tier", ""))' 2>/dev/null || true)
        fi
        if [[ ! "$COMPUTED" =~ ^[ABC]$ ]]; then
            if [[ ! -f "$RISK_SCRIPT" ]]; then
                REASONS+=("requires exactly one valid Review-Tier trailer (review risk classifier unavailable)")
            elif [[ -z "$DECLARED" ]]; then
                REASONS+=("requires exactly one valid Review-Tier trailer")
            else
                REASONS+=("declared review tier downgrades computed risk (or the review classifier failed)")
            fi
        else
            REQUIRED="$COMPUTED"; [[ "$PROTECTED" == "true" ]] && REQUIRED="C"
            if [[ -z "$DECLARED" ]]; then
                REASONS+=("Review-Tier: $REQUIRED  (requires exactly one valid Review-Tier trailer)")
                TIER="$REQUIRED"
            elif [[ "$DECLARED" != "C" && "$PROTECTED" == "true" ]]; then
                REASONS+=("Review-Tier: C  (review-policy bootstrap files independently require Tier C)")
                TIER="C"
            elif [[ "$RISK_OK" != "true" ]]; then
                REASONS+=("Review-Tier: $REQUIRED  (declared review tier downgrades computed risk)")
                TIER="$REQUIRED"
            fi
            [[ "$SELF_COUNT" -eq 1 ]] || REASONS+=("Self-Review: <one-line summary of the review pass>  (requires exactly one non-empty Self-Review trailer)")
            [[ "$MSG" == *'[no-review]'* && "$TIER" != "A" ]] && REASONS+=("[no-review] is allowed only for validated Tier A")
            printf '%s' "$MSG" | python3 -B "$HOOK_DIR/../lib/git_command.py" --cwd "$REPO_ROOT" --policy ticket-message >/dev/null 2>&1 || REASONS+=("task reference: #NNN, project ticket/URL, or [task: authorized request]; bare [no-ticket] is invalid")
            if [[ "$TIER" != "A" && "$SOURCE_COUNT" -ne 1 ]]; then
                REASONS+=("Self-Review-Source: <path or URL to the self-review artifact>  (Tier $TIER requires exactly one Self-Review-Source)")
            elif [[ "$TIER" != "A" ]] && ! validate_committed_artifact "$COMMIT" "$SOURCE_VALUE" "$TIER"; then
                REASONS+=("Self-Review-Source lacks required committed Tier $TIER content")
            fi
            if [[ "$TIER" == "C" && "$HOSTILE_COUNT" -ne 1 ]]; then
                REASONS+=("Hostile-Review: <URL, #ticket, or committed file with the independent hostile review>  (Tier C requires exactly one Hostile-Review)")
            elif [[ "$TIER" == "C" && ! "$HOSTILE_VALUE" =~ ^(https?://|#[0-9]+$) ]] && { [[ ! "$(git --literal-pathspecs ls-tree --full-tree "$COMMIT" -- "${HOSTILE_VALUE#./}" 2>/dev/null | awk '{print $1}')" =~ ^100(644|755)$ ]] || [[ "$(git cat-file -t "$COMMIT:${HOSTILE_VALUE#./}" 2>/dev/null)" != blob ]] || [[ $(git cat-file -s "$COMMIT:${HOSTILE_VALUE#./}" 2>/dev/null || echo 0) -eq 0 ]]; }; then
                REASONS+=("Hostile-Review is not a URL, ticket, or non-empty file in the commit")
            fi

        fi
        if [[ ${#REASONS[@]} -gt 0 ]]; then
            BLOCKED=1
            BLOCKED_COMMITS="${BLOCKED_COMMITS}\n  ${SHORT}:"
            for REASON in "${REASONS[@]}"; do
                BLOCKED_COMMITS="${BLOCKED_COMMITS}\n    - ${REASON}"
            done
        fi
    done
done

if [[ "$BLOCKED" -eq 1 ]]; then
    cat >&2 <<HOOKEOF

BLOCKED by pre-push-self-review hook.

The following commits violate proportional review policy:
$(echo -e "$BLOCKED_COMMITS")

Every non-merge commit must include Review-Tier: A|B|C and Self-Review:.
Tier B/C also require Self-Review-Source:. Tier C requires actual independent
Hostile-Review: evidence. The compact record contains actual source facts,
checks/results and findings; compatible historical review records remain valid.
The declared tier may escalate but cannot be lower than the machine-computed tier.

To add trailers, amend the commit:
  git commit --amend  (then add trailers to the message)

See skills/self-review/SKILL.md for the full artifact format.

HOOKEOF
    exit 1
fi

exit 0
