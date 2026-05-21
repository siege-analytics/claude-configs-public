#!/bin/bash
# check-self-review.sh — canonical self-review artifact check
#
# Usage: check-self-review.sh <commit-sha> <artifact-path>
#
# Verifies that:
#   1. The artifact file exists at <artifact-path>.
#   2. The artifact has the three required sections:
#      ## Assumptions / ## Peer review / ## Lead review
#   3. The artifact has a non-empty 'Goal source:' line.
#   4. The artifact's '## Assumptions' section names ≥1 role.
#   5. The artifact's '## Peer review' section cites ≥1 shelf
#      (writing-{code,tests,claims,prose,releases,rules}:N).
#   6. (v2 / claude-configs-public#146) When the artifact is in a git
#      repo, the artifact's first-added commit is an ancestor of
#      <commit-sha>. Closes the retroactive-trailer loophole.
#
# Exits 0 on PASS, 2 on BLOCK with a specific error message.
#
# Originating ticket: claude-configs-public#147 (parent #146).

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: check-self-review.sh <commit-sha> <artifact-path>" >&2
    exit 64
fi

COMMIT_SHA="$1"
ARTIFACT_PATH="$2"

if [[ ! -f "$ARTIFACT_PATH" ]]; then
    echo "BLOCK: artifact $ARTIFACT_PATH does not exist" >&2
    exit 2
fi

# Required section headers.
MISSING_SECTIONS=()
for section in "## Assumptions" "## Peer review" "## Lead review"; do
    if ! grep -qF "$section" "$ARTIFACT_PATH"; then
        MISSING_SECTIONS+=("$section")
    fi
done
if [[ ${#MISSING_SECTIONS[@]} -gt 0 ]]; then
    echo "BLOCK: $ARTIFACT_PATH missing sections:" >&2
    printf '  - %s\n' "${MISSING_SECTIONS[@]}" >&2
    exit 2
fi

# Non-empty Goal source.
if ! grep -qE '^Goal source:[[:space:]]+\S' "$ARTIFACT_PATH"; then
    echo "BLOCK: $ARTIFACT_PATH missing or empty 'Goal source:' line" >&2
    exit 2
fi

# Working as: line with at least one canonical role.
ROLE_RE='(software engineer|tech lead|data engineer|data analyst|geospatial)'
if ! grep -qiE "^Working as:[[:space:]]+.*$ROLE_RE" "$ARTIFACT_PATH"; then
    echo "BLOCK: $ARTIFACT_PATH 'Working as:' does not name a canonical role" >&2
    echo "       (software engineer / tech lead / data engineer / data analyst / geospatial)" >&2
    exit 2
fi

# Peer review section cites at least one shelf.
SHELF_RE='writing-(code|tests|claims|prose|releases|rules):'
PEER_BLOCK=$(awk '/^## Peer review/{flag=1; next} /^## /{flag=0} flag' "$ARTIFACT_PATH")
if ! echo "$PEER_BLOCK" | grep -qE "$SHELF_RE"; then
    echo "BLOCK: $ARTIFACT_PATH '## Peer review' section does not cite a shelf" >&2
    echo "       (expected: writing-code:N, writing-tests:N, etc.)" >&2
    exit 2
fi

# v2: artifact-predates-work check.
ARTIFACT_DIR=$(dirname "$ARTIFACT_PATH")
if git -C "$ARTIFACT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    ARTIFACT_REPO=$(git -C "$ARTIFACT_DIR" rev-parse --show-toplevel)
    ARTIFACT_REL="${ARTIFACT_PATH#$ARTIFACT_REPO/}"
    FIRST_ADDED=$(git -C "$ARTIFACT_REPO" log --diff-filter=A --follow --format=%H -- "$ARTIFACT_REL" 2>/dev/null | tail -1)

    if [[ -n "$FIRST_ADDED" ]]; then
        if ! git -C "$ARTIFACT_REPO" merge-base --is-ancestor "$FIRST_ADDED" "$COMMIT_SHA" 2>/dev/null; then
            cat >&2 <<EOF
BLOCK: $ARTIFACT_PATH was first added in $FIRST_ADDED, which is NOT
an ancestor of work commit $COMMIT_SHA.

The artifact is retroactive — written AFTER the work it claims to
review. Closes the loophole per claude-configs-public#146:

  - Write the self-review artifact BEFORE doing the work; commit
    it first; then proceed with the work.
  - If the work commit predates the artifact's existence, rebase
    or amend so the work commit follows the artifact commit.
EOF
            exit 2
        fi
    fi
    # If FIRST_ADDED is empty, the artifact isn't tracked by git in
    # this repo (e.g., session-scoped plans/). The check doesn't apply;
    # mtime sanity (handled by caller if desired) is the fallback.
fi

exit 0
