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
# Level 3: Disposition validation — checks that verifiedShapes entries include
#          a dispositions array with PROBED/ATTESTED/SKIPPED entries per the
#          Sagan assumption universe format. V1 signal files (no dispositions)
#          get a warning, not a block.
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
#         "status": "VERIFIED" | "UNVERIFIED",
#         "dispositions": [            // v2 schema — optional for backward compat
#           {
#             "layer": "schematic",    // physical|schematic|semantic|operational|correctness
#             "assumption": "takes 2 positional args",
#             "disposition": "PROBED", // PROBED|ATTESTED|SKIPPED
#             "probe": "grep ...",     // PROBED: command run
#             "result": "...",         // PROBED: output
#             "threshold": "PASS"      // PROBED: PASS|FAIL
#             // ATTESTED: "source" + "value"
#             // SKIPPED: "skipReason" (>=20 chars, no trivial phrases)
#           }
#         ]
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
# Repo-scoped resolution (#494): check think-gate-*.json first, fall back to think-gate.json
RESOLVE_TG="$SCRIPT_DIR/../lib/resolve-think-gate.py"
THINK_GATE="${CLAUDE_THINK_GATE:-}"
if [[ -z "$THINK_GATE" ]] && [[ -f "$RESOLVE_TG" ]]; then
    THINK_GATE=$(python3 "$RESOLVE_TG" --workspace "$WORKSPACE_ROOT" --all 2>/dev/null | python3 -c "
import json, sys
gates = json.load(sys.stdin)
for g in gates:
    s = g.get('data', {}).get('status', '')
    if s not in ('disposed', 'done-awaiting-pr', 'complete'):
        print(g['path'])
        sys.exit(0)
if gates:
    print(gates[0]['path'])
" 2>/dev/null || true)
fi
if [[ -z "$THINK_GATE" ]]; then
    THINK_GATE="$WORKSPACE_ROOT/think-gate.json"
fi
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

Re-run investigation and update investigate-gate.json, or archive it
(post disposition to ticket, then rm the file).
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

# Level 2.5: Scope mismatch check.
# If the investigate-gate ticket doesn't match the current branch's ticket,
# warn about stale/mismatched scope (#323).
SCOPE_WARN=""
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ -n "$BRANCH_NAME" ] && [ "$BRANCH_NAME" != "HEAD" ]; then
    SIGNAL_TICKET=$(python3 -c "
import json, re, sys
try:
    data = json.load(open('$INVESTIGATE_GATE'))
    raw = data.get('ticket', '')
    m = re.search(r'#(\d+)', raw)
    if m:
        print(m.group(1))
    else:
        m = re.search(r'([A-Z]+-\d+)', raw)
        if m:
            print(m.group(1))
except:
    pass
" 2>/dev/null || echo "")

    BRANCH_TICKETS=$(echo "$BRANCH_NAME" | grep -oE '([0-9]+|[A-Z]+-[0-9]+)' || true)

    if [ -n "$SIGNAL_TICKET" ] && [ -n "$BRANCH_TICKETS" ]; then
        if ! echo "$BRANCH_TICKETS" | grep -qF "$SIGNAL_TICKET"; then
            DISPLAY_TICKET="${SIGNAL_TICKET}"
            if echo "$SIGNAL_TICKET" | grep -qE '^[0-9]+$'; then DISPLAY_TICKET="#${SIGNAL_TICKET}"; fi
            SCOPE_WARN="SCOPE MISMATCH: investigate-gate.json is for ${DISPLAY_TICKET} but current branch is '${BRANCH_NAME}'.
To continue: update the signal file for the current task.
To archive: post disposition to the ticket, then rm investigate-gate.json."
        fi
    fi
fi

if [ -n "$SCOPE_WARN" ]; then
    cat <<EOF
<investigate-gate>
$SCOPE_WARN
</investigate-gate>
EOF
fi

# Level 2.75: Temporal decay check.
# Detects stale signal files based on lastUpdated/timestamp or file mtime.
# Tiered warnings: 4h stale (active), 24h expired (active).
# Ref: #328
DECAY_WARN=$(python3 -c "
import json, sys, os, time
from datetime import datetime, timezone

try:
    data = json.load(open('$INVESTIGATE_GATE'))
except:
    sys.exit(0)

last_updated = data.get('lastUpdated', '') or data.get('timestamp', '')
ticket = data.get('ticket', 'unknown')

if last_updated:
    try:
        ts = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
        age_source = 'lastUpdated' if data.get('lastUpdated') else 'timestamp'
    except:
        age_seconds = time.time() - os.path.getmtime('$INVESTIGATE_GATE')
        age_source = 'file mtime (timestamp unparseable)'
else:
    age_seconds = time.time() - os.path.getmtime('$INVESTIGATE_GATE')
    age_source = 'file mtime (no timestamp field)'

age_hours = age_seconds / 3600

if age_hours >= 24:
    print(f'EXPIRED SIGNAL: investigate-gate.json for {ticket} has not been updated in {age_hours:.0f}h (source: {age_source}).')
    print(f'A signal older than 24h likely reflects an abandoned or interrupted task.')
    print(f'Re-investigate before continuing. Update lastUpdated or timestamp after review.')
elif age_hours >= 4:
    print(f'STALE SIGNAL: investigate-gate.json for {ticket} has not been updated in {age_hours:.1f}h (source: {age_source}).')
    print(f'If the task is still active, update lastUpdated in the signal file.')
    print(f'If investigation is complete and task is done, archive: post to ticket, then rm the file.')
" 2>/dev/null || true)

if [ -n "$DECAY_WARN" ]; then
    cat <<EOF
<investigate-gate>
$DECAY_WARN
</investigate-gate>
EOF
fi

# Level 3: Disposition validation (Sagan assumption universe enforcement).
# Checks that verifiedShapes entries include a dispositions array with
# valid PROBED/ATTESTED/SKIPPED entries. V1 signal files (no dispositions
# on any entry) get a warning, not a block.
DISP_RESULT=$(python3 -c "
import json, sys, os

try:
    data = json.load(open('$INVESTIGATE_GATE'))
except Exception as e:
    print(f'WARN: investigate-gate.json malformed: {e}')
    sys.exit(0)

shapes = data.get('verifiedShapes', [])
if not shapes:
    sys.exit(0)

VALID_LAYERS = {'physical', 'schematic', 'semantic', 'operational', 'correctness'}
VALID_DISPOSITIONS = {'PROBED', 'ATTESTED', 'SKIPPED'}
CODE_EXTENSIONS = {'.py', '.sql', '.sh', '.js', '.ts', '.jsx', '.tsx', '.java', '.scala', '.go', '.rs', '.rb'}
TRIVIAL_SKIP_PHRASES = {
    '', 'n/a', 'na', 'n.a.', 'n.a',
    'not applicable', 'not relevant', 'not needed',
    'trivial', 'obvious', 'skip', 'skipped', 'no',
}
MIN_SKIP_REASON_LEN = 20

has_any_dispositions = False
v1_count = 0
errors = []
warnings = []

for shape in shapes:
    entity = shape.get('entity', '(unnamed)')
    filepath = shape.get('file', '')
    disps = shape.get('dispositions')

    if disps is None:
        v1_count += 1
        continue

    has_any_dispositions = True

    if not isinstance(disps, list) or len(disps) == 0:
        errors.append(f'{entity}: dispositions must be a non-empty array')
        continue

    is_code = any(filepath.endswith(ext) for ext in CODE_EXTENSIONS) if filepath else False
    layers_present = set()
    has_probed_or_attested = False

    for i, d in enumerate(disps):
        layer = d.get('layer', '')
        disposition = d.get('disposition', '')
        prefix = f'{entity}[{i}]'

        if layer not in VALID_LAYERS:
            errors.append(f'{prefix}: invalid layer {layer!r} (expected one of {sorted(VALID_LAYERS)})')
        else:
            layers_present.add(layer)

        if disposition not in VALID_DISPOSITIONS:
            errors.append(f'{prefix}: invalid disposition {disposition!r} (expected one of {sorted(VALID_DISPOSITIONS)})')
            continue

        if disposition == 'PROBED':
            has_probed_or_attested = True
            for field in ('probe', 'result', 'threshold'):
                if not d.get(field):
                    errors.append(f'{prefix}: PROBED requires {field!r} field')

        elif disposition == 'ATTESTED':
            has_probed_or_attested = True
            for field in ('source', 'value'):
                if not d.get(field):
                    errors.append(f'{prefix}: ATTESTED requires {field!r} field')

        elif disposition == 'SKIPPED':
            reason = (d.get('skipReason') or '').strip()
            if reason.lower() in TRIVIAL_SKIP_PHRASES:
                errors.append(f'{prefix}: SKIPPED reason {reason!r} is in the trivial-phrases blocklist')
            elif len(reason) < MIN_SKIP_REASON_LEN:
                errors.append(f'{prefix}: SKIPPED reason ({len(reason)} chars) < {MIN_SKIP_REASON_LEN} char minimum')

    if not has_probed_or_attested:
        errors.append(f'{entity}: all dispositions are SKIPPED -- at least one must be PROBED or ATTESTED')

    if is_code:
        for required in ('schematic', 'semantic'):
            if required not in layers_present:
                errors.append(f'{entity}: code entity missing required {required!r} layer')

# If ALL entries are v1 (no dispositions anywhere), warn but don't block.
if v1_count == len(shapes):
    print(f'WARN: signal file uses v1 schema (no dispositions on any of {len(shapes)} entries).')
    print('Disposition enforcement skipped. Update to v2 schema for full Sagan enforcement.')
    sys.exit(0)

# Mixed v1/v2 entries: warn about v1 entries.
if v1_count > 0:
    warnings.append(f'{v1_count} of {len(shapes)} entries have no dispositions (v1 schema)')

# Tier escalation check: if tier is "focused" but entities span 3+ directories,
# the investigation scope exceeds what Focused tier covers.
tier = data.get('tier', 'unknown')
if tier == 'focused':
    dirs = set()
    for shape in shapes:
        fp = shape.get('file', '')
        if fp:
            parts = fp.rsplit('/', 1)
            dirs.add(parts[0] if len(parts) > 1 else '.')
    if len(dirs) >= 3:
        warnings.append(
            f'Focused tier declared but entities span {len(dirs)} directories: '
            f'{sorted(dirs)}. Consider escalating to Full tier.'
        )

if errors:
    print(f'DISPOSITION ERRORS ({len(errors)}):')
    for e in errors:
        print(f'  {e}')
    print()
    print('Expected disposition shape:')
    print('  PROBED:   {\"layer\": \"...\", \"disposition\": \"PROBED\", \"assumption\": \"...\", \"probe\": \"<cmd>\", \"result\": \"<output>\", \"threshold\": \"PASS\"}')
    print('  ATTESTED: {\"layer\": \"...\", \"disposition\": \"ATTESTED\", \"assumption\": \"...\", \"source\": \"<file:line>\", \"value\": \"<verbatim>\"}')
    print('  SKIPPED:  {\"layer\": \"...\", \"disposition\": \"SKIPPED\", \"assumption\": \"...\", \"skipReason\": \"<>=20 chars, non-trivial>\"}')
    print()
    print('Rules:')
    print('  - Every entity needs at least one PROBED or ATTESTED disposition')
    print('  - Code entities (.py/.sql/.sh/etc) require schematic + semantic layers')
    print('  - SKIPPED reasons must be >= 20 chars and not in the trivial-phrases list')
    print(f'  - Trivial phrases: {sorted(TRIVIAL_SKIP_PHRASES - {\"\"})}')

if warnings:
    for w in warnings:
        print(f'WARN: {w}')
" 2>&1)

if [ -n "$DISP_RESULT" ]; then
    cat <<EOF
<investigate-gate>
$DISP_RESULT
</investigate-gate>
EOF
fi

exit 0
