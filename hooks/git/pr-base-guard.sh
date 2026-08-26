#!/bin/bash
# Hook: pr-base-guard
# Enforces: skills/git-workflow/develop-guard/SKILL.md, skills/git-workflow/branch/SKILL.md
# Trigger: PreToolUse on Bash(gh pr create *)
#
# Blocks PR-creation invocations whose effective --base is a main-role
# branch (main, master, prod, ...) unless the head branch is a
# develop-role / release/* / promote/* / hotfix/* shape, or the command
# includes the --label hotfix-direct-to-main bypass.
#
# This is the local mechanical enforcement of the curation invariant
# documented in develop-guard/SKILL.md. The skill is the prose layer;
# the agent's recurring failure to consult it before `gh pr create`
# motivated this hook (siege-analytics/claude-configs-public#198).
#
# Same false-positive recovery posture as branch-guard.sh / self-review.sh:
# yield on multi-cd commands, cross-repo cd, etc. (issues #98, #101).

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Match `gh pr create` (GitHub) or `glab mr create` (GitLab) anywhere in
# the command. Portable word-boundary form (BSD grep does not support
# `\b`); see issue #106 fix for self-review. Both platforms use the same
# develop-first rule (CCP#201); the parser below switches on which CLI
# matched to handle the per-CLI flag shapes (--base vs --target-branch).
TRIGGER='(^|[^[:alnum:]])(gh[[:space:]]+pr[[:space:]]+create|glab[[:space:]]+mr[[:space:]]+create)([^[:alnum:]]|$)'
if ! echo "$COMMAND" | grep -qE "$TRIGGER"; then
    exit 0
fi

