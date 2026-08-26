#!/usr/bin/env bash
# Tests for bin/verify-enforcement.sh
#
# The probe is the acceptance test for "enforcement is live, not just present."
# These tests assert it:
#   1. PASSES a fully-wired fixture (all artifacts + a working blocking gate)
#   2. runs a real live block test (continue:false) against the deployed gate
#   3. FAILS a skills-only fixture (the advisory-only failure mode of #96)
#   4. FAILS when the blocking wrapper is absent from settings.json
#
# No jq dependency; uses python3 for JSON, matching verify-enforcement.sh.
#
# Refs: #96.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROBE="$REPO_ROOT/bin/verify-enforcement.sh"
REAL_GATE="$REPO_ROOT/hooks/resolver/ca-enforcement-gate.sh"

pass=0
fail=0
ok()   { echo "  PASS: $1"; pass=$((pass + 1)); }
bad()  { echo "  FAIL: $1" >&2; fail=$((fail + 1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Build a fully-wired PASS fixture ----------------------------------------

WIRED="$TMP/wired"
mkdir -p "$WIRED/hooks/resolver" "$WIRED/.claude"
cp "$REAL_GATE" "$WIRED/hooks/resolver/ca-enforcement-gate.sh"
chmod +x "$WIRED/hooks/resolver/ca-enforcement-gate.sh"
: > "$WIRED/RULES_BUNDLE.md"
: > "$WIRED/RESOLVER.md"
(cd "$WIRED" && ln -s RULES_BUNDLE.md CLAUDE.md)
cat > "$WIRED/enforcement-manifest.json" <<'JSON'
{"gates":[{"id":"think-gate"},{"id":"investigate-gate"}]}
JSON
cat > "$WIRED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$WIRED/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
cat > "$WIRED/automations.json" <<'JSON'
{"version":2,"automations":{"SchedulerTick":[{"name":"Standing-order watchdog","cron":"*/10 * * * *","actions":[{"type":"prompt","prompt":"x"}]}]}}
JSON

if bash "$PROBE" --target "$WIRED" --mode craft-agent >/dev/null 2>&1; then
    ok "fully-wired fixture passes"
else
    bad "fully-wired fixture should pass but did not"
fi

# --- FAIL fixture: skills only, nothing wired --------------------------------

DARK="$TMP/dark"
mkdir -p "$DARK/skills"
: > "$DARK/skills/placeholder"
if bash "$PROBE" --target "$DARK" --mode craft-agent >/dev/null 2>&1; then
    bad "skills-only fixture should FAIL the probe but passed"
else
    ok "skills-only fixture fails the probe (advisory-only caught)"
fi

# --- FAIL fixture: everything present but blocking wrapper not registered -----

NOWRAP="$TMP/nowrap"
cp -r "$WIRED" "$NOWRAP"
cat > "$NOWRAP/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$NOWRAP/hooks/resolver/inject-resolver.sh"}]}]}}
JSON
if bash "$PROBE" --target "$NOWRAP" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture missing the blocking wrapper should FAIL but passed"
else
    ok "fixture missing ca-enforcement-gate registration fails the probe"
fi

echo
echo "verify_enforcement: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
