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

payload_with_root() {
  python3 - "$ROOT" "$1" <<'PY'
import json, sys
root, kind = sys.argv[1:3]
prompts = {
  "no-worktree": "Use RESOLVER.md and spawn-protocol. Implement fix 248 and commit changes.",
  "with-worktree": "Use RESOLVER.md and spawn-protocol. Create a git worktree first, then implement fix 248 and commit changes there.",
  "read-only": "Use RESOLVER.md and spawn-protocol. Review only; do not modify files and send_agent_message findings then set_session_status done.",
}
models = {"read-only": "claude-opus-4-8"}
thinking = {"read-only": "high"}
print(json.dumps({"tool_input": {
  "name": "Read-only review" if kind == "read-only" else "Implementation",
  "prompt": prompts[kind],
  "permissionMode": "allow-all",
  "model": models.get(kind, "claude-sonnet-5"),
  "thinkingLevel": thinking.get(kind, "medium"),
  "enabledSourceSlugs": [],
  "workingDirectory": root,
}}))
PY
}

expect_block \
  "write-capable git child without worktree blocks" \
  "$HOOK" \
  "$(payload_with_root no-worktree)"

expect_block \
  "write-capable git child with inherited working directory blocks" \
  "$HOOK" \
  "$(payload '{"name":"Implementation","prompt":"Use RESOLVER.md and spawn-protocol. Implement fix 248 and commit changes.","permissionMode":"allow-all","model":"claude-sonnet-5","thinkingLevel":"medium","enabledSourceSlugs":[]}')"

expect_pass \
  "write-capable git child with worktree instruction passes" \
  "$HOOK" \
  "$(payload_with_root with-worktree)"

expect_pass \
  "read-only git child without worktree passes" \
  "$HOOK" \
  "$(payload_with_root read-only)"

report
