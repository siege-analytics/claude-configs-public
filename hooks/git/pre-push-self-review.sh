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
        # Skip merge commits (2+ parents)
        PARENT_COUNT=$(git cat-file -p "$COMMIT" | grep -c '^parent ' || true)
        if [[ "$PARENT_COUNT" -gt 1 ]]; then
            continue
        fi

        # Skip fixup/squash commits (will be folded)
        SUBJECT=$(git log -1 --format='%s' "$COMMIT")
        if [[ "$SUBJECT" == fixup!* ]] || [[ "$SUBJECT" == squash!* ]]; then
            continue
        fi

        # Check for Self-Review trailer
        MSG=$(git log -1 --format='%B' "$COMMIT")
        if ! echo "$MSG" | grep -qE '^Self-Review:[[:space:]]+\S'; then
            BLOCKED=1
            SHORT=$(git log -1 --format='%h %s' "$COMMIT")
            BLOCKED_COMMITS="${BLOCKED_COMMITS}\n  ${SHORT}"
        fi
    done
done

if [[ "$BLOCKED" -eq 1 ]]; then
    cat >&2 <<HOOKEOF

BLOCKED by pre-push-self-review hook.

The following commits are missing Self-Review: trailers:
$(echo -e "$BLOCKED_COMMITS")

Every non-merge commit must include trailers:
  Self-Review: <one-line summary>
  Self-Review-Source: <path or ticket pointing at review artifact>

To add trailers, amend the commit:
  git commit --amend  (then add trailers to the message)

To bypass (emergencies only):
  git push --no-verify

See skills/self-review/SKILL.md for the full artifact format.

HOOKEOF
    exit 1
fi

exit 0
