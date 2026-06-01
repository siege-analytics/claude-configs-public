#!/bin/bash
# UserPromptSubmit hook — investigate-gate enforcement.
#
# Checks for <workspace>/investigate-gate.json when think-gate.json exists.
# If a design is registered (think-gate) but investigation has not been
# completed (no investigate-gate), injects a blocking directive.
#
# Level 1: Gate existence — blocks implementation when investigation is missing.
# Level 2: Citation spot-check — greps file:line claims in verifiedShapes
#          to confirm cited content exists at cited locations.
#
# Signal file schema:
#   {
#     "ticket": "#255",
#     "factSheetLocation": "URL or file path to posted Fact Sheet",
#     "timestamp": "ISO 8601",
#     "tier": "full" | "focused",
#     "verifiedShapes": [
#       {
#         "entity": "human-readable name",
#         "file": "relative/path/to/file",
#         "line": 42,
#         "grep": "pattern expected at that line",
#         "status": "VERIFIED" | "UNVERIFIED"
#       }
#     ],
#     "designNote": "path or URL to think design note"
#   }
#
# Behavior:
#   No think-gate.json       → no pipeline active → allow (exit 0)
#   think-gate.json exists,
#     investigate-gate.json missing → BLOCK: investigation required
#   Both exist, investigate older    → STALE: re-investigation required
#   Both exist, citations fail       → WARN: N citation(s) could not be verified
#   Both exist, citations pass       → "Investigation current. Proceed."
#
# Location: <workspace>/investigate-gate.json
# Ref: claude-configs-public#255
#
# Levels 1-3 enforcement ladder (standard, always active):
#   L1: gate existence (this hook)
#   L2: citation spot-check (this hook)
#   L3: Pre-ship-dry-run trailer (self-review.sh)
# Level 4 (probation) is operator-triggered, not in this hook.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
THINK_GATE="${CLAUDE_THINK_GATE:-$WORKSPACE_ROOT/think-gate.json}"
INVESTIGATE_GATE="${CLAUDE_INVESTIGATE_GATE:-$WORKSPACE_ROOT/investigate-gate.json}"

# No think-gate → no pipeline active → nothing to enforce
if [ ! -f "$THINK_GATE" ]; then
    exit 0
fi

