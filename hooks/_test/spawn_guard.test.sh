#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
HOOK="$ROOT/hooks/agent-comms/spawn-guard.sh"

payload() {
  python3 - "$1" <<'PY'
import json, sys
print(json.dumps({"tool_input": json.loads(sys.argv[1])}))
PY
}

expect_pass \
  "help request passes" \
  "$HOOK" \
  "$(payload '{"help": true}')"

expect_block \
  "review spawn missing explicit contract blocks" \
  "$HOOK" \
  "$(payload '{"name":"GPT review","prompt":"Review this diff and return findings.","model":"pi/gpt-5.5"}')"

expect_block \
  "review spawn with weak model blocks" \
  "$HOOK" \
  "$(payload '{"name":"Review","prompt":"Review with RULES_BUNDLE and send_agent_message findings then set_session_status done.","permissionMode":"allow-all","model":"pi/gpt-5.4-mini","thinkingLevel":"high","enabledSourceSlugs":[]}')"

expect_block \
  "review spawn without rules binding blocks" \
  "$HOOK" \
  "$(payload '{"name":"Review","prompt":"Review and send_agent_message findings then set_session_status done.","permissionMode":"allow-all","model":"pi/gpt-5.5","thinkingLevel":"high","enabledSourceSlugs":[]}')"

expect_block \
  "review spawn with non-reasoning model blocks" \
  "$HOOK" \
  "$(payload '{"name":"Review","prompt":"Review with RULES_BUNDLE and send_agent_message findings then set_session_status done.","permissionMode":"allow-all","model":"gpt-4o","thinkingLevel":"high","enabledSourceSlugs":[]}')"

expect_pass \
  "review spawn with explicit rules contract passes" \
  "$HOOK" \
  "$(payload '{"name":"GPT-5.5 review","prompt":"Review using RULES_BUNDLE and session-coordination. Send findings by send_agent_message and call set_session_status done.","permissionMode":"allow-all","model":"pi/gpt-5.5","thinkingLevel":"high","enabledSourceSlugs":[]}')"

expect_pass \
  "non-review work with explicit off reasoning and sources passes" \
  "$HOOK" \
  "$(payload '{"name":"Data extraction","prompt":"Use RESOLVER.md and spawn-protocol. Extract local facts; no reply tools needed.","permissionMode":"allow-all","model":"claude-sonnet-5","thinkingLevel":"off","enabledSourceSlugs":[]}')"

report
