#!/bin/bash
# Hook: bash/universal-mutation-gate (v1)
# Enforces: fail-closed mutation gating (#473, parent #415)
# Trigger: PreToolUse on Bash — MUST be FIRST in the Bash hook list
#
# Inverts the enforcement default: instead of listing guarded mutations
# (fail-open), this hook lists safe reads (fail-closed). Every Bash
# command not on the safelist is blocked unless a valid think-gate.json
# exists with status=implementing.
#
# Decision flow:
#   1. Extract command from stdin JSON
#   2. Match against SAFE_PATTERNS -> PASS
#   3. Check think-gate.json status=implementing -> PASS
#   4. Check for [mutation-acknowledged] in command -> PASS (one-shot)
#   5. BLOCK (exit 2)
#
# Escape hatches:
#   1. think-gate.json with status=implementing (normal workflow)
#   2. [mutation-acknowledged] inline in the command (audit trail)
#   3. CLAUDE_MUTATION_GATE=off env var (emergency disable, discouraged)

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

[[ -z "$COMMAND" ]] && exit 0

# Emergency disable
if [[ "${CLAUDE_MUTATION_GATE:-}" == "off" ]]; then
    exit 0
fi

# --- SAFE_PATTERNS: read-only commands that pass without check ---
# Each pattern is an extended regex. Order does not matter.
# Add new patterns conservatively: if unsure whether a command mutates, leave it off.
SAFE_PATTERNS=(
    # File reads
    '^(cat|head|tail|less|more|wc|file|stat|du|df|find|tree|which|type|readlink|realpath|md5|sha256sum|shasum|xxd|od|hexdump) '
    '^ls( |$)'

    # Content search
    '^(grep|egrep|fgrep|rg|ag|ack|ripgrep) '

    # Git reads (status, log, diff, show, branch listing, tag listing, etc.)
    '^(cd .* &&[[:space:]]*)?(git )(log|status|diff|show|branch|tag|rev-parse|merge-base|remote|config|describe|rev-list|shortlog|blame|ls-tree|ls-files|cat-file|name-rev|for-each-ref|stash list|fetch|worktree list)( |$)'

    # GitHub CLI reads
    '^(cd .* &&[[:space:]]*)?(gh )(issue (view|list)|pr (view|list|checks|diff|status)|repo view|release (view|list)|api .* --method GET|run (view|list))( |$)'

    # Python read-only operations
    '^python3? -c .*(import ast|import sys|import json|print\().*$'
    '^(pip|pip3) (list|show|freeze|check)( |$)'
    '^python3? -m (pip (list|show|freeze)|pytest|py_compile)( |$)'

    # System info (no side effects)
    '^(echo|printf|date|env|printenv|uname|hostname|whoami|id|pwd|dirname|basename|true|false) '
    '^(echo|printf|date|env|printenv|uname|hostname|whoami|id|pwd|dirname|basename|true|false)$'
    '^test '
    '^\['

    # Build and test tools (outputs only, gated elsewhere)
    '^(cd .* &&[[:space:]]*)?(pytest|python3? -m pytest|sphinx-build|bash -n|shellcheck|flake8|mypy|ruff check|pylint|black --check|isort --check) '

    # Package/dependency reads
    '^(npm|yarn|pnpm) (list|ls|info|view|outdated|audit)( |$)'
    '^(brew|apt|dnf|yum) (list|info|search|show)( |$)'

    # markitdown and doc tools (read-only conversions to stdout)
    '^(markitdown|pdf-tool (info|extract)|xlsx-tool (read|info)|pptx-tool info|doc-diff|ical-tool read) '
)

