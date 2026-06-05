#!/bin/bash
# UserPromptSubmit hook — think-gate enforcement via falsifiable claims.
#
# Reads <workspace>/think-gate.json and verifies each claim against the
# codebase on every turn. Narrates findings to the agent/user.
#
# Signal file supports TWO claim schemas:
#
# Schema A (machine-verifiable):
#   {
#     "ticket": "#262",
#     "design_note": "https://github.com/.../issues/262#issuecomment-...",
#     "repo_root": "/absolute/path/to/repo",
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
# Schema B (prose-only — agent-written design claims):
#   {
#     "ticket": "owner/repo#NNN",
#     "task": "description",
#     "design_note_location": "ticket comment URL or 'inline'",
#     "status": "designing|implementing|reviewing|done-awaiting-pr|disposed",
#     "claims": [
#       {
#         "id": "C1",
#         "claim": "human-readable claim",
#         "falsifier": "what would disprove this"
#       }
#     ]
#   }
#
# Schema B claims cannot be machine-verified (no file+grep). The hook
# passes them with an advisory. Machine verification requires Schema A.
#
# The "status" field (Schema B) controls hook behavior:
#   "disposed" or "done-awaiting-pr" → no verification, just report status
#   anything else → verify claims if machine-verifiable
#
# Behavior:
#   No signal file       → inject "No design note registered"
#   All claims pass      → inject "Design for #N is current. Proceed."
#   Any claim fails      → inject "STALE DESIGN: [assertion] no longer holds"
#   Prose-only claims    → inject "Design for #N registered (prose claims, not machine-verified)"
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
# Support both schema field names
design_note = data.get('design_note') or data.get('design_note_location', 'not specified')
repo_root = data.get('repo_root', '') or '$WORKSPACE_ROOT'
claims = data.get('claims', [])
status = data.get('status', '')

# Status-based short-circuit (Schema B lifecycle)
if status in ('disposed', 'done-awaiting-pr'):
    disposition = data.get('disposition', '')
    msg = f'Design for {ticket}: status={status}.'
    if disposition:
        msg += f' Disposition: {disposition}'
    msg += ' No verification needed.'
    print(msg)
    sys.exit(0)

if not claims:
    print(f'Design for {ticket} registered but has no claims.')
    print(f'Design note: {design_note}')
    print('Proceed, but consider adding falsifiable claims.')
    sys.exit(0)

# Detect schema: Schema A has 'file'+'grep', Schema B has 'claim'+'falsifier'
def is_machine_verifiable(claim):
    return bool(claim.get('file')) and bool(claim.get('grep'))

def is_prose_only(claim):
    return bool(claim.get('claim') or claim.get('falsifier')) and not is_machine_verifiable(claim)

machine_claims = [c for c in claims if is_machine_verifiable(c)]
prose_claims = [c for c in claims if is_prose_only(c)]

# If ALL claims are prose-only, report and pass
if not machine_claims and prose_claims:
    print(f'Design for {ticket} registered ({len(prose_claims)} prose claim(s), not machine-verified).')
    print(f'Design note: {design_note}')
    print('Prose claims require manual verification. Proceed with awareness.')
    sys.exit(0)

# Verify machine-verifiable claims
failed = []
passed = []

for claim in machine_claims:
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

# Report prose claims as unverified addendum
if prose_claims:
    print(f'  (+ {len(prose_claims)} prose claim(s) not machine-verified)')

if failed:
    print()
    print(f'STALE DESIGN for {ticket}: {len(failed)} claim(s) no longer hold.')
    print(f'The premises of your design have changed. Re-examine the')
    print(f'design note at {design_note} before proceeding.')
    print(f'Reconcile the design, then update the signal or archive it (post disposition to ticket, then rm the file).')
else:
    total = len(passed) + len(prose_claims)
    print()
    print(f'Design for {ticket} is current ({len(passed)} verified, {len(prose_claims)} prose). Proceed.')
" 2>&1)

if [ -n "$RESULT" ]; then
    cat <<EOF
<think-gate>
$RESULT
</think-gate>
EOF
fi

