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
SIGNAL_FILE="${CLAUDE_THINK_GATE:-$WORKSPACE_ROOT/think-gate.json}"

if [ ! -f "$SIGNAL_FILE" ]; then
    exit 0
fi

RESULT=$(python3 -c "
import json, sys, os, glob

signal_path = '$SIGNAL_FILE'
workspace = '$WORKSPACE_ROOT'

try:
    data = json.load(open(signal_path))
except Exception:
    sys.exit(0)

status = data.get('status', '')
if status in ('disposed', 'done-awaiting-pr'):
    sys.exit(0)

task = data.get('task', data.get('ticket', 'unknown'))
warnings = []

# Scan common artifact locations
plan_dirs = []

# Session plans (Craft Agent)
craft_plans = os.environ.get('CRAFT_AGENT_PLANS_PATH', '')
if craft_plans and os.path.isdir(craft_plans):
    plan_dirs.append(craft_plans)

# Repo plans/
repo_plans = os.path.join(workspace, 'plans')
if os.path.isdir(repo_plans):
    plan_dirs.append(repo_plans)

# Session-local plans in workspace
for d in glob.glob(os.path.join(workspace, 'sessions/*/plans')):
    if os.path.isdir(d):
        plan_dirs.append(d)

def find_artifact(patterns):
    for d in plan_dirs:
        for p in patterns:
            matches = glob.glob(os.path.join(d, p))
            if matches:
                return matches[0]
    return None

# 1. Investigation artifact
invest_patterns = ['fact-sheet*', 'investigate*', 'investigation*', 'Fact-Sheet*']
invest = find_artifact(invest_patterns)
if not invest:
    warnings.append(
        'INVESTIGATE: No investigation artifact found.\\n'
        '  Produce a Fact Sheet before writing code.\\n'
        '  Expected: plans/fact-sheet-*.md or plans/investigate-*.md\\n'
        '  Read: skills/thinking/investigate/SKILL.md'
    )

# 2. Pre-mortem artifact
premortem_patterns = ['pre-mortem*', 'premortem*', 'risk*', 'Pre-mortem*']
premortem = find_artifact(premortem_patterns)
if not premortem:
    warnings.append(
        'PRE-MORTEM: No pre-mortem artifact found.\\n'
        '  Classify risks before writing code.\\n'
        '  Expected: plans/pre-mortem-*.md or plans/risk-*.md\\n'
        '  Read: skills/thinking/pre-mortem/SKILL.md'
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

if not warnings:
    found = []
    if invest:
        found.append(f'investigate: {os.path.basename(invest)}')
    if premortem:
        found.append(f'pre-mortem: {os.path.basename(premortem)}')
    print(f'Pipeline for {task}: artifacts present ({', '.join(found)}).')
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
