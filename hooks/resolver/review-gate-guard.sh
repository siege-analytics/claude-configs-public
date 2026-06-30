#!/bin/bash
# UserPromptSubmit hook — review-gate enforcement.
#
# Reads <workspace>/review-gate.json (Craft Agent) or
# <repo>/.review-gate.json (pure Claude Code) and checks whether the
# branch has new commits since the last review. If so, emits a
# re-review directive.
#
# Signal file schema:
#   {
#     "ticket": "owner/repo#NNN",
#     "branch": "feat/my-feature",
#     "reviewed_commit": "abc1234def5678...",
#     "skill": "hostile-review",
#     "provider": "openai",
#     "verdict": "request-changes",
#     "findings_location": "URL or file path",
#     "created": "2026-06-25T00:00:00Z",
#     "lastChecked": "2026-06-25T00:00:00Z"
#   }
#
# Behavior:
#   No signal file           → silent (no output)
#   verdict = approve        → "Review approved. Gate clear."
#   Branch matches + no new  → "Review current. Proceed."
#   Branch matches + new     → "RE-REVIEW REQUIRED"
#   Branch does not match    → advisory note
#
# Works in both Craft Agent and pure Claude Code:
#   - Craft Agent: signal file at <workspace>/review-gate.json
#   - Claude Code: signal file at <repo>/.review-gate.json
#
# Ref: claude-configs-public#468

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESOLVE_TG="$SCRIPT_DIR/../lib/resolve-think-gate.py"

# Search order: env override, repo-scoped (#578), workspace singleton, repo-local
SIGNAL_FILE="${CLAUDE_REVIEW_GATE:-}"

if [ -z "$SIGNAL_FILE" ]; then
    REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
    # Repo-scoped resolution (#578)
    if [ -n "$REPO_ROOT" ] && [ -f "$RESOLVE_TG" ]; then
        SIGNAL_FILE=$(python3 "$RESOLVE_TG" --workspace "$WORKSPACE_ROOT" --repo-root "$REPO_ROOT" --gate-name review-gate 2>/dev/null | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['path'] if r else '')" 2>/dev/null || true)
    fi
    # Legacy fallback
    if [ -z "$SIGNAL_FILE" ]; then
        if [ -f "$WORKSPACE_ROOT/review-gate.json" ]; then
            SIGNAL_FILE="$WORKSPACE_ROOT/review-gate.json"
        elif [ -n "$REPO_ROOT" ] && [ -f "$REPO_ROOT/.review-gate.json" ]; then
            SIGNAL_FILE="$REPO_ROOT/.review-gate.json"
        fi
    fi
fi

if [ -z "$SIGNAL_FILE" ] || [ ! -f "$SIGNAL_FILE" ]; then
    exit 0
fi

RESULT=$(python3 -c "
import json, sys, subprocess

try:
    data = json.load(open('$SIGNAL_FILE'))
except Exception as e:
    print(f'WARN: review-gate signal file is malformed: {e}')
    sys.exit(0)

verdict = data.get('verdict', '')
branch = data.get('branch', '')
reviewed_commit = data.get('reviewed_commit', '')
ticket = data.get('ticket', 'unknown')
skill = data.get('skill', 'unknown')
provider = data.get('provider', 'unknown')
findings = data.get('findings_location', '')

if verdict == 'approve':
    print(f'Review for {ticket} approved ({provider}/{skill}). Gate clear.')
    sys.exit(0)

if not branch or not reviewed_commit:
    print(f'review-gate.json for {ticket} missing branch or reviewed_commit.')
    sys.exit(0)

# Get current branch
try:
    current = subprocess.check_output(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        text=True, timeout=5
    ).strip()
except Exception:
    current = ''

if current != branch:
    print(f'Review gate is for branch \"{branch}\" but current branch is \"{current}\".')
    print(f'Gate does not apply to this branch.')
    sys.exit(0)

# Check if HEAD has moved since the review
try:
    head = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'],
        text=True, timeout=5
    ).strip()
except Exception:
    print('Could not determine HEAD. Skipping review-gate check.')
    sys.exit(0)

if head.startswith(reviewed_commit) or reviewed_commit.startswith(head):
    print(f'Review for {ticket} is current (no new commits since review). Proceed.')
    sys.exit(0)

# HEAD differs from reviewed commit — new code since review
try:
    new_count = subprocess.check_output(
        ['git', 'rev-list', '--count', reviewed_commit + '..HEAD'],
        text=True, timeout=5
    ).strip()
except Exception:
    new_count = '?'

print(f'RE-REVIEW REQUIRED: {new_count} new commit(s) on \"{branch}\" since last review.')
print(f'  Reviewed commit: {reviewed_commit[:12]}')
print(f'  Current HEAD:    {head[:12]}')
print(f'  Original review: {provider}/{skill} (verdict: {verdict})')
if findings:
    print(f'  Prior findings:  {findings}')
print()
print(f'Before pushing, re-run the review on the current code:')
print(f'  - Use cross-review with skill=\"{skill}\" on the changed files')
print(f'  - Or use the cross-review MCP source directly')
print(f'  - Update review-gate.json with the new reviewed_commit after re-review')
" 2>&1)

if [ -n "$RESULT" ]; then
    cat <<EOF
<review-gate>
$RESULT
</review-gate>
EOF
fi

exit 0
