#!/usr/bin/env bash
# Tests for bin/verify-enforcement.sh
#
# The probe is the acceptance test for "enforcement is live, not just present."
# These tests assert it:
#   1. PASSES a fully-wired fixture (all artifacts + a working blocking gate)
#   2. runs a real live block test (continue:false) against the deployed gate
#   3. FAILS a skills-only fixture (the advisory-only failure mode of #96)
#   4. FAILS when the blocking wrapper is absent from settings.json
#   5. FAILS when a deployed gate guard is missing (F1) or the registered
#      wrapper path does not resolve (F2)
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
# The wrapper silently skips guards it cannot execute, so the probe requires
# the deployed guards to be present and executable. Provide clean stubs.
for guard in think-gate-guard.sh investigate-gate-guard.sh skill-enforcement-gate.sh; do
    printf '#!/usr/bin/env bash\n' > "$WIRED/hooks/resolver/$guard"
    chmod +x "$WIRED/hooks/resolver/$guard"
done
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

# --- PASS fixture: fully wired but NO watchdog automation ---------------------
# The standing-order watchdog is opt-in and not wired by default (README.md);
# its absence is advisory, not an enforcement failure. A fully-wired target
# whose only "gap" is the missing watchdog must PASS. Goes red if Check 7 is
# reverted to `fail`.

NOWATCHDOG="$TMP/nowatchdog"
cp -r "$WIRED" "$NOWATCHDOG"
cat > "$NOWATCHDOG/automations.json" <<'JSON'
{"version":2,"automations":{"SchedulerTick":[{"name":"Skills sync","cron":"0 * * * *","actions":[{"type":"prompt","prompt":"x"}]}]}}
JSON
if bash "$PROBE" --target "$NOWATCHDOG" --mode craft-agent >/dev/null 2>&1; then
    ok "fully-wired-but-no-watchdog fixture passes (watchdog is advisory)"
else
    bad "no-watchdog fixture should PASS (watchdog opt-in) but failed"
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

# --- FAIL fixture: wrapper present but a deployed gate guard is missing (F1) --

NOGUARD="$TMP/noguard"
cp -r "$WIRED" "$NOGUARD"
rm -f "$NOGUARD/hooks/resolver/think-gate-guard.sh"
if bash "$PROBE" --target "$NOGUARD" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture with a missing gate guard should FAIL but passed"
else
    ok "fixture with a missing deployed gate guard fails the probe"
fi

# --- FAIL fixture: registered wrapper path does not resolve (F2) --------------

BADPATH="$TMP/badpath"
cp -r "$WIRED" "$BADPATH"
cat > "$BADPATH/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"/nonexistent/typo/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$BADPATH" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture with a non-resolving wrapper path should FAIL but passed"
else
    ok "fixture with a non-resolving ca-enforcement-gate path fails the probe"
fi

echo
echo "verify_enforcement: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
