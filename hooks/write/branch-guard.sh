#!/usr/bin/env bash
# Hook: write/branch-guard
# Enforces: git-workflow/develop-guard at WRITE time (not just commit time).
# Trigger: PreToolUse on Write
#
# Closes the highest-volume git-perimeter gap: Write tool calls to files in
# a git repo on develop/main/master/staging happen silently today; the
# discipline only fires when the agent eventually tries to commit. This hook
# moves the gate upstream to the write itself.
#
# Logic:
#   - Resolve file_path to absolute (anchored against cwd if relative).
#   - Walk up looking for .git. If not in a git repo: ALLOW.
#   - Read current branch. If in {main, master, develop, staging}: BLOCK.
#   - If detached HEAD: BLOCK.
#   - Otherwise: ALLOW (the push-time hooks will gate the eventual commit).
#
# Carve-outs (silent ALLOW):
#   - File path under any session/plans/ or session/data/ directory
#     (Craft Agent session-managed sandbox).
#   - File path under ~/.claude/ or ~/.craft-agent/ (agent-managed config).
#   - File path under /tmp/ (workspace-scratch).
#
# Composes with hooks/write/write-guard.sh (path-pattern-based) -- both must
# allow for the write to proceed. Defense-in-depth.

set -uo pipefail
source "$(f="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/hook-path.sh"; [[ -f "$f" ]] && printf '%s' "$f" || printf /dev/null)"

INPUT=$(cat)

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
FILE_PATH=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.file_path tool_input.path tool_input.notebook_path 2>/dev/null || echo "")
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || echo "")

[[ -z "$FILE_PATH" ]] && exit 0

# Resolve to absolute. Relative path -> anchor against cwd; if cwd is empty,
# bail with ALLOW (the host should always provide cwd, but we don't want
# to false-block on a malformed input).
case "$FILE_PATH" in
    /*) ABS_PATH="$FILE_PATH" ;;
    *)  [[ -z "$CWD" ]] && exit 0; ABS_PATH="$CWD/$FILE_PATH" ;;
esac

# Carve-out (silent ALLOW): session-managed and agent-config paths.
# /tmp/ is NOT carved out here -- a /tmp/<repo-name>/ path that's actually
# inside a git repo (e.g. /tmp/sw-work-target/) must be subject to the
# branch check. True /tmp scratch files fall through to the git-walk and
# are ALLOWed there (no .git found -> exit 0).
case "$ABS_PATH" in
    */.craft-agent/workspaces/*/sessions/*/plans/*) exit 0 ;;
    */.craft-agent/workspaces/*/sessions/*/data/*) exit 0 ;;
    */.claude/*) exit 0 ;;
    */.craft-agent/*) exit 0 ;;
esac

# Find git repo root. Walk up from the file's parent directory.
search_dir=$(dirname "$ABS_PATH")
repo_root=""
while [[ "$search_dir" != "/" && -n "$search_dir" ]]; do
    if [[ -d "$search_dir/.git" ]] || [[ -f "$search_dir/.git" ]]; then
        repo_root="$search_dir"
        break
    fi
    search_dir=$(dirname "$search_dir")
done

# Not in a git repo: ALLOW (out-of-scope for this hook).
[[ -z "$repo_root" ]] && exit 0

# Read current branch. git -C handles the repo location.
BRANCH=$(git -C "$repo_root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

# Detached HEAD shows as "HEAD".
if [[ "$BRANCH" == "HEAD" ]]; then
    cat >&2 <<HOOKEOF
BLOCKED: Write to $FILE_PATH but the repo at $repo_root is in detached HEAD.

For normal development, prepare a separate task worktree before writing:
  python3 "$HOOK_DIR/../../bin/prepare-task-branch.py" --repo "$repo_root" --branch fix/ticket_description --worktree /absolute/unique-task-worktree

Refresh when available; the helper reports cached develop honestly offline and
bootstraps only after verified remote absence. Continue in the returned worktree.
For an explicitly authorized release/backport, retain the exact approved source
through the existing own-Task branch_source_authorization in [skill:develop-guard],
not this normal development helper.

See git-workflow/branch/SKILL.md for branch naming.
HOOKEOF
    exit 2
fi

# Protected branches: develop/main/master/staging.
case "$BRANCH" in
    main|master|develop|staging)
        cat >&2 <<HOOKEOF
BLOCKED: Write to $FILE_PATH on protected branch '$BRANCH'.

Direct writes to $BRANCH bypass the git-workflow discipline (branch-guard,
ticket-required, self-review, survey-context). Prepare a normal task worktree:

  python3 "$HOOK_DIR/../../bin/prepare-task-branch.py" --repo "$repo_root" --branch fix/ticket_description --worktree /absolute/unique-task-worktree

The helper refreshes when available and reports cached develop honestly offline.
Continue in the returned worktree. Explicitly authorized release/backport work
retains its exact approved source through the existing own-Task
branch_source_authorization route in [skill:develop-guard].

If this is a documentation-only fix that genuinely needs to land on $BRANCH,
use a feature branch + PR anyway -- the PR-time hooks (self-review,
survey-context) catch missing trailers and doc-drift.

Missing develop is bootstrapped only after successful remote absence verification.

See git-workflow/branch/SKILL.md and git-workflow/develop-guard/SKILL.md.
HOOKEOF
        exit 2
        ;;
esac

# Feature branch: ALLOW. Push-time hooks will gate the eventual commit.
exit 0
