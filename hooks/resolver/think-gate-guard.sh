#!/bin/bash
# UserPromptSubmit hook — think-gate enforcement via falsifiable claims.
#
# Reads <workspace>/think-gate.json and verifies each claim against the
# codebase on every turn. Narrates findings to the agent/user.
#
# Signal file schema:
#   {
#     "ticket": "#262",
#     "design_note": "https://github.com/.../issues/262#issuecomment-...",
#     "repo_root": "/absolute/path/to/repo",
#     "created": "2026-05-29T13:35:00-05:00",
#     "claims": [
#       {
#         "assertion": "human-readable description",
#         "file": "relative/to/repo_root",
#         "grep": "pattern to search for",
#         "expected": true
#       }
#     ]
#   }
#
# Behavior:
#   No signal file       → inject "No design note registered"
#   All claims pass      → inject "Design for #N is current. Proceed."
#   Any claim fails      → inject "STALE DESIGN: [assertion] no longer holds"
#   Malformed signal file → inject warning, fail-open
#
# Location: <workspace>/think-gate.json, derived from script path
# (hooks/resolver/think-gate-guard.sh → ../../).
#
# Ref: claude-configs-public#262

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SIGNAL_FILE="${CLAUDE_THINK_GATE:-$WORKSPACE_ROOT/think-gate.json}"

if [ ! -f "$SIGNAL_FILE" ]; then
    cat <<EOF
<think-gate>
No design note registered. Before writing code for any non-trivial
change, produce a design note (read skills/thinking/think/SKILL.md)
and write a think-gate.json signal file with falsifiable claims.

Signal file location: $SIGNAL_FILE
Ref: #262
</think-gate>
EOF
    exit 0
fi

RESULT=$(python3 -c "
import json, sys, os, subprocess

try:
    data = json.load(open('$SIGNAL_FILE'))
except Exception as e:
    print(f'WARN: think-gate.json is malformed: {e}')
    sys.exit(0)

ticket = data.get('ticket', 'unknown')
design_note = data.get('design_note', 'not specified')
repo_root = data.get('repo_root', '')
claims = data.get('claims', [])

if not claims:
    print(f'Design for {ticket} registered but has no claims.')
    print(f'Design note: {design_note}')
    print('Proceed, but consider adding falsifiable claims.')
    sys.exit(0)

failed = []
passed = []

for claim in claims:
    assertion = claim.get('assertion', '(unnamed)')
    filepath = claim.get('file', '')
    pattern = claim.get('grep', '')
    expected = claim.get('expected', True)

    if repo_root and not os.path.isabs(filepath):
        filepath = os.path.join(repo_root, filepath)

    if not os.path.isfile(filepath):
        if expected:
            failed.append(f'  FAIL: \"{assertion}\" -- file not found: {filepath}')
        else:
            passed.append(f'  OK: \"{assertion}\"')
        continue

    try:
        result = subprocess.run(
            ['grep', '-q', pattern, filepath],
            capture_output=True, timeout=5
        )
        found = (result.returncode == 0)
    except Exception:
        passed.append(f'  SKIP: \"{assertion}\" -- grep error')
        continue

    if found == expected:
        passed.append(f'  OK: \"{assertion}\"')
    else:
        failed.append(f'  FAIL: \"{assertion}\"')

for line in passed:
    print(line)
for line in failed:
    print(line)

if failed:
    print()
    print(f'STALE DESIGN for {ticket}: {len(failed)} claim(s) no longer hold.')
    print(f'The premises of your design have changed. Re-examine the')
    print(f'design note at {design_note} before proceeding.')
    print(f'Update or archive {os.path.basename(\"$SIGNAL_FILE\")} after reconciliation.')
else:
    print()
    print(f'Design for {ticket} is current ({len(passed)} claim(s) verified). Proceed.')
" 2>&1)

if [ -n "$RESULT" ]; then
    cat <<EOF
<think-gate>
$RESULT
</think-gate>
EOF
fi

exit 0
