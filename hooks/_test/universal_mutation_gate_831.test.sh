#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$ROOT/hooks/bash/universal-mutation-gate.sh"
RESOLVER="$ROOT/hooks/lib/resolve-think-gate.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

SESSION_ID="260525-long-swan"
TICKET="R11-meta remediation PR B+C combined (fallback execution after 3x spawn orphan)"
OLD_TICKET="siege-analytics/claude-configs-public#718"
WS="$TMP/workspace"
REPO="$TMP/repo"
mkdir -p "$WS/sessions/$SESSION_ID" "$WS/plans" "$REPO"

git -C "$REPO" init -q
git -C "$REPO" config user.email test@example.com
git -C "$REPO" config user.name Test
git -C "$REPO" remote add origin git@github.com:siege-analytics/test-repo.git
printf 'x\n' > "$REPO/file.txt"
git -C "$REPO" add file.txt
git -C "$REPO" commit -q -m 'baseline'

payload() {
  printf '{"tool_input":{"command":"%s"},"cwd":"%s"}\n' "$1" "$REPO"
}

write_json() {
  local path="$1"
  shift
  python3 - "$path" "$@" <<'PY'
import json, sys
path = sys.argv[1]
data = json.loads(sys.argv[2])
open(path, 'w').write(json.dumps(data, indent=2) + '\n')
PY
}

write_current_workspace_artifacts() {
  write_json "$WS/investigate-gate-repo.json" "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"findings\": [{\"id\": \"F1\"}]}"
  write_json "$WS/junior-senior-gate-repo.json" "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"junior_found\": true, \"senior_found\": true}"
  write_json "$WS/artifacts-posted-gate-repo.json" "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"investigate_posted\": true, \"premortem_posted\": true}"
  cat > "$WS/plans/pre-mortem-current.md" <<EOF2
# Pre-mortem

Ticket: $TICKET

### Tiger 1
Severity: LOW
Mitigation: fixture current artifact.
EOF2
}

write_stale_session_artifacts() {
  write_json "$WS/sessions/$SESSION_ID/investigate-gate.json" "{\"ticket\": \"$OLD_TICKET\", \"task\": \"old\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"findings\": [{\"id\": \"OLD\"}]}"
  write_json "$WS/sessions/$SESSION_ID/junior-senior-gate.json" "{\"ticket\": \"$OLD_TICKET\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"junior_found\": true, \"senior_found\": true}"
  write_json "$WS/sessions/$SESSION_ID/artifacts-posted-gate.json" "{\"ticket\": \"$OLD_TICKET\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"investigate_posted\": true, \"premortem_posted\": true}"
}

write_json "$WS/sessions/$SESSION_ID/think-gate.json" "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SESSION_ID\", \"session\": \"$SESSION_ID\", \"status\": \"implementing\", \"repo_root\": \"$REPO\"}"
write_stale_session_artifacts
write_current_workspace_artifacts

known="$(CRAFT_SESSION_ID="$SESSION_ID" python3 "$RESOLVER" --workspace "$WS" --session-known)"
if [[ "$known" != "1" ]]; then
  echo "FAIL: --session-known should return 1 with CRAFT_SESSION_ID" >&2
  exit 1
fi

many="$(CRAFT_SESSION_ID="$SESSION_ID" python3 "$RESOLVER" --workspace "$WS" --repo-root "$REPO" --resolve-many investigate-gate,junior-senior-gate,artifacts-posted-gate)"
if grep -q "$WS/sessions/$SESSION_ID" <<<"$many"; then
  echo "$many" >&2
  echo "FAIL: stale wrong-ticket session artifacts should not shadow current workspace repo-scoped artifacts" >&2
  exit 1
fi
if ! grep -q 'investigate-gate-repo.json' <<<"$many"; then
  echo "$many" >&2
  echo "FAIL: current workspace repo-scoped artifacts should be selected" >&2
  exit 1
fi

if ! out="$(CRAFT_SESSION_ID="$SESSION_ID" CRAFT_AGENT_WORKSPACE="$WS" bash "$HOOK" <<<"$(payload 'git checkout -b feature/test')" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: mutation should pass when stale session artifacts exist but current workspace artifacts match the task" >&2
  exit 1
