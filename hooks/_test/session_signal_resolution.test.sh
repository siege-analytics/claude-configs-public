#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
RESOLVER="$ROOT/hooks/lib/resolve-think-gate.py"
STANDING="$ROOT/hooks/resolver/standing-order-guard.sh"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/sessions/session-a" "$TMP/repo" "$TMP/foreign-repo" "$TMP/hooks"
cp -R "$ROOT/hooks/lib" "$TMP/hooks/lib"
mkdir -p "$TMP/hooks/resolver" "$TMP/hooks/bash"
cp "$STANDING" "$TMP/hooks/resolver/standing-order-guard.sh"
cp "$ROOT/hooks/resolver/investigate-gate-guard.sh" "$TMP/hooks/resolver/investigate-gate-guard.sh"
cp "$ROOT/hooks/resolver/pipeline-state-guard.sh" "$TMP/hooks/resolver/pipeline-state-guard.sh"
cp "$ROOT/hooks/bash/universal-mutation-gate.sh" "$TMP/hooks/bash/universal-mutation-gate.sh"
TMP_STANDING="$TMP/hooks/resolver/standing-order-guard.sh"
TMP_INVESTIGATE="$TMP/hooks/resolver/investigate-gate-guard.sh"
TMP_PIPELINE="$TMP/hooks/resolver/pipeline-state-guard.sh"
TMP_MUTATION="$TMP/hooks/bash/universal-mutation-gate.sh"

git -C "$TMP/repo" init -q -b main
git -C "$TMP/repo" config user.email "t@example.test"
git -C "$TMP/repo" config user.name "test"
printf 'seed\n' > "$TMP/repo/file.txt"
git -C "$TMP/repo" add file.txt
git -C "$TMP/repo" commit -q --no-verify -m seed

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

# Cross-session --all contamination: a brand-new session with NO gate of
# its own must not inherit a foreign session's stale, non-terminal
# workspace-root think-gate. Reproduces a bug where a foreign session's
# think-gate-<slug>.json got picked up by --all for every other session
# in a shared workspace and blocked their Bash calls on an unrelated
# ticket's missing artifacts.
cat >"$TMP/think-gate-foreign.json" <<'JSON'
{"ticket":"#foreign","repo_root":"/tmp/foreign-repo","status":"implementing","session":"session-foreign"}
JSON

