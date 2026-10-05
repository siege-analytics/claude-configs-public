#!/usr/bin/env bash
# Test: project-scoped gate resolution (#892 FU2, defect D2 completion).
# find_gate_for_repo consults <gate>-<project-slug>.json (project from
# resolve_project) after the repo-slug file and before the umbrella singleton.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RESOLVER="$ROOT/hooks/lib/resolve-think-gate.py"

_PASS=0; _FAIL=0; _FAILED=()
check() {
    local name="$1" want="$2" got="$3"
    if [[ "$got" == "$want" ]]; then
        _PASS=$((_PASS+1)); printf '  [PASS] %s\n' "$name"
    else
        _FAIL=$((_FAIL+1)); _FAILED+=("$name"); printf '  [FAIL] %s (want "%s", got "%s")\n' "$name" "$want" "$got"
    fi
}

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# Workspace declaring a project 'demo' -> repo demo/app.
mkdir -p "$TMP/ws/projects/demo"
cat > "$TMP/ws/projects/demo/PROJECT.md" <<'MD'
---
name: demo
repo: demo/app
owners:
  - x@y.test
---
MD

# A repo whose origin matches the demo project.
mkdir -p "$TMP/app"
git -C "$TMP/app" init -q -b main
git -C "$TMP/app" remote add origin git@github.com:demo/app.git

# Resolve --repo-root and print the resolved gate's ticket (or NONE), with all
# session env unset so we exercise the workspace-file tiers, not a session dir.
ticket_for() {
    env -u CRAFT_SESSION_ID -u CLAUDE_SESSION_ID -u CCP_HOOK_INPUT_JSON \
        python3 "$RESOLVER" --workspace "$TMP/ws" --repo-root "$1" 2>/dev/null \
    | python3 -c 'import json,sys
d=sys.stdin.read().strip()
print(json.loads(d)["data"]["ticket"] if d and d!="null" else "NONE")' 2>/dev/null
}

# Project-scoped gate present, no repo-slug gate -> project gate resolves.
cat > "$TMP/ws/think-gate-demo.json" <<JSON
{"ticket":"#project","status":"implementing","repo_root":"$TMP/app"}
JSON
check "project-scoped gate resolves for a repo in the project" "#project" "$(ticket_for "$TMP/app")"

# Repo-slug gate must WIN over the project gate (more specific).
cat > "$TMP/ws/think-gate-app.json" <<JSON
{"ticket":"#repo","status":"implementing","repo_root":"$TMP/app"}
JSON
check "repo-slug gate beats project gate" "#repo" "$(ticket_for "$TMP/app")"

# A repo in NO project must not pick up the project gate.
mkdir -p "$TMP/other"
git -C "$TMP/other" init -q -b main
git -C "$TMP/other" remote add origin git@github.com:someone/unrelated.git
check "repo in no project does not bind the project gate" "NONE" "$(ticket_for "$TMP/other")"

echo
if [[ $_FAIL -eq 0 ]]; then
    echo "Results: $_PASS passed, 0 failed"; exit 0
else
    echo "Results: $_PASS passed, $_FAIL failed"
    printf '  FAILED: %s\n' "${_FAILED[@]}"; exit 1
fi
