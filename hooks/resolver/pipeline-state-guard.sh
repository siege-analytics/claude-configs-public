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

HOOK_INPUT_JSON=$(cat 2>/dev/null || true)
export CCP_HOOK_INPUT_JSON="$HOOK_INPUT_JSON"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="${CRAFT_AGENT_WORKSPACE:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
# Task-scoped resolution: resolve the think gate for the CURRENT hook cwd/repo,
# not the first active gate anywhere in the workspace. Pipeline warnings for
# one task must not become workspace-global noise or blockers for another task.
RESOLVE_TG="$SCRIPT_DIR/../lib/resolve-think-gate.py"
REPO_ROOT=$(printf '%s' "$HOOK_INPUT_JSON" | python3 -c '
import json, sys, os, subprocess
try:
    data = json.loads(sys.stdin.read() or "{}")
    cwd = data.get("cwd") or os.getcwd()
except Exception:
    cwd = os.getcwd()
try:
    result = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
    print(result.stdout.strip() if result.returncode == 0 else cwd)
except Exception:
    print(cwd)
' 2>/dev/null || echo "$WORKSPACE_ROOT")
SIGNAL_FILE=""
if [[ -z "$SIGNAL_FILE" ]] && [[ -f "$RESOLVE_TG" ]]; then
    SIGNAL_FILE=$(python3 "$RESOLVE_TG" --workspace "$WORKSPACE_ROOT" --repo-root "$REPO_ROOT" --env-override "${CLAUDE_THINK_GATE:-}" | python3 -c "import json,sys
try:
    r=json.load(sys.stdin)
    print(r['path'] if r else '')
except Exception:
    print('')" 2>/dev/null || true)
fi

if [ ! -f "$SIGNAL_FILE" ]; then
    exit 0
fi

RESULT=$(python3 "$SCRIPT_DIR/../lib/pipeline_state.py" "$SIGNAL_FILE" "$WORKSPACE_ROOT" "$SCRIPT_DIR/../lib" 2>&1 || true)

if [ -n "$RESULT" ]; then
    cat <<EOF
<pipeline-gate>
$RESULT
</pipeline-gate>
EOF
fi

exit 0
