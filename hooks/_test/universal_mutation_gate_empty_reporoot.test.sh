#!/usr/bin/env bash
# siege#926: on an empty REPO_ROOT (workspace-root, non-git CWD) a KNOWN
# session must resolve its OWN session-dir gate (and its own artifacts), and
# must NEVER inherit the shared workspace-root singleton or another session's
# gate. Unknown sessions, and known sessions with no gate, fail closed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$ROOT/hooks/bash/universal-mutation-gate.sh"
RESOLVER="$ROOT/hooks/lib/resolve-think-gate.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

SID="261001-empty-reporoot"
OTHER_SID="261001-other-session"
TICKET="TEST-926-empty-reporoot-fixture"     # unique: never appears in real plans/
WS="$TMP/workspace"                           # NOT a git repo -> empty REPO_ROOT
mkdir -p "$WS/sessions/$SID" "$WS/sessions/$OTHER_SID" "$WS/plans"

fail() { echo "FAIL: $1" >&2; exit 1; }

# Scrub the live session's env so the resolver does not pick up THIS session's
# real CRAFT_SESSION_DIR/ID (which would shadow the fixtures). Each case sets
# CRAFT_SESSION_ID explicitly (or leaves it unset for the "unknown" case).
SCRUB=(env -u CRAFT_SESSION_DIR -u CRAFT_SESSION_ID -u CLAUDE_SESSION_ID -u SESSION_ID
       -u CLAUDE_SIGNAL_DIR -u CRAFT_SIGNAL_DIR -u CRAFT_AGENT_SIGNAL_DIR
       -u CRAFT_AGENT_SESSION_DIR -u CLAUDE_SESSION_DIR)

# The scenario is only valid if the workspace-root CWD is not a git repo.
if git -C "$WS" rev-parse --show-toplevel >/dev/null 2>&1; then
  fail "test precondition: \$WS must not be inside a git repo (empty REPO_ROOT)"
fi

payload() { printf '{"tool_input":{"command":"%s"},"cwd":"%s"}\n' "$1" "$WS"; }

write_json() {
  python3 - "$1" "$2" <<'PY'
import json, sys
open(sys.argv[1], 'w').write(json.dumps(json.loads(sys.argv[2]), indent=2) + '\n')
PY
}

write_premortem() {
  cat > "$WS/plans/pre-mortem-926test.md" <<EOF2
---
ticket_refs:
  - $TICKET: fixture
---
# Pre-mortem $TICKET

### Tiger 1
Severity: LOW
Mitigation: fixture.
EOF2
}

session_think_gate() {
  write_json "$WS/sessions/$SID/think-gate.json" \
    "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SID\", \"session\": \"$SID\", \"status\": \"implementing\"}"
}
session_artifacts() {
  write_json "$WS/sessions/$SID/investigate-gate.json" \
    "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SID\", \"findings\": [{\"id\": \"F1\"}]}"
  write_json "$WS/sessions/$SID/junior-senior-gate.json" \
    "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SID\", \"junior_found\": true, \"senior_found\": true}"
  write_json "$WS/sessions/$SID/artifacts-posted-gate.json" \
    "{\"ticket\": \"$TICKET\", \"task\": \"$TICKET\", \"sessionId\": \"$SID\", \"investigate_posted\": true, \"premortem_posted\": true}"
  write_premortem
}
resolver() { "${SCRUB[@]}" CRAFT_SESSION_ID="$1" python3 "$RESOLVER" "${@:2}"; }
resolver_nosession() { "${SCRUB[@]}" python3 "$RESOLVER" "$@"; }
run_gate() { "${SCRUB[@]}" CRAFT_SESSION_ID="$1" CRAFT_AGENT_WORKSPACE="$WS" bash "$HOOK" <<<"$(payload "$2")"; }
run_gate_nosession() { "${SCRUB[@]}" CRAFT_AGENT_WORKSPACE="$WS" bash "$HOOK" <<<"$(payload "$1")"; }

