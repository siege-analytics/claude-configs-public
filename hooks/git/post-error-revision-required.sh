#!/bin/bash
# Hook: post-error-revision-required
# Enforces: writing-rules:6 (claude-configs-public#167, #168) + the
#           post-error-revision skill.
# Trigger:  PreToolUse on Bash(git commit *), Bash(git revert *),
#           Bash(gh pr create *).
#
# Fires when the command is a revert OR a regression-fix commit OR a
# revert-titled PR creation. Requires the message body / PR body to
# carry BOTH:
#   - Refs: <ticket>   (the originating ticket whose Assumption was
#                       contradicted)
#   - Post-error-revision: <link>  (link to the ticket's
#                                   `## Post-error revision` block)
#
# When the Post-error-revision: trailer's value resolves to a local
# file path, the hook additionally delegates to
# scripts/discipline/check-post-error-revision.sh for block-structure
# validation. URL values are not fetched (network-free hook).
#
# Override: [no-post-error-revision: <Reason: ... ; Evidence: ... ;
#           Falsification: ...>] per writing-rules:4. Bare overrides
# are blocked.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Detect whether this command is in scope.
IS_REVERT=0
IS_REGRESSION_FIX=0
IS_REVERT_PR=0

if echo "$COMMAND" | grep -qE '^git[[:space:]]+revert\b'; then
    IS_REVERT=1
fi

# Regression-fix commit: message contains "fix(...): regression" OR the
# word "revert" in a `git commit -m` body (auto-generated revert
# messages start with "Revert ").
if echo "$COMMAND" | grep -qE '^git[[:space:]]+commit\b'; then
    if echo "$COMMAND" | grep -qiE 'fix\([^)]+\):[[:space:]]+regression|Revert[[:space:]]+"|: revert '; then
        IS_REGRESSION_FIX=1
    fi
fi

# PR-create with revert / regression title.
if echo "$COMMAND" | grep -qE '^gh[[:space:]]+pr[[:space:]]+create\b'; then
    if echo "$COMMAND" | grep -qiE -- '--title[[:space:]]+["'\''][^"'\'']*(Revert|regression)'; then
        IS_REVERT_PR=1
    fi
fi

if [[ $IS_REVERT -eq 0 && $IS_REGRESSION_FIX -eq 0 && $IS_REVERT_PR -eq 0 ]]; then
    exit 0
fi

# In scope. Check for the evidence-bearing override marker first.
if echo "$COMMAND" | grep -qE '\[no-post-error-revision:[[:space:]]+Reason:[^]]+;[[:space:]]*Evidence:[^]]+;[[:space:]]*Falsification:[^]]+\]'; then
    exit 0
fi

# Bare override -> blocked per writing-rules:4.
if echo "$COMMAND" | grep -qE '\[no-post-error-revision(\]|:[[:space:]]*\])'; then
    cat >&2 <<HOOKEOF
BLOCKED: '[no-post-error-revision]' override now requires evidence.

Per writing-rules:4, every "this doesn't apply" claim requires the
evidence chain. Replace bare '[no-post-error-revision]' with:

  [no-post-error-revision: Reason: <falsifiable why>; Evidence: <obs>;
                           Falsification: <observable that would prove
                                           this wrong>]

If the override doesn't fit that shape, this commit is in scope.
HOOKEOF
    exit 2
fi

# Both trailers required.
HAS_REFS=0
HAS_PER=0
if echo "$COMMAND" | grep -qE 'Refs:[[:space:]]+'; then HAS_REFS=1; fi
if echo "$COMMAND" | grep -qE 'Post-error-revision:[[:space:]]+\S'; then HAS_PER=1; fi

if [[ $HAS_REFS -eq 0 || $HAS_PER -eq 0 ]]; then
    cat >&2 <<HOOKEOF
BLOCKED: revert / regression-fix commits require BOTH trailers.

Per writing-rules:6 (claude-configs-public#167, #168), any commit that
reverts a change or fixes a regression must reference the originating
ticket AND the Post-error revision block on it.

Required trailers in the commit / PR body:
  Refs: <ticket-reference> Post-error revision dated YYYY-MM-DD
  Post-error-revision: <link to the ticket's '## Post-error revision'
                        block, OR a local artifact path>

Accepted ticket reference formats:
  GitHub/GitLab:  repo#42, owner/repo#42, #42
  Jira/Linear:    PROJ-123, ELE-42
  URL:            https://jira.example.com/browse/PROJ-123

If the originating ticket has no Post-error revision block yet, STOP
and follow skills/post-error-revision/SKILL.md:
  1. Identify the originating ticket (walk failure -> commit -> PR -> ticket)
  2. Append the five-field block to that ticket
  3. Preserve-and-annotate the wrong Assumption alongside the revised one
  4. THEN re-run this command with the trailer pair

Found: Refs: $HAS_REFS, Post-error-revision: $HAS_PER (both must be 1).
HOOKEOF
    exit 2
fi

# If the Post-error-revision: trailer points at a local file, validate
# its block structure via the canonical script.
PER_VALUE=$(echo "$COMMAND" | grep -oE 'Post-error-revision:[[:space:]]+\S+' | head -1 | sed -E 's/^Post-error-revision:[[:space:]]+//')

CHECK_SCRIPT="$(dirname "$0")/../../scripts/discipline/check-post-error-revision.sh"

if [[ -f "$PER_VALUE" && -x "$CHECK_SCRIPT" ]]; then
    if ! "$CHECK_SCRIPT" "$PER_VALUE" 1>&2; then
        cat >&2 <<HOOKEOF

The Post-error-revision: trailer points at a local file but the block
inside it failed validation. Fix the block first, then re-run.
HOOKEOF
        exit 2
    fi
fi

# If the value is a GitHub issue URL, verify the ticket has a post-error
# revision comment. Best-effort: warns if gh is unavailable or API fails.
if echo "$PER_VALUE" | grep -qE 'github\.com/.+/issues/[0-9]+'; then
    REPO_SLUG=$(echo "$PER_VALUE" | grep -oE 'github\.com/[^/]+/[^/]+' | sed 's|github.com/||')
    ISSUE_NUM=$(echo "$PER_VALUE" | grep -oE 'issues/[0-9]+' | grep -oE '[0-9]+')
    if [ -n "$REPO_SLUG" ] && [ -n "$ISSUE_NUM" ] && command -v gh >/dev/null 2>&1; then
        HAS_PER_COMMENT=$(gh api "repos/$REPO_SLUG/issues/$ISSUE_NUM/comments" \
            --jq '[.[] | select(.body | test("## Post-error revision"; "i"))] | length' \
            2>/dev/null || echo "error")
        if [ "$HAS_PER_COMMENT" = "0" ]; then
            cat >&2 <<HOOKEOF
WARNING: Post-error-revision: points at $REPO_SLUG#$ISSUE_NUM but no
comment with "## Post-error revision" was found on the ticket.

The five-field block should be posted to the originating ticket BEFORE
this commit. Either post it now, or verify the heading is different.
HOOKEOF
        elif [ "$HAS_PER_COMMENT" = "error" ]; then
            cat >&2 <<HOOKEOF
WARNING: Could not verify Post-error-revision ticket via GitHub API.
Manual verification recommended: check $PER_VALUE for a
"## Post-error revision" section.
HOOKEOF
        fi
    fi
fi

exit 0
