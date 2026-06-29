#!/bin/bash
# UserPromptSubmit hook -- enforce the artifact pipeline mid-flight.
#
# When a think-gate.json signal file is active (design in progress),
# this hook checks whether downstream artifacts exist:
#   1. Investigation artifact (fact sheet)
#   2. Pre-mortem artifact (risk classification)
#   3. Self-review artifact (when code changes are staged)
#
# Injects persistent warnings for each missing artifact. The warnings
# repeat every turn until the artifacts are produced. This closes the
# mid-pipeline gap (#255): between think (session start) and self-review
# (push time), investigation and pre-mortem were honor-system.
#
# Fail-open: if think-gate.json doesn't exist, exit silently (no
# pipeline active = nothing to enforce).
#
# Ref: claude-configs-public#255 (mid-pipeline gate)
# Ref: claude-configs-public#261 (PreToolUse workaround)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# Repo-scoped resolution (#494): check think-gate-*.json first, fall back to think-gate.json
RESOLVE_TG="$SCRIPT_DIR/../lib/resolve-think-gate.py"
SIGNAL_FILE="${CLAUDE_THINK_GATE:-}"
if [[ -z "$SIGNAL_FILE" ]] && [[ -f "$RESOLVE_TG" ]]; then
    SIGNAL_FILE=$(python3 "$RESOLVE_TG" --workspace "$WORKSPACE_ROOT" --all 2>/dev/null | python3 -c "
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
if [[ -z "$SIGNAL_FILE" ]]; then
    SIGNAL_FILE="$WORKSPACE_ROOT/think-gate.json"
fi

if [ ! -f "$SIGNAL_FILE" ]; then
    exit 0
fi

RESULT=$(python3 -c "
import json, sys, os, glob

signal_path = '$SIGNAL_FILE'
workspace = '$WORKSPACE_ROOT'

try:
    data = json.load(open(signal_path))
except Exception as e:
    print(f'WARN: think-gate.json is malformed ({e}). Pipeline enforcement skipped.')
    sys.exit(0)

status = data.get('status', '')
if status in ('disposed', 'done-awaiting-pr'):
    sys.exit(0)

task = data.get('task', data.get('ticket', 'unknown'))
current_ticket = data.get('ticket', '')
warnings = []

# Scan common artifact locations
plan_dirs = []

# Session plans (Craft Agent)
craft_plans = os.environ.get('CRAFT_AGENT_PLANS_PATH', '')
if craft_plans and os.path.isdir(craft_plans):
    plan_dirs.append(craft_plans)

# Workspace plans/
ws_plans = os.path.join(workspace, 'plans')
if os.path.isdir(ws_plans):
    plan_dirs.append(ws_plans)

# Repo plans/ (from think-gate.json repo_root field)
repo_root = data.get('repo_root', '')
if repo_root:
    repo_plans = os.path.join(repo_root, 'plans')
    if os.path.isdir(repo_plans) and repo_plans not in plan_dirs:
        plan_dirs.append(repo_plans)

# Session-local plans in workspace
for d in glob.glob(os.path.join(workspace, 'sessions/*/plans')):
    if os.path.isdir(d):
        plan_dirs.append(d)

def ticket_slug(ticket_ref):
    \"\"\"Extract repo#N from full ticket ref (e.g. 'siege-analytics/repo#123' -> '#123').\"\"\"
    if not ticket_ref:
        return ''
    if '#' in ticket_ref:
        return '#' + ticket_ref.split('#')[-1]
    return ticket_ref

def file_references_ticket(filepath, ticket_ref):
    \"\"\"Check if a file's content references the current ticket.\"\"\"
    if not ticket_ref:
        return True  # no ticket to check = pass
    try:
        content = open(filepath).read(4096)
    except Exception:
        return False
    slug = ticket_slug(ticket_ref)
    return ticket_ref in content or slug in content

import re as _re
def premortem_has_risks(filepath):
    try:
        content = open(filepath).read(8192)
    except Exception:
        return False
    lower = content.lower()
    return bool(
        'severity:' in lower
        or '**urgency:**' in lower
        or _re.search(r'(?:tiger|paper tiger|elephant)\s+\d', lower)
    )

def premortem_has_launch_blocker(filepath):
    try:
        content = open(filepath).read(8192)
    except Exception:
        return False
    lower = content.lower()
    return 'implementation may proceed: no' in lower or 'blocks-launch' in lower

def find_artifact(patterns, require_ticket=True):
    for d in plan_dirs:
        for p in patterns:
            matches = glob.glob(os.path.join(d, p))
            for m in sorted(matches):
                if require_ticket and current_ticket:
                    if file_references_ticket(m, current_ticket):
                        return m
                else:
                    return m
    return None

# 1. Investigation artifact
invest_patterns = ['fact-sheet*', 'investigate*', 'investigation*', 'Fact-Sheet*']
invest = find_artifact(invest_patterns)
# Also check investigate-gate.json (ticket association via JSON ticket field)
if not invest:
    invest_gate_path = os.path.join(workspace, 'investigate-gate.json')
    if os.path.isfile(invest_gate_path):
        try:
            ig = json.load(open(invest_gate_path))
            ig_ticket = ig.get('ticket', '')
            if ig_ticket == current_ticket or not current_ticket:
                invest = invest_gate_path
                if not ig.get('findings', []):
                    warnings.append(
                        f'INVESTIGATE: investigate-gate.json exists but has no findings FOR {current_ticket or \"current task\"}.\\n'
                        '  Add at least one finding before proceeding.\\n'
                        '  The mutation gate will block until findings are present.'
                    )
        except Exception:
            pass
if not invest:
    warnings.append(
        f'INVESTIGATE: No investigation artifact found FOR {current_ticket or \"current task\"}.\\n'
        '  Produce a Fact Sheet before writing code.\\n'
        '  Expected: plans/fact-sheet-*.md or plans/investigate-*.md (must reference current ticket)\\n'
        '  Read: skills/thinking/investigate/SKILL.md'
    )

# 2. Pre-mortem artifact
premortem_patterns = ['pre-mortem*', 'premortem*', 'risk*', 'Pre-mortem*']
premortem = find_artifact(premortem_patterns)
if not premortem:
    warnings.append(
        f'PRE-MORTEM: No pre-mortem artifact found FOR {current_ticket or \"current task\"}.\\n'
        '  Classify risks before writing code.\\n'
        '  Expected: plans/pre-mortem-*.md (must reference current ticket in ticket_refs)\\n'
        '  Read: skills/thinking/pre-mortem/SKILL.md'
    )
elif not premortem_has_risks(premortem):
    warnings.append(
        f'PRE-MORTEM: Pre-mortem artifact exists but has no classified risks FOR {current_ticket or \"current task\"}.\\n'
        '  Add at least one risk with Severity: or Tiger/Elephant classification.\\n'
        '  The mutation gate will block until risks are present.'
    )
elif premortem_has_launch_blocker(premortem):
    warnings.append(
        f'LAUNCH-BLOCKING TIGER: Pre-mortem ({os.path.basename(premortem)}) contains a Launch-Blocking Tiger.\\n'
        '  Implementation is halted until the Tiger is mitigated.\\n'
        '  Update the pre-mortem to remove Blocks-Launch status or set \"Implementation may proceed: YES\".\\n'
        '  The mutation gate will block until the Launch-Blocking Tiger is resolved.'
    )

# 3. Self-review artifact (only warn when code changes exist)
try:
    import subprocess
    staged = subprocess.run(
        ['git', '-C', workspace, 'diff', '--cached', '--name-only'],
        capture_output=True, text=True, timeout=5
    ).stdout.strip()
    unstaged = subprocess.run(
        ['git', '-C', workspace, 'diff', '--name-only'],
        capture_output=True, text=True, timeout=5
    ).stdout.strip()
    has_changes = bool(staged or unstaged)
except Exception:
    has_changes = False

if has_changes:
    review_patterns = ['self-review*', 'review*', 'Self-review*']
    review = find_artifact(review_patterns)
    if not review:
        warnings.append(
            'SELF-REVIEW: Code changes detected but no self-review artifact.\\n'
            '  Before pushing, produce a self-review artifact.\\n'
            '  Expected: plans/self-review-*.md\\n'
            '  Read: skills/self-review/SKILL.md'
        )

# 4. Pre-implementation comprehension check (#489 component A).
# When status is 'implementing', check the ticket for Junior's task
# description with the 5 required elements.
if status == 'implementing' and current_ticket:
    junior_found = False
    senior_found = False
    junior_stems = [
        'current behavior', 'intended behavior', 'steps to get there',
        'success criteria', 'what could go wrong',
    ]
    senior_stems = [
        'hasty mistakes', 'observable behavior', 'over-focusing',
        'leave out', 'prior work', 'right environment',
        'failure case', 'instance or class', 'done match',
        'skip if nobody',
    ]
    try:
        # Extract owner/repo and issue number from ticket ref.
        if '#' in current_ticket:
            parts = current_ticket.split('#')
            issue_num = parts[-1]
            repo_slug = parts[0].rstrip('/') if len(parts) > 1 and parts[0] else ''
        else:
            issue_num = current_ticket
            repo_slug = ''

        if issue_num.isdigit():
            if repo_slug:
                api_path = f'repos/{repo_slug}/issues/{issue_num}/comments'
            else:
                api_path = f'repos/siege-analytics/claude-configs-public/issues/{issue_num}/comments'

            result = subprocess.run(
                ['gh', 'api', api_path, '--paginate', '-q', '.[].body'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                comments = result.stdout.lower()
                junior_hits = sum(1 for s in junior_stems if s in comments)
                if junior_hits >= 3:
                    junior_found = True

                senior_hits = sum(1 for s in senior_stems if s in comments)
                if senior_hits >= 5:
                    senior_found = True
    except Exception:
        pass

    if not junior_found:
        warnings.append(
            f'PRE-IMPLEMENTATION COMPREHENSION: No Junior task description found on {current_ticket}.\\n'
            '  Before writing code, post a maximal description with:\\n'
            '  1. Current behavior (with evidence)\\n'
            '  2. Intended behavior (observable, not code-to-write)\\n'
            '  3. Steps to get there\\n'
            '  4. Success criteria (testable in target environment)\\n'
            '  5. What could go wrong\\n'
            '  Read: skills/self-review/SKILL.md (Pre-implementation comprehension)'
        )

    # 5. Senior adversarial checklist (#489 component B).
    if not senior_found:
        warnings.append(
            f'SENIOR ADVERSARIAL CHECKLIST: No Senior checklist response found on {current_ticket}.\\n'
            '  After the Junior posts the task description, the Senior must run\\n'
            '  the 10 presumptive questions and post responses on the ticket.\\n'
            '  Read: skills/self-review/SKILL.md (Senior adversarial checklist)'
        )

    # Write junior-senior-gate.json signal file (#492)
    # The mutation gate reads this to block when Junior/Senior are missing.
    import datetime
    gate_data = {
        'ticket': current_ticket,
        'junior_found': junior_found,
        'senior_found': senior_found,
        'lastChecked': datetime.datetime.now().astimezone().isoformat(),
    }
    gate_path = os.path.join(workspace, 'junior-senior-gate.json')
    try:
        with open(gate_path, 'w') as f:
            json.dump(gate_data, f, indent=2)
            f.write('\\n')
    except Exception:
        pass

if not warnings:
    found = []
    if invest:
        found.append(f'investigate: {os.path.basename(invest)}')
    if premortem:
        found.append(f'pre-mortem: {os.path.basename(premortem)}')
    summary = ', '.join(found)
    print(f'Pipeline for {task}: artifacts present ({summary}).')
    if status == 'implementing':
        print('Slow is smooth: what have you not yet verified about the deployed state?')
else:
    print(f'Pipeline for {task}: {len(warnings)} artifact(s) missing.')
    print()
    for w in warnings:
        print(w)
        print()
    print('These warnings repeat every turn until the artifacts are produced.')
    print('If this work is trivial, archive think-gate.json to silence them.')
" 2>&1)

if [ -n "$RESULT" ]; then
    cat <<EOF
<pipeline-gate>
$RESULT
</pipeline-gate>
EOF
fi

exit 0