# --- resolver unit checks ------------------------------------------------
known="$(resolver "$SID" --workspace "$WS" --session-known)"
[[ "$known" == "1" ]] || fail "--session-known should be 1 with CRAFT_SESSION_ID"
unknown="$(resolver_nosession --workspace "$WS" --session-known)"
[[ "$unknown" == "0" ]] || fail "--session-known should be 0 with no session env ($unknown)"

session_think_gate
sg="$(resolver "$SID" --workspace "$WS" --session-gate --gate-name think-gate)"
grep -q "sessions/$SID/think-gate.json" <<<"$sg" || fail "--session-gate should resolve the session's own think-gate ($sg)"

# shared-root singleton for a DIFFERENT ticket must NOT be returned by --session-gate
write_json "$WS/think-gate.json" "{\"ticket\": \"STRANGER\", \"status\": \"implementing\"}"
rm -f "$WS/sessions/$SID/think-gate.json"
sg_none="$(resolver "$SID" --workspace "$WS" --session-gate --gate-name think-gate)"
[[ "$sg_none" == "null" ]] || fail "--session-gate must NOT fall back to the shared root ($sg_none)"
rm -f "$WS/think-gate.json"

# unknown session -> no session gate
session_think_gate
sg_unknown="$(resolver_nosession --workspace "$WS" --session-gate --gate-name think-gate)"
[[ "$sg_unknown" == "null" ]] || fail "--session-gate for an unknown session must be null ($sg_unknown)"

# --- KNOWN-GOOD: known session + own implementing gate + artifacts -> PASS
session_artifacts
run_gate "$SID" "git checkout -b feature/empty-reporoot-good" \
  || fail "known session with its own implementing gate + artifacts must PASS on empty REPO_ROOT"

# --- KNOWN-BAD 1: known session, implementing gate, MISSING artifacts -> BLOCK
rm -f "$WS/sessions/$SID/"{investigate-gate,junior-senior-gate,artifacts-posted-gate}.json "$WS/plans/pre-mortem-926test.md"
if out="$(run_gate "$SID" "git checkout -b feature/empty-reporoot-noart" 2>&1)"; then
  fail "known session with implementing gate but no artifacts must BLOCK"
fi
grep -qi 'artifacts missing' <<<"$out" || fail "expected missing-artifacts diagnostic ($out)"

# --- KNOWN-BAD 2: known session, NO session gate, but a shared-root singleton
# present -> must BLOCK (must not inherit the shared root). This is the bleed.
rm -f "$WS/sessions/$SID/think-gate.json"
write_json "$WS/think-gate.json" "{\"ticket\": \"STRANGER\", \"status\": \"implementing\"}"
if run_gate "$SID" "git checkout -b feature/empty-reporoot-bleed" >/dev/null 2>&1; then
  fail "known session with no gate must NOT inherit the shared-root singleton"
fi
rm -f "$WS/think-gate.json"

# --- KNOWN-BAD 3: another session's gate must not resolve for our session
write_json "$WS/sessions/$OTHER_SID/think-gate.json" \
  "{\"ticket\": \"OTHER\", \"sessionId\": \"$OTHER_SID\", \"session\": \"$OTHER_SID\", \"status\": \"implementing\"}"
if run_gate "$SID" "git checkout -b feature/empty-reporoot-cross" >/dev/null 2>&1; then
  fail "a different session's gate must not authorize our session"
fi

# --- KNOWN-BAD 4: unknown session (no CRAFT_SESSION_ID) + shared singleton -> BLOCK
write_json "$WS/think-gate.json" "{\"ticket\": \"STRANGER\", \"status\": \"implementing\"}"
if run_gate_nosession "git checkout -b feature/empty-reporoot-unknown" >/dev/null 2>&1; then
  fail "unknown session on empty REPO_ROOT must not bind the no-repo shared singleton"
fi
rm -f "$WS/think-gate.json"

# --- designing status still allows a non-mutation command (regression guard)
write_json "$WS/sessions/$SID/think-gate.json" \
  "{\"ticket\": \"$TICKET\", \"sessionId\": \"$SID\", \"session\": \"$SID\", \"status\": \"designing\"}"
run_gate "$SID" "ls -la" || fail "a non-mutation read must pass under designing even on empty REPO_ROOT"

echo "universal_mutation_gate_empty_reporoot.test: PASS"
