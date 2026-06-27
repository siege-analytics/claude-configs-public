#!/bin/bash
# Hook: bash/universal-mutation-gate (v2)
# Enforces: fail-closed mutation gating (#473, hardened #477)
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
#   3. Check think-gate.json status=designing|reviewing -> PASS
#   4. Check think-gate.json status=implementing + artifact checks -> PASS
#   5. BLOCK (exit 2)
#
# No escape hatches. If the gate blocks a legitimate command, the fix is
# adding it to SAFE_PATTERNS or producing the required artifacts.
# See #477 for rationale.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

[[ -z "$COMMAND" ]] && exit 0

# No emergency disable. To disable the gate, comment out the hook in
# settings.json — that produces an auditable change. (#477)

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
    # Note: git config is read-only only for --get/--list/--get-regexp forms;
    # bare 'git config' can write. Narrow to read-only subcommands.
    '^(cd .* &&[[:space:]]*)?(git )(log|status|diff|show|branch|tag|rev-parse|merge-base|remote|config (--get|--list|--get-regexp|--get-all)|describe|rev-list|shortlog|blame|ls-tree|ls-files|cat-file|name-rev|for-each-ref|stash list|fetch|worktree list)( |$)'

    # GitHub CLI reads
    '^(cd .* &&[[:space:]]*)?(gh )(issue (view|list)|pr (view|list|checks|diff|status)|repo view|release (view|list)|api .* --method GET|run (view|list))( |$)'

    # Python read-only operations (no arbitrary -c; only known-safe modules)
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
    '\brm [^-]'
    'sed -i|sed --in-place'
    'awk -i inplace'
    '\bpatch '
    'curl.* -X (POST|PUT|DELETE|PATCH)'
    'pip[3]? install'
    'npm install|yarn add|pnpm add'
    'cat .* >|tee |>[^ ]|> |>> '
    'mkdir |touch |mv |cp '
    'chmod |chown |chgrp '
    'git config (--global|--system|--local|--unset|--add|--replace-all)'
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

# [mutation-acknowledged] bypass removed (#477). Self-authorization is the
# problem, not the solution. If a command is legitimately safe, add it to
# SAFE_PATTERNS. If the pipeline is incomplete, complete it.

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
    d = json.load(open(sys.argv[1]))
    print(d.get('status', ''))
except Exception:
    pass
" "$THINK_GATE" 2>/dev/null || true)

    if [[ "$TG_STATUS" == "designing" || "$TG_STATUS" == "reviewing" ]]; then
        exit 0
    fi

    if [[ "$TG_STATUS" == "implementing" ]]; then
        # Artifact checks with ticket association (#477, #484)
        # Artifacts must exist AND reference the current ticket.
        WORKSPACE_CANDIDATE="$(dirname "$(dirname "$HOOK_DIR")")"

        MISSING=$(python3 -c "
import json, sys, os, glob

think_gate_path = sys.argv[1]
workspace = sys.argv[2]
plans_path = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '__none__' else ''

try:
    tg = json.load(open(think_gate_path))
except Exception:
    sys.exit(0)

current_ticket = tg.get('ticket', '')

def ticket_slug(ref):
    if not ref or '#' not in ref:
        return ref or ''
    return '#' + ref.split('#')[-1]

def file_references_ticket(path, ticket):
    if not ticket:
        return True
    try:
        content = open(path).read(4096)
    except Exception:
        return False
    return ticket in content or ticket_slug(ticket) in content

missing = []

# 1. Check investigate-gate.json (ticket field must match)
invest_found = False
for candidate in [
    os.environ.get('CRAFT_AGENT_WORKSPACE', '') + '/investigate-gate.json',
    os.path.join(workspace, 'investigate-gate.json'),
]:
    if os.path.isfile(candidate):
        try:
            ig = json.load(open(candidate))
            if ig.get('ticket', '') == current_ticket or not current_ticket:
                invest_found = True
                break
        except Exception:
            pass
if not invest_found:
    missing.append('investigate-gate.json for ' + (current_ticket or 'current task'))

# 2. Check pre-mortem artifact (must reference current ticket)
premortem_found = False
plan_dirs = []
if plans_path and os.path.isdir(plans_path):
    plan_dirs.append(plans_path)
ca_ws = os.environ.get('CRAFT_AGENT_WORKSPACE', '')
if ca_ws:
    ca_plans = os.path.join(ca_ws, 'plans')
    if os.path.isdir(ca_plans):
        plan_dirs.append(ca_plans)
ws_plans = os.path.join(workspace, 'plans')
if os.path.isdir(ws_plans):
    plan_dirs.append(ws_plans)

# Repo plans/ (from think-gate.json repo_root field)
repo_root = tg.get('repo_root', '')
if repo_root:
    repo_plans = os.path.join(repo_root, 'plans')
    if os.path.isdir(repo_plans) and repo_plans not in plan_dirs:
        plan_dirs.append(repo_plans)

for d in plan_dirs:
    for pattern in ['pre-mortem*', 'premortem*', 'risk*']:
        for f in glob.glob(os.path.join(d, pattern)):
            if os.path.isfile(f) and file_references_ticket(f, current_ticket):
                premortem_found = True
                break
        if premortem_found:
            break
    if premortem_found:
        break

if not premortem_found:
    missing.append('pre-mortem artifact for ' + (current_ticket or 'current task'))

print('|'.join(missing))
" "$THINK_GATE" "$WORKSPACE_CANDIDATE" "${CRAFT_AGENT_PLANS_PATH:-__none__}" 2>/dev/null || true)

        if [[ -z "$MISSING" ]]; then
            exit 0
        fi

        # Format the missing list for display
        MISSING_DISPLAY=$(echo "$MISSING" | tr '|' '\n' | sed 's/^/  - /')

        cat >&2 <<ARTEOF
BLOCKED by universal-mutation-gate (#477/#484): artifacts missing or wrong ticket

think-gate.json status=implementing, but required artifacts are missing
or do not reference the current ticket:
$MISSING_DISPLAY

The gate requires both an investigation artifact (investigate-gate.json)
and a pre-mortem artifact (plans/pre-mortem-*.md) that reference the
CURRENT ticket. Artifacts from prior tasks do not satisfy the gate.

Produce the missing artifacts for the current ticket, then retry.
ARTEOF
        exit 2
    fi
fi

# --- BLOCK ---
# Extract a short summary of what was attempted
CMD_SHORT="${COMMAND:0:120}"
if [[ ${#COMMAND} -gt 120 ]]; then
    CMD_SHORT="${CMD_SHORT}..."
fi

cat >&2 <<HOOKEOF
BLOCKED by universal-mutation-gate (v2, #473/#477)

Command: $CMD_SHORT

This command is not on the read-only safelist and no valid think-gate.json
was found with an active status.

To proceed:
  1. Produce a design note (think gate) and write think-gate.json
     with status=designing — this is the normal workflow.
  2. If this command is genuinely read-only and should be on the safelist,
     add its pattern to hooks/bash/universal-mutation-gate.sh SAFE_PATTERNS.

There are no bypass mechanisms. The enforcement default is fail-closed.
See #473 (original gate) and #477 (hardening).
HOOKEOF
exit 2