# Level 1.5: Scope mismatch check.
# If the signal file's ticket doesn't match the current branch's ticket number,
# warn about stale/mismatched scope. Prevents a signal from ticket X giving a
# clean pass while working on ticket Y (#323).
SCOPE_WARN=""
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ -n "$BRANCH_NAME" ] && [ "$BRANCH_NAME" != "HEAD" ]; then
    SIGNAL_TICKET=$(python3 -c "
import json, re, sys
try:
    data = json.load(open('$SIGNAL_FILE'))
    raw = data.get('ticket', '')
    # Normalize: strip repo prefix, extract bare number or PROJ-NNN
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

    # Extract ticket number(s) from branch name
    BRANCH_TICKETS=$(echo "$BRANCH_NAME" | grep -oE '([0-9]+|[A-Z]+-[0-9]+)' || true)

    if [ -n "$SIGNAL_TICKET" ] && [ -n "$BRANCH_TICKETS" ]; then
        if ! echo "$BRANCH_TICKETS" | grep -qF "$SIGNAL_TICKET"; then
            # Format ticket: add # prefix only for bare numbers
            DISPLAY_TICKET="${SIGNAL_TICKET}"
            if echo "$SIGNAL_TICKET" | grep -qE '^[0-9]+$'; then DISPLAY_TICKET="#${SIGNAL_TICKET}"; fi
            SCOPE_WARN="SCOPE MISMATCH: think-gate.json is for ${DISPLAY_TICKET} but current branch is '${BRANCH_NAME}'.
To continue: update the signal file for the current task.
To archive: post disposition to the ticket, then rm think-gate.json.
A mismatched signal file cannot validate your current design."
        fi
    fi
fi

if [ -n "$SCOPE_WARN" ]; then
    cat <<EOF
<think-gate>
$SCOPE_WARN
</think-gate>
EOF
fi

# Level 1.75: Temporal decay check.
# Detects stale signal files based on lastUpdated timestamp or file mtime.
# Tiered warnings: 4h stale (active), 24h expired (active), 4h archive prompt (done).
# Ref: #328
DECAY_WARN=$(python3 -c "
import json, sys, os, time
from datetime import datetime, timezone

try:
    data = json.load(open('$SIGNAL_FILE'))
except:
    sys.exit(0)

status = data.get('status', '')
last_updated = data.get('lastUpdated', '')
ticket = data.get('ticket', 'unknown')

if last_updated:
    try:
        ts = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
        age_source = 'lastUpdated'
    except:
        age_seconds = time.time() - os.path.getmtime('$SIGNAL_FILE')
        age_source = 'file mtime (lastUpdated unparseable)'
else:
    age_seconds = time.time() - os.path.getmtime('$SIGNAL_FILE')
    age_source = 'file mtime (no lastUpdated field)'

age_hours = age_seconds / 3600

if status in ('disposed', 'done-awaiting-pr'):
    if age_hours >= 4:
        print(f'ARCHIVE PROMPT: think-gate.json for {ticket} has been {status} for {age_hours:.0f}h (source: {age_source}).')
        print(f'This signal is from a completed task. To archive:')
        print(f'  1. Verify disposition is posted to the ticket')
        print(f'  2. Delete the signal file: rm think-gate.json')
        print(f'Starting new work with a stale done signal causes scope mismatch warnings.')
elif age_hours >= 24:
    print(f'EXPIRED SIGNAL: think-gate.json for {ticket} has not been updated in {age_hours:.0f}h (source: {age_source}).')
    print(f'A signal older than 24h likely reflects an abandoned or interrupted task.')
    print(f'Re-examine the design note before continuing. Update lastUpdated after review.')
elif age_hours >= 4:
    print(f'STALE SIGNAL: think-gate.json for {ticket} has not been updated in {age_hours:.1f}h (source: {age_source}).')
    print(f'If the task is still active, update lastUpdated in the signal file.')
    print(f'If the task is complete, set status to done-awaiting-pr with a disposition.')
" 2>/dev/null || true)

if [ -n "$DECAY_WARN" ]; then
    cat <<EOF
<think-gate>
$DECAY_WARN
</think-gate>
EOF
fi

# Level 2: Design note structure check.
# If the design note is a local file, verify it contains key section headings.
# Warnings only — format varies by task complexity.
DESIGN_NOTE_PATH=$(python3 -c "
import json, sys
try:
    data = json.load(open('$SIGNAL_FILE'))
    note = data.get('design_note') or data.get('design_note_location') or data.get('design_note_path', '')
    print(note)
except:
    print('')
" 2>/dev/null || echo "")

if [ -n "$DESIGN_NOTE_PATH" ] && [ -f "$DESIGN_NOTE_PATH" ]; then
    STRUCTURE_WARNINGS=""
    HEADING_COUNT=$(grep -cE '^#{1,3} ' "$DESIGN_NOTE_PATH" || true)

    if [ "$HEADING_COUNT" -lt 2 ]; then
        STRUCTURE_WARNINGS="${STRUCTURE_WARNINGS}  - Design note has $HEADING_COUNT section heading(s); expected at least 2 (e.g., What + Risk)\n"
    fi

    HAS_WHAT=$(grep -ciE '^#{1,3} (what|context|problem|summary|approach)' "$DESIGN_NOTE_PATH" || true)
    HAS_RISK=$(grep -ciE '^#{1,3} (risk|what could go wrong|tradeoff|rollback|falsif)' "$DESIGN_NOTE_PATH" || true)
    HAS_PROPOSAL=$(grep -ciE '^#{1,3} (proposal|option|approach|design|layer|how)' "$DESIGN_NOTE_PATH" || true)

    if [ "$HAS_WHAT" -eq 0 ]; then
        STRUCTURE_WARNINGS="${STRUCTURE_WARNINGS}  - Missing context/problem section (expected heading like ## What, ## Context, ## Problem)\n"
    fi
    if [ "$HAS_RISK" -eq 0 ]; then
        STRUCTURE_WARNINGS="${STRUCTURE_WARNINGS}  - Missing risk section (expected heading like ## Risk, ## What could go wrong, ## Rollback)\n"
    fi
    if [ "$HAS_PROPOSAL" -eq 0 ]; then
        STRUCTURE_WARNINGS="${STRUCTURE_WARNINGS}  - Missing proposal/design section (expected heading like ## Proposals, ## Design, ## Approach)\n"
    fi

    if [ -n "$STRUCTURE_WARNINGS" ]; then
        printf '<think-gate>\nDesign note structure warnings for %s:\n%b\nThese are advisory — update the design note if sections are genuinely missing.\n</think-gate>\n' "$DESIGN_NOTE_PATH" "$STRUCTURE_WARNINGS"
    fi
fi

exit 0