fi

rm -f "$WS"/*-repo.json "$WS/plans/pre-mortem-current.md"
if out="$(CRAFT_SESSION_ID="$SESSION_ID" CRAFT_AGENT_WORKSPACE="$WS" bash "$HOOK" <<<"$(payload 'git checkout -b feature/test2')" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: mutation should block when only stale wrong-ticket session artifacts exist" >&2
  exit 1
fi
if ! grep -q 'artifacts missing or wrong ticket' <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: expected missing-artifacts diagnostic" >&2
  exit 1
fi

# Generic no-ticket session artifacts must not satisfy a current task.
write_json "$WS/sessions/$SESSION_ID/investigate-gate.json" "{\"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"findings\": [{\"id\": \"GENERIC\"}]}"
write_json "$WS/sessions/$SESSION_ID/junior-senior-gate.json" "{\"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"junior_found\": true, \"senior_found\": true}"
write_json "$WS/sessions/$SESSION_ID/artifacts-posted-gate.json" "{\"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$REPO\", \"investigate_posted\": true, \"premortem_posted\": true}"
if out="$(CRAFT_SESSION_ID="$SESSION_ID" CRAFT_AGENT_WORKSPACE="$WS" bash "$HOOK" <<<"$(payload 'git checkout -b feature/test3')" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: generic session artifacts without ticket/task should not authorize current-task mutation" >&2
  exit 1
fi

# Generic workspace-root artifacts must not authorize mutation either.
rm -f "$WS/sessions/$SESSION_ID/"{investigate-gate,junior-senior-gate,artifacts-posted-gate}.json
write_json "$WS/investigate-gate.json" "{\"status\": \"complete\", \"findings\": [{\"id\": \"GLOBAL\"}]}"
write_json "$WS/junior-senior-gate.json" "{\"status\": \"complete\", \"junior_found\": true, \"senior_found\": true}"
write_json "$WS/artifacts-posted-gate.json" "{\"status\": \"complete\", \"investigate_posted\": true, \"premortem_posted\": true}"
if out="$(CRAFT_SESSION_ID="$SESSION_ID" CRAFT_AGENT_WORKSPACE="$WS" bash "$HOOK" <<<"$(payload 'git checkout -b feature/test4')" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: generic workspace-root artifacts should not authorize current-task mutation" >&2
  exit 1
fi
rm -f "$WS/"{investigate-gate,junior-senior-gate,artifacts-posted-gate}.json

# Same-basename different repositories must not match by basename alone.
OTHER_PARENT="$TMP/other"
OTHER="$OTHER_PARENT/repo"
mkdir -p "$OTHER"
git -C "$OTHER" init -q
git -C "$OTHER" config user.email other@example.com
git -C "$OTHER" config user.name Other
git -C "$OTHER" remote add origin git@github.com:siege-analytics/other-repo.git
printf 'y\n' > "$OTHER/file.txt"
git -C "$OTHER" add file.txt
git -C "$OTHER" commit -q -m 'baseline other'
write_json "$WS/investigate-gate-repo.json" "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$OTHER\", \"findings\": [{\"id\": \"OTHER\"}]}"
write_json "$WS/junior-senior-gate-repo.json" "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$OTHER\", \"junior_found\": true, \"senior_found\": true}"
write_json "$WS/artifacts-posted-gate-repo.json" "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SESSION_ID\", \"status\": \"complete\", \"repo_root\": \"$OTHER\", \"investigate_posted\": true, \"premortem_posted\": true}"
cat > "$WS/plans/pre-mortem-current.md" <<EOF2
# Pre-mortem

Ticket: $TICKET

### Tiger 1
Severity: LOW
Mitigation: fixture current artifact.
EOF2
if out="$(CRAFT_SESSION_ID="$SESSION_ID" CRAFT_AGENT_WORKSPACE="$WS" bash "$HOOK" <<<"$(payload 'git checkout -b feature/test5')" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: same-basename different repo artifacts should not authorize mutation" >&2
  exit 1
fi

echo "universal_mutation_gate_831.test: PASS"