# Yield on multi-statement-with-cd shapes (mirrors branch-guard.sh / self-review.sh).
CD_COUNT=$(echo "$COMMAND" | { grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    if [[ "$CD_COUNT" -gt 1 ]] || echo "$COMMAND" | grep -qE $'\n|;|\\|\\|'; then
        exit 0
    fi
fi

# Resolve effective repo dir (follow leading-cd pattern from branch-guard).
EFFECTIVE_CWD="$CWD"
if [[ "$COMMAND" =~ ^[[:space:]]*cd[[:space:]]+([^[:space:];&]+) ]]; then
    CD_TARGET="${BASH_REMATCH[1]}"
    CD_TARGET="${CD_TARGET%\"}"; CD_TARGET="${CD_TARGET#\"}"
    CD_TARGET="${CD_TARGET%\'}"; CD_TARGET="${CD_TARGET#\'}"
    case "$CD_TARGET" in
        /*) ;;
        *) CD_TARGET="$CWD/$CD_TARGET" ;;
    esac
    if [[ -d "$CD_TARGET" ]]; then
        OUTER_TOP=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || echo "")
        TARGET_TOP=$(git -C "$CD_TARGET" rev-parse --show-toplevel 2>/dev/null || echo "")
        if [[ -z "$TARGET_TOP" ]]; then
            exit 0
        fi
        if [[ "$OUTER_TOP" != "$TARGET_TOP" ]]; then
            exit 0
        fi
        EFFECTIVE_CWD="$CD_TARGET"
    else
        exit 0
    fi
fi

if [[ -z "$EFFECTIVE_CWD" ]]; then
    exit 0
fi

# Extract the PR/MR target branch from the command. Both CLIs have
# their own flag shape:
#   gh pr create:   --base / --base= / -B  (GitHub)
#   glab mr create: --target-branch / --target-branch= / -b  (GitLab)
# We only need the next bare word; both CLIs accept branch names with
# no special characters in the role synonyms we care about.
PR_BASE=""
if echo "$COMMAND" | grep -qE '(^|[^[:alnum:]])glab[[:space:]]+mr[[:space:]]+create([^[:alnum:]]|$)'; then
    # GitLab path
    if [[ "$COMMAND" =~ --target-branch[[:space:]]+([A-Za-z0-9_/.-]+) ]]; then
        PR_BASE="${BASH_REMATCH[1]}"
    elif [[ "$COMMAND" =~ --target-branch=([A-Za-z0-9_/.-]+) ]]; then
        PR_BASE="${BASH_REMATCH[1]}"
    elif [[ "$COMMAND" =~ (^|[[:space:]])-b[[:space:]]+([A-Za-z0-9_/.-]+) ]]; then
        PR_BASE="${BASH_REMATCH[2]}"
    fi
    # Fall back to glab's default-branch query.
    if [[ -z "$PR_BASE" ]]; then
        PR_BASE=$(cd "$EFFECTIVE_CWD" && glab repo view --output json 2>/dev/null | python3 "$EXTRACT" default_branch 2>/dev/null || echo "")
        if [[ -z "$PR_BASE" ]]; then
            exit 0
        fi
    fi
else
    # GitHub path (default)
    if [[ "$COMMAND" =~ --base[[:space:]]+([A-Za-z0-9_/.-]+) ]]; then
        PR_BASE="${BASH_REMATCH[1]}"
    elif [[ "$COMMAND" =~ --base=([A-Za-z0-9_/.-]+) ]]; then
        PR_BASE="${BASH_REMATCH[1]}"
    elif [[ "$COMMAND" =~ (^|[[:space:]])-B[[:space:]]+([A-Za-z0-9_/.-]+) ]]; then
        PR_BASE="${BASH_REMATCH[2]}"
    fi
    # Fall back to gh's default-branch query.
    if [[ -z "$PR_BASE" ]]; then
        PR_BASE=$(cd "$EFFECTIVE_CWD" && gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null || echo "")
        if [[ -z "$PR_BASE" ]]; then
            exit 0
        fi
    fi
fi

# Main-role synonyms (mirror skills/git-workflow/develop-guard/SKILL.md).
case "$PR_BASE" in
    main|master|prod|production|trunk|stable|release)
        ;;
    *)
        # Base is not main-role; no enforcement applies.
        exit 0
        ;;
esac

# At this point: base is a main-role branch. Allow if head is
# develop-role, release/*, promote/*, hotfix/*, or the command carries
# the hotfix-direct-to-main bypass label.

# Bypass label check first (cheap; doesn't need git).
if echo "$COMMAND" | grep -qE '(^|[^[:alnum:]])--label[[:space:]]+hotfix-direct-to-main([^[:alnum:]]|$)'; then
    exit 0
fi
if echo "$COMMAND" | grep -qE '(^|[^[:alnum:]])--label=hotfix-direct-to-main([^[:alnum:]]|$)'; then
    exit 0
fi

HEAD_BRANCH=$(git -C "$EFFECTIVE_CWD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [[ -z "$HEAD_BRANCH" ]]; then
    exit 0
fi

# Allow develop-role heads (canonical promote) and release/promote/hotfix shapes.
case "$HEAD_BRANCH" in
    develop|dev|development|next|integration|staging|develop-next)
        exit 0
        ;;
    release/*|promote/*|hotfix/*)
        exit 0
        ;;
esac

# Block. Print the develop-guard skill's remediation; the message is
# the operator-facing surface for this hook and must point at the
# canonical skill, not just complain.
# Detect which CLI matched to surface the right remediation flag name.
if echo "$COMMAND" | grep -qE '(^|[^[:alnum:]])glab[[:space:]]+mr[[:space:]]+create([^[:alnum:]]|$)'; then
    REMEDIATION_FLAG="--target-branch develop"
    CLI_LABEL="glab mr create"
else
    REMEDIATION_FLAG="--base develop"
    CLI_LABEL="gh pr create"
fi

cat >&2 <<EOF
BLOCKED: $CLI_LABEL targets main-role branch '$PR_BASE' but head '$HEAD_BRANCH'
is not develop-role / promote / release / hotfix, and the command does
not carry the 'hotfix-direct-to-main' label.

Per skills/git-workflow/develop-guard/SKILL.md (the curation invariant):
main-role is the curated best of all work; develop-role is the origin
where experiments compete for promotion. Feature/task/bugfix PRs/MRs
target the develop-role branch, not main.

Remediation:
  - Re-target the PR/MR: \`$REMEDIATION_FLAG\` (or your repo's develop-role synonym).
  - If this is a deliberate release/promote/hotfix shape, rename the head
    branch to match \`release/*\` / \`promote/*\` / \`hotfix/*\`.
  - If this is a deliberate hotfix that must bypass develop, add
    \`--label hotfix-direct-to-main\` (audit trail in the PR/MR's label
    history; matches the server-side guard in pr-base-guard.yml and
    templates/gitlab-pr-base-guard.yml).

See develop-guard/SKILL.md for the full decision tree.
EOF
exit 2