# Check think-gate status — disposed/done designs don't need investigation
THINK_STATUS=$(python3 -c "
import json, sys
try:
    data = json.load(open('$THINK_GATE'))
    print(data.get('status', ''))
except:
    print('')
" 2>/dev/null || echo "")

if [ "$THINK_STATUS" = "disposed" ] || [ "$THINK_STATUS" = "done-awaiting-pr" ]; then
    exit 0
fi

# Think-gate exists but no investigate-gate → Level 1 BLOCK
if [ ! -f "$INVESTIGATE_GATE" ]; then
    THINK_TICKET=$(python3 -c "
import json
data = json.load(open('$THINK_GATE'))
print(data.get('ticket', 'unknown'))
" 2>/dev/null || echo "unknown")

    cat <<EOF
<investigate-gate>
INVESTIGATION REQUIRED before implementation.

Design for $THINK_TICKET is approved (think-gate.json exists), but no
investigation has been completed (investigate-gate.json missing).

You MUST:
1. Read skills/thinking/investigate/SKILL.md
2. Produce a Fact Sheet with file:line citations (Phase 1-5)
3. Post the Fact Sheet to the ticket
4. Write investigate-gate.json with verifiedShapes

Until investigate-gate.json exists, implementation writes are blocked
by the investigation skill's "no artifact CRUD before investigation" rule.

Signal file location: $INVESTIGATE_GATE
Ref: #255 (mid-pipeline enforcement gap)
</investigate-gate>
EOF
    exit 0
fi

# Both exist — check staleness (investigate older than think = stale)
THINK_MTIME=$(stat -f %m "$THINK_GATE" 2>/dev/null || stat -c %Y "$THINK_GATE" 2>/dev/null || echo "0")
INVEST_MTIME=$(stat -f %m "$INVESTIGATE_GATE" 2>/dev/null || stat -c %Y "$INVESTIGATE_GATE" 2>/dev/null || echo "0")

if [ "$INVEST_MTIME" -lt "$THINK_MTIME" ]; then
    cat <<EOF
<investigate-gate>
STALE INVESTIGATION: investigate-gate.json is older than think-gate.json.

The design changed after investigation was completed. Re-investigate:
the Fact Sheet may no longer match the current design approach.

Update investigate-gate.json after re-investigation.
Ref: #255
</investigate-gate>
EOF
    exit 0
fi

# Both exist and fresh — Level 2: spot-check citations
RESULT=$(python3 -c "
import json, sys, os

try:
    data = json.load(open('$INVESTIGATE_GATE'))
except Exception as e:
    print(f'WARN: investigate-gate.json malformed: {e}')
    sys.exit(0)

ticket = data.get('ticket', 'unknown')
fact_sheet = data.get('factSheetLocation', 'not specified')
tier = data.get('tier', 'unknown')
shapes = data.get('verifiedShapes', [])

if not shapes:
    print(f'Investigation for {ticket} registered (tier: {tier}) but has no verifiedShapes.')
    print(f'Fact Sheet: {fact_sheet}')
    print('WARN: No citations to spot-check. Proceeding, but this is suspicious.')
    sys.exit(0)

# Spot-check each shape that has file + line + grep
checked = 0
passed = 0
failed = []
skipped = 0

for shape in shapes:
    entity = shape.get('entity', '(unnamed)')
    filepath = shape.get('file', '')
    line_num = shape.get('line', 0)
    pattern = shape.get('grep', '')
    status = shape.get('status', 'VERIFIED')

    if status == 'UNVERIFIED':
        skipped += 1
        continue

    if not filepath or not pattern:
        skipped += 1
        continue

    checked += 1

    if not os.path.isfile(filepath):
        # Try relative to common roots
        found = False
        for root_env in ['INVESTIGATE_GATE_REPO_ROOT']:
            root = os.environ.get(root_env, '')
            if root and os.path.isfile(os.path.join(root, filepath)):
                filepath = os.path.join(root, filepath)
                found = True
                break
        if not found:
            failed.append(f'  FAIL: \"{entity}\" — file not found: {filepath}')
            continue

    try:
        with open(filepath, 'r', errors='replace') as f:
            lines = f.readlines()

        if line_num > 0 and line_num <= len(lines):
            # Check specific line
            if pattern in lines[line_num - 1]:
                passed += 1
            else:
                # Fuzzy: check ±3 lines
                nearby = lines[max(0, line_num-4):line_num+3]
                if any(pattern in l for l in nearby):
                    passed += 1
                else:
                    failed.append(f'  FAIL: \"{entity}\" — \"{pattern}\" not found near line {line_num} of {filepath}')
        else:
            # No line number, grep whole file
            content = ''.join(lines)
            if pattern in content:
                passed += 1
            else:
                failed.append(f'  FAIL: \"{entity}\" — \"{pattern}\" not found in {filepath}')
    except Exception as e:
        failed.append(f'  SKIP: \"{entity}\" — read error: {e}')

# Report
print(f'Investigation for {ticket} (tier: {tier})')
print(f'Fact Sheet: {fact_sheet}')
print(f'Citations: {passed} passed, {len(failed)} failed, {skipped} skipped/unverified')

if failed:
    print()
    for f in failed:
        print(f)
    print()
    print('WARN: Some file:line citations could not be verified.')
    print('The cited content may have changed since investigation.')
    print('Re-verify before proceeding with implementation.')
else:
    print()
    print(f'Investigation current ({passed} citations verified). Proceed.')
" 2>&1)

if [ -n "$RESULT" ]; then
    cat <<EOF
<investigate-gate>
$RESULT
</investigate-gate>
EOF
fi

exit 0