# --- Compound command mutation scan ---
# A command starting with a safe read but containing a mutation via && or ;
# or | is still a mutation. Scan the full string for mutation indicators
# BEFORE checking the safelist. If any mutation indicator appears anywhere
# in the command, skip the safelist and fall through to think-gate check.
MUTATION_INDICATORS=(
    'git (push|commit|reset|checkout|rebase|merge|cherry-pick|revert|stash (pop|drop|apply|clear)|clean|tag -[adf]|branch -[dDmM])'
    'gh (issue (create|comment|close|edit|delete|reopen|transfer)|pr (create|merge|close|edit|comment|review)|release (create|delete|edit)|repo (create|delete|fork|rename))'
    'glab (issue (create|close|note)|mr (create|merge|close|note|approve))'
    'rm (-[rRf]|--force|--recursive)'
    'curl.* -X (POST|PUT|DELETE|PATCH)'
    'pip[3]? install'
    'npm install|yarn add|pnpm add'
    'cat .* >|tee |> |>> '
    'mkdir |touch |mv |cp '
    'chmod |chown |chgrp '
    'docker |kubectl |helm '
    'psql .* -c|mysql .* -e'
    'aws s3 (cp|mv|rm|sync)'
    'spawn_session'
)

COMPOUND_MUTATION=false
for m_pattern in "${MUTATION_INDICATORS[@]}"; do
    if [[ "$COMMAND" =~ $m_pattern ]]; then
        COMPOUND_MUTATION=true
        break
    fi
done

# --- Match against safelist (only if no mutation indicator found) ---
if [[ "$COMPOUND_MUTATION" == "false" ]]; then
    for pattern in "${SAFE_PATTERNS[@]}"; do
        if [[ "$COMMAND" =~ $pattern ]]; then
            exit 0
        fi
    done
fi

# --- Check for [mutation-acknowledged] escape ---
if [[ "$COMMAND" == *'[mutation-acknowledged]'* ]]; then
    echo "[universal-mutation-gate] One-shot bypass: mutation-acknowledged" >&2
    exit 0
fi

# --- Check think-gate.json ---
# Search order: CLAUDE_THINK_GATE env, workspace root, repo .think-gate.json
THINK_GATE=""
if [[ -n "${CLAUDE_THINK_GATE:-}" ]] && [[ -f "$CLAUDE_THINK_GATE" ]]; then
    THINK_GATE="$CLAUDE_THINK_GATE"
elif [[ -n "${CRAFT_AGENT_WORKSPACE:-}" ]] && [[ -f "$CRAFT_AGENT_WORKSPACE/think-gate.json" ]]; then
    THINK_GATE="$CRAFT_AGENT_WORKSPACE/think-gate.json"
else
    # Derive workspace from hook path: hooks/bash/ -> two levels up from hooks/
    WORKSPACE_CANDIDATE="$(dirname "$(dirname "$HOOK_DIR")")"
    if [[ -f "$WORKSPACE_CANDIDATE/think-gate.json" ]]; then
        THINK_GATE="$WORKSPACE_CANDIDATE/think-gate.json"
    fi
    # Also check CWD for Claude Code (repo-local .think-gate.json)
    CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)
    if [[ -z "$THINK_GATE" ]] && [[ -n "$CWD" ]] && [[ -f "$CWD/.think-gate.json" ]]; then
        THINK_GATE="$CWD/.think-gate.json"
    fi
fi

if [[ -n "$THINK_GATE" ]]; then
    TG_STATUS=$(python3 -c "
import json, sys
try:
    d = json.load(open('$THINK_GATE'))
    print(d.get('status', ''))
except Exception:
    pass
" 2>/dev/null || true)

    if [[ "$TG_STATUS" == "implementing" || "$TG_STATUS" == "designing" || "$TG_STATUS" == "reviewing" ]]; then
        exit 0
    fi
fi

# --- BLOCK ---
# Extract a short summary of what was attempted
CMD_SHORT="${COMMAND:0:120}"
if [[ ${#COMMAND} -gt 120 ]]; then
    CMD_SHORT="${CMD_SHORT}..."
fi

cat >&2 <<HOOKEOF
BLOCKED by universal-mutation-gate (v1, #473)

Command: $CMD_SHORT

This command is not on the read-only safelist and no valid think-gate.json
was found with status=implementing.

To proceed, choose one:
  1. Produce a design note (think gate) and write think-gate.json
     with status=implementing — this is the normal workflow.
  2. Add [mutation-acknowledged] to the command for a one-shot bypass.
  3. If this command is genuinely read-only and should be on the safelist,
     add its pattern to hooks/bash/universal-mutation-gate.sh SAFE_PATTERNS.

The enforcement default is fail-closed: unknown commands are blocked,
not passed. See #473 for rationale.
HOOKEOF
exit 2
