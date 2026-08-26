#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
RESOLVER="$ROOT/hooks/lib/resolve-think-gate.py"
STANDING="$ROOT/hooks/resolver/standing-order-guard.sh"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/sessions/session-a" "$TMP/repo" "$TMP/hooks/resolver"
cp "$STANDING" "$TMP/hooks/resolver/standing-order-guard.sh"
TMP_STANDING="$TMP/hooks/resolver/standing-order-guard.sh"

cat >"$TMP/think-gate.json" <<'JSON'
{"ticket":"#root","repo_root":"/tmp/not-this-repo","status":"implementing"}
JSON
cat >"$TMP/sessions/session-a/think-gate.json" <<JSON
{"ticket":"#session","repo_root":"$TMP/repo","status":"implementing"}
JSON

resolved=$(CRAFT_AGENT_SESSION_ID=session-a python3 "$RESOLVER" --workspace "$TMP" --repo-root "$TMP/repo" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["ticket"])')
if [[ "$resolved" == "#session" ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] session think-gate beats workspace root (exit 0)\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("session think-gate beats workspace root")
  printf '  [FAIL] session think-gate beats workspace root (got %s)\n' "$resolved"
fi

resolved_from_hook_json=$(CCP_HOOK_INPUT_JSON='{"sessionId":"session-a"}' python3 "$RESOLVER" --workspace "$TMP" --repo-root "$TMP/repo" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["ticket"])')
if [[ "$resolved_from_hook_json" == "#session" ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] hook JSON session id beats workspace root (exit 0)\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("hook JSON session id beats workspace root")
  printf '  [FAIL] hook JSON session id beats workspace root (got %s)\n' "$resolved_from_hook_json"
fi

cat >"$TMP/standing-order.json" <<'JSON'
{"active":true,"deadline":"2099-01-01T00:00:00Z","directive":"ROOT DIRECTIVE","work_queue":["root"]}
JSON
cat >"$TMP/sessions/session-a/standing-order.json" <<'JSON'
{"active":true,"deadline":"2099-01-01T00:00:00Z","directive":"SESSION DIRECTIVE","work_queue":["session"]}
JSON

out=$(CLAUDE_SIGNAL_DIR="$TMP/sessions/session-a" bash "$STANDING" 2>&1)
if echo "$out" | grep -q "SESSION DIRECTIVE" && ! echo "$out" | grep -q "ROOT DIRECTIVE"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] session standing-order beats workspace root (exit 0)\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("session standing-order beats workspace root")
  printf '  [FAIL] session standing-order beats workspace root\n'
  printf '         output: %s\n' "${out:0:300}"
fi

out=$(printf '%s' '{"sessionId":"session-a"}' | env -u CLAUDE_SIGNAL_DIR -u CRAFT_AGENT_SIGNAL_DIR -u CRAFT_AGENT_SESSION_DIR -u CLAUDE_SESSION_DIR -u CRAFT_AGENT_SESSION_ID -u CLAUDE_SESSION_ID -u SESSION_ID bash "$TMP_STANDING" 2>&1)
if echo "$out" | grep -q "SESSION DIRECTIVE" && ! echo "$out" | grep -q "ROOT DIRECTIVE"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] standing-order hook JSON session id beats workspace root (exit 0)\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("standing-order hook JSON session id beats workspace root")
  printf '  [FAIL] standing-order hook JSON session id beats workspace root\n'
  printf '         output: %s\n' "${out:0:300}"
fi

report
