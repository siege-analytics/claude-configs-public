#!/bin/bash
# Hook: pre-push-self-review
# Type: git pre-push hook (NOT a Claude Code PreToolUse hook)
# Enforces: Self-Review trailers on commits being pushed
#
# Install: symlink or copy to .git/hooks/pre-push in target repos
#   ln -sf /path/to/claude-configs-public/hooks/git/pre-push-self-review.sh .git/hooks/pre-push
#
# Bypass: git push --no-verify (standard git escape hatch)
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
        for section in "## Assumptions" "## Test plan"; do grep -qF "$section" <<<"$content" || return 1; done
    else
        for section in "## Assumptions" "## Peer review" "## Lead review" "## Quantified claims"; do grep -qF "$section" <<<"$content" || return 1; done
        grep -qE '^Pre-mortem-artifact:[[:space:]]+\S' <<<"$content" || return 1
        grep -qE '^Hostile-review-artifact:[[:space:]]+\S' <<<"$content" || return 1
    fi
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
        REASON=""
        if [[ ! -f "$RISK_SCRIPT" || "$TIER_COUNT" -ne 1 || ! "$TIER" =~ ^[ABC]$ ]]; then
            REASON="requires exactly one valid Review-Tier trailer"
        elif [[ "$TIER" != "C" ]] && git diff-tree --root --no-renames --name-only -r "$COMMIT" | grep -Eq '^(bin/review-risk\.py|catalog/review-risk-policy\.json|\.githooks/commit-msg|hooks/git/(self-review|pre-push-self-review)\.sh)$'; then
            REASON="review-policy bootstrap files independently require Tier C"
        elif ! python3 "$RISK_SCRIPT" --repo "$REPO_ROOT" --commit "$COMMIT" --declared "$TIER" >/dev/null 2>&1; then
            REASON="declared review tier downgrades computed risk"
        elif [[ "$SELF_COUNT" -ne 1 ]]; then
            REASON="requires exactly one non-empty Self-Review trailer"
        elif [[ "$MSG" == *'[no-review]'* && "$TIER" != "A" ]]; then
            REASON="[no-review] is allowed only for validated Tier A"
        elif ! echo "$MSG" | grep -qE '(#[0-9]+|\[no-ticket\])'; then
            REASON="missing ticket reference or [no-ticket]"
        elif [[ "$TIER" != "A" && "$SOURCE_COUNT" -ne 1 ]]; then
            REASON="Tier $TIER requires exactly one Self-Review-Source"
        elif [[ "$TIER" != "A" ]] && ! validate_committed_artifact "$COMMIT" "$SOURCE_VALUE" "$TIER"; then
            REASON="Self-Review-Source lacks required committed Tier $TIER content"
        elif [[ "$TIER" == "C" && "$HOSTILE_COUNT" -ne 1 ]]; then
            REASON="Tier C requires exactly one Hostile-Review"
        elif [[ "$TIER" == "C" && ! "$HOSTILE_VALUE" =~ ^(https?://|#[0-9]+$) ]] && { ! git cat-file -e "$COMMIT:${HOSTILE_VALUE#./}" 2>/dev/null || [[ $(git cat-file -s "$COMMIT:${HOSTILE_VALUE#./}" 2>/dev/null || echo 0) -eq 0 ]]; }; then
            REASON="Hostile-Review is not a URL, ticket, or non-empty file in the commit"
        elif [[ "$TIER" == "C" ]]; then
            for EVIDENCE in Negative-Tests Full-Suite Canary-Rollback; do
                [[ $(echo "$TRAILERS" | grep -cE "^${EVIDENCE}:[[:space:]]+\\S") -eq 1 ]] || { REASON="Tier C requires exactly one $EVIDENCE trailer"; break; }
            done
        fi
        if [[ -n "$REASON" ]]; then
            BLOCKED=1
            BLOCKED_COMMITS="${BLOCKED_COMMITS}\n  ${SHORT} — ${REASON}"
        fi
    done
done

if [[ "$BLOCKED" -eq 1 ]]; then
    cat >&2 <<HOOKEOF

BLOCKED by pre-push-self-review hook.

The following commits violate proportional review policy:
$(echo -e "$BLOCKED_COMMITS")

Every non-merge commit must include Review-Tier: A|B|C and Self-Review:.
Tier B/C also require Self-Review-Source:. Tier C requires Hostile-Review:.
The declared tier may escalate but cannot be lower than the machine-computed tier.

To add trailers, amend the commit:
  git commit --amend  (then add trailers to the message)

To bypass (emergencies only):
  git push --no-verify

See skills/self-review/SKILL.md for the full artifact format.

HOOKEOF
    exit 1
fi

exit 0
