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
# Unlike self-review.sh (PreToolUse), this hook does NOT validate artifact
# content — only trailer presence. Artifact structure validation remains
# in self-review.sh for Claude Code sessions.
#
# Scope: commits being pushed, not all commits on the branch. Uses the
# git pre-push protocol: stdin receives lines of
#   <local ref> <local sha> <remote ref> <remote sha>
#
# Rebase handling: after a rebase, the old remote SHA is no longer an
# ancestor of the local SHA. The hook detects this and falls back to
# --not --remotes (same as new-branch logic) so only branch-unique
# commits are checked, not the upstream commits that got rebased in.

set -uo pipefail

BLOCKED=0
BLOCKED_COMMITS=""
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
RISK_SCRIPT="$HOOK_DIR/../../bin/review-risk.py"

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

while read -r LOCAL_REF LOCAL_SHA REMOTE_REF REMOTE_SHA; do
    # Skip branch deletions
    if [[ "$LOCAL_SHA" == "0000000000000000000000000000000000000000" ]]; then
        continue
    fi

    # Determine commit range
    if [[ "$REMOTE_SHA" == "0000000000000000000000000000000000000000" ]]; then
        # New branch: check all commits not on any remote branch
        RANGE="$LOCAL_SHA --not --remotes"
    elif ! git merge-base --is-ancestor "$REMOTE_SHA" "$LOCAL_SHA" 2>/dev/null; then
        # Force push (rebase): old remote tip is no longer an ancestor.
        # Fall back to --not --remotes so we only check branch-unique
        # commits, not the upstream commits that got rebased in.
        RANGE="$LOCAL_SHA --not --remotes"
    else
        # Only check commits not yet on ANY remote branch. This avoids
        # re-validating commits already pushed to develop when they arrive
        # on main via promotion merge. See #491.
        RANGE="$LOCAL_SHA --not --remotes"
    fi

    # Iterate commits in push range
    for COMMIT in $(git rev-list $RANGE 2>/dev/null); do
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