resolved_all_new_session=$(CRAFT_AGENT_SESSION_ID=session-brand-new python3 "$RESOLVER" --workspace "$TMP" --all 2>/dev/null | python3 -c '
import json, sys
gates = json.load(sys.stdin)
tickets = [g["data"].get("ticket") for g in gates]
print(",".join(tickets) if tickets else "NONE")
')
if [[ "$resolved_all_new_session" != *"#foreign"* ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] new session --all does not inherit foreign session think-gate\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("new session --all does not inherit foreign session think-gate")
  printf '  [FAIL] new session --all does not inherit foreign session think-gate (got: %s)\n' "$resolved_all_new_session"
fi

# The owning session's own --all resolution must still see its gate.
resolved_all_owning_session=$(CRAFT_AGENT_SESSION_ID=session-foreign python3 "$RESOLVER" --workspace "$TMP" --all 2>/dev/null | python3 -c '
import json, sys
gates = json.load(sys.stdin)
tickets = [g["data"].get("ticket") for g in gates]
print(",".join(tickets) if tickets else "NONE")
')
if [[ "$resolved_all_owning_session" == *"#foreign"* ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] owning session --all still sees its own workspace-root think-gate\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("owning session --all still sees its own workspace-root think-gate")
  printf '  [FAIL] owning session --all still sees its own workspace-root think-gate (got: %s)\n' "$resolved_all_owning_session"
fi

# Task-scoped prompt gates: a workspace-root singleton for a different repo must
# not make the current repo look like it has an active design/investigation
# pipeline. This is the prompt-gate version of the cross-session contamination
# bug: warnings are allowed for the owning task only, not as workspace-global
# state for every session.
cat >"$TMP/think-gate.json" <<JSON
{"ticket":"#foreign-root","repo_root":"$TMP/foreign-repo","status":"implementing"}
JSON
payload_current_repo=$(printf '{"cwd":"%s","tool_input":{"command":"user prompt"}}' "$TMP/repo")

out=$(printf '%s' "$payload_current_repo" | CRAFT_AGENT_SESSION_ID=session-brand-new bash "$TMP_INVESTIGATE" 2>&1)
if [[ -z "$out" ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] investigate gate ignores foreign workspace-root think-gate\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("investigate gate ignores foreign workspace-root think-gate")
  printf '  [FAIL] investigate gate used foreign workspace-root think-gate\n'
  printf '         output: %s\n' "${out:0:300}"
fi

out=$(printf '%s' "$payload_current_repo" | CRAFT_AGENT_SESSION_ID=session-brand-new bash "$TMP_PIPELINE" 2>&1)
if [[ -z "$out" ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] pipeline gate ignores foreign workspace-root think-gate\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("pipeline gate ignores foreign workspace-root think-gate")
  printf '  [FAIL] pipeline gate used foreign workspace-root think-gate\n'
  printf '         output: %s\n' "${out:0:300}"
fi

# Current-task gates still fire: once the workspace singleton belongs to the
# current repo, investigate-gate should surface the missing investigation for
# that task.
cat >"$TMP/think-gate.json" <<JSON
{"ticket":"#current","repo_root":"$TMP/repo","status":"implementing"}
JSON
out=$(printf '%s' "$payload_current_repo" | CRAFT_AGENT_SESSION_ID=session-brand-new bash "$TMP_INVESTIGATE" 2>&1)
if echo "$out" | grep -q "INVESTIGATION REQUIRED" && echo "$out" | grep -q "#current"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] investigate gate still warns for current-task missing investigation\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("investigate gate still warns for current-task missing investigation")
  printf '  [FAIL] investigate gate did not warn for current task\n'
  printf '         output: %s\n' "${out:0:300}"
fi

mutation_payload=$(printf '{"cwd":"%s","tool_input":{"command":"git commit -m x"}}' "$TMP/repo")
cat >"$TMP/think-gate.json" <<JSON
{"ticket":"#foreign-root","repo_root":"$TMP/foreign-repo","status":"implementing"}
JSON
out=$(printf '%s' "$mutation_payload" | CRAFT_AGENT_WORKSPACE="$TMP" CRAFT_AGENT_SESSION_ID=session-brand-new bash "$TMP_MUTATION" 2>&1)
code=$?
if [[ "$code" -eq 2 ]] && echo "$out" | grep -q "no valid think-gate" && ! echo "$out" | grep -q "#foreign-root"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] mutation gate does not use foreign workspace-root gate as current task\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("mutation gate does not use foreign workspace-root gate as current task")
  printf '  [FAIL] mutation gate used or reported foreign gate unexpectedly (exit %s)\n' "$code"
  printf '         output: %s\n' "${out:0:400}"
fi

# Same repo but foreign session is the sharper task-scoping case. A local
# .think-gate.json from another session must not be revived after resolver
# rejection by prompt gates or mutation gates.
rm -f "$TMP/think-gate.json"
cat >"$TMP/repo/.think-gate.json" <<JSON
{"ticket":"#same-repo-foreign-session","repo_root":"$TMP/repo","session":"session-other","status":"implementing"}
JSON
out=$(printf '%s' "$payload_current_repo" | CRAFT_AGENT_SESSION_ID=session-brand-new bash "$TMP_INVESTIGATE" 2>&1)
if [[ -z "$out" ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] investigate gate ignores same-repo foreign-session local gate\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("investigate gate ignores same-repo foreign-session local gate")
  printf '  [FAIL] investigate gate used same-repo foreign-session local gate\n'
  printf '         output: %s\n' "${out:0:300}"
fi

out=$(printf '%s' "$payload_current_repo" | CRAFT_AGENT_SESSION_ID=session-brand-new CLAUDE_THINK_GATE="$TMP/repo/.think-gate.json" bash "$TMP_PIPELINE" 2>&1)
if [[ -z "$out" ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] pipeline gate validates env override against current session\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("pipeline gate validates env override against current session")
  printf '  [FAIL] pipeline gate trusted foreign env override\n'
  printf '         output: %s\n' "${out:0:300}"
fi

out=$(printf '%s' "$mutation_payload" | CRAFT_AGENT_WORKSPACE="$TMP" CRAFT_AGENT_SESSION_ID=session-brand-new bash "$TMP_MUTATION" 2>&1)
code=$?
if [[ "$code" -eq 2 ]] && echo "$out" | grep -q "no valid think-gate" && ! echo "$out" | grep -q "#same-repo-foreign-session"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] mutation gate ignores same-repo foreign-session local gate\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("mutation gate ignores same-repo foreign-session local gate")
  printf '  [FAIL] mutation gate used same-repo foreign-session local gate (exit %s)\n' "$code"
  printf '         output: %s\n' "${out:0:400}"
fi

cat >"$TMP/repo/.think-gate.json" <<JSON
{"ticket":"#same-repo-current-session","repo_root":"$TMP/repo","session":"session-brand-new","status":"implementing"}
JSON
out=$(printf '%s' "$payload_current_repo" | CRAFT_AGENT_SESSION_ID=session-brand-new bash "$TMP_INVESTIGATE" 2>&1)
if echo "$out" | grep -q "INVESTIGATION REQUIRED" && echo "$out" | grep -q "#same-repo-current-session"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] investigate gate still accepts same-repo current-session local gate\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("investigate gate still accepts same-repo current-session local gate")
  printf '  [FAIL] investigate gate rejected current-session local gate\n'
  printf '         output: %s\n' "${out:0:300}"
fi

report
