#!/bin/bash
# PreToolUse hook — workaround tally.
#
# Detects repeated "fix-it" commands (rm -rf, git checkout --, git clean)
# and logs each to <workspace>/workaround-tally.json. When the same
# pattern appears 3+ times in a session, blocks with a directive to
# file a ticket instead of repeating the workaround.
#
# The tally file is also read by the UserPromptSubmit resolver hook
# (pre-action-guard.sh) for environments where PreToolUse doesn't fire.
#
# Trigger: PreToolUse on Bash commands
# Ref: claude-configs-public#312

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

WORKSPACE_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
TALLY_FILE="${WORKSPACE_ROOT}/workaround-tally.json"
THRESHOLD=3

python3 -c "
import json, sys, os, re, hashlib
from datetime import datetime

command = '''$COMMAND'''

WORKAROUND_PATTERNS = [
    (r'rm\s+(-rf?|--recursive)\s+', 'rm -rf'),
    (r'git\s+checkout\s+--\s+', 'git checkout --'),
    (r'git\s+clean\s+-[fd]', 'git clean'),
    (r'git\s+stash\s+(push|drop)', 'git stash'),
    (r'git\s+reset\s+--hard', 'git reset --hard'),
]

matched = None
for pattern, label in WORKAROUND_PATTERNS:
    if re.search(pattern, command):
        target = re.sub(r'\s+', ' ', command.strip())
        if len(target) > 120:
            target = target[:120]
        sig = hashlib.md5(target.encode()).hexdigest()[:8]
        matched = {'label': label, 'command': target, 'sig': sig}
        break

if not matched:
    sys.exit(0)

tally_file = '$TALLY_FILE'
threshold = $THRESHOLD

try:
    with open(tally_file) as f:
        tally = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    tally = {'patterns': {}}

sig = matched['sig']
if sig not in tally['patterns']:
    tally['patterns'][sig] = {
        'label': matched['label'],
        'first_command': matched['command'],
        'count': 0,
        'timestamps': [],
    }

entry = tally['patterns'][sig]
entry['count'] += 1
entry['timestamps'].append(datetime.now().isoformat())
if len(entry['timestamps']) > 10:
    entry['timestamps'] = entry['timestamps'][-10:]

with open(tally_file, 'w') as f:
    json.dump(tally, f, indent=2)

if entry['count'] >= threshold:
    print(f\"\"\"BLOCKED: This workaround has been used {entry['count']} times this session.

Pattern: {entry['label']}
Command: {entry['first_command']}
First seen: {entry['timestamps'][0]}
Count: {entry['count']}

Repeated workarounds mask bugs. Instead of running this command again:
1. File a ticket for the root cause
2. Investigate why this keeps happening
3. Fix the underlying issue

To override: include [workaround-acknowledged: <ticket-ref>] in the command.
\"\"\", file=sys.stderr)
    sys.exit(2)
" 2>&1

EXIT_CODE=$?

# Allow override via acknowledged marker
if [[ $EXIT_CODE -ne 0 ]] && echo "$COMMAND" | grep -qE '\[workaround-acknowledged:[[:space:]]+#[0-9]+\]'; then
    exit 0
fi

exit $EXIT_CODE
